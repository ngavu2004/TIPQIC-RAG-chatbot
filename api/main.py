import os
import sys
from uuid import uuid4
from datetime import datetime, timedelta
from typing import List, Optional
import boto3
from botocore.exceptions import ClientError

from fastapi import FastAPI, HTTPException, Depends, status, Request, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from query.chatbot_response import generate_chat_response
from query.query_db import search_db
from data.create_db import add_chunks_to_chroma
from db.database import (
    get_db,
    User,
    UserSession,
    ChatSession,
    ChatMessage,
    verify_password,
    get_password_hash,
)

# ----------------------------
# Config
# ----------------------------
SESSION_COOKIE_NAME = "tipqic_session"
SESSION_TTL_MINUTES = 60 * 24  # 1 day
RESUME_TOKEN_TTL_MINUTES = 60 * 24 * 7  # 7 days
FRONTEND_ORIGINS = ["http://localhost:8501", "http://127.0.0.1:8501"]  # Streamlit dev server

# S3 Configuration
S3_BUCKET_NAME = "tipchatbot"
S3_FILES_PREFIX = "files/"

def generate_session_name(message: str) -> str:
    """Generate a meaningful session name from the first user message."""
    cleaned_message = message.strip()
    if len(cleaned_message) > 50:
        cleaned_message = cleaned_message[:47] + "..."
    cleaned_message = " ".join(cleaned_message.split())
    if len(cleaned_message) < 3:
        return f"Chat {datetime.now().strftime('%m/%d %H:%M')}"
    return cleaned_message

def create_resume_token(session_id: str) -> str:
    """Create a resume token for the session."""
    return f"resume_{session_id}_{uuid4().hex[:16]}"

def upload_file_to_s3(file_content: bytes, filename: str) -> dict:
    """Upload a file to S3 bucket."""
    try:
        s3_client = boto3.client('s3')
        s3_key = f"{S3_FILES_PREFIX}{filename}"
        
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType='application/octet-stream'
        )
        
        return {
            "success": True,
            "s3_key": s3_key,
            "filename": filename,
            "message": f"File uploaded successfully to s3://{S3_BUCKET_NAME}/{s3_key}"
        }
    except ClientError as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to upload file to S3"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Unexpected error during upload"
        }

app = FastAPI(
    title="TIPQIC RAG Chatbot API",
    description="API for the TIPQIC RAG Chatbot system",
    version="1.0.0",
)

# Enable CORS for cookie-based auth
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,  # MUST be explicit when allow_credentials=True
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Models
# ----------------------------
class UserSignup(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class ResumeToken(BaseModel):
    resume_token: str

class ChatRequest(BaseModel):
    message: str
    chat_session_id: Optional[str] = None
    max_results: Optional[int] = 5
    include_sources: Optional[bool] = True

class SourceInfo(BaseModel):
    filename: str
    page: str
    score: float
    preview: str

class ChatResponse(BaseModel):
    response: str
    sources: List[SourceInfo]
    timestamp: str
    success: bool
    error_message: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

class DocumentChunk(BaseModel):
    content: str
    metadata: dict

# ----------------------------
# Session-based auth dependency
# ----------------------------
def get_current_user_from_session(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    sid = request.cookies.get(SESSION_COOKIE_NAME)
    print(f"DEBUG: Session cookie value: {sid}")
    if not sid:
        print("DEBUG: No session cookie found")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    sess = (
        db.query(UserSession)
        .filter(UserSession.id == sid, UserSession.is_active == True)
        .first()
    )
    print(f"DEBUG: Session found: {sess is not None}")
    if not sess:
        print("DEBUG: Session not found in database")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    # Optional expiry check if your model has expires_at
    if getattr(sess, "expires_at", None) and sess.expires_at < datetime.utcnow():
        print("DEBUG: Session expired")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    user = db.query(User).filter(User.id == sess.user_id).first()
    print(f"DEBUG: User found: {user is not None}")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def get_current_admin_user(current_user: User = Depends(get_current_user_from_session)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

# ----------------------------
# Endpoints
# ----------------------------
@app.get("/", response_model=dict)
async def root():
    return {
        "message": "TIPQIC RAG Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/api/chat",
            "health": "/api/health",
            "docs": "/docs",
        },
    }

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy", timestamp=datetime.now().isoformat(), version="1.0.0"
    )

# --- Auth: Signup (no automatic login here; keep it simple) ---
@app.post("/api/auth/signup", response_model=dict)
async def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    # Check uniqueness
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    if user_data.email and user_data.email.strip():
        existing_email = db.query(User).filter(User.email == user_data.email.strip()).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    hashed_password = get_password_hash(user_data.password)
    email = user_data.email.strip() if user_data.email and user_data.email.strip() else None
    db_user = User(username=user_data.username, password_hash=hashed_password, email=email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {"ok": True, "username": db_user.username}

# --- Auth: Login (creates session + sets cookie) ---
@app.post("/api/auth/login", response_model=dict)
async def login(user_data: UserLogin, response: Response, db: Session = Depends(get_db)):
    user = authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    user.last_login = datetime.utcnow()
    db.commit()

    # Create backend session
    sid = str(uuid4())
    expires_at = datetime.utcnow() + timedelta(minutes=SESSION_TTL_MINUTES)
    resume_token = create_resume_token(sid)
    
    db_sess = UserSession(
        id=sid, 
        user_id=user.id, 
        resume_token=resume_token,
        is_active=True, 
        expires_at=expires_at
    )
    db.add(db_sess)
    db.commit()

    # Set httpOnly cookie (Secure=True in prod with HTTPS)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=sid,
        httponly=True,
        samesite="lax",
        secure=False,  # True in production
        max_age=SESSION_TTL_MINUTES * 60,
        path="/",
    )

    return {"ok": True, "username": user.username, "resume_token": resume_token}

# --- Auth: Logout (revokes session + clears cookie) ---
@app.post("/api/auth/logout", response_model=dict)
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    sid = request.cookies.get(SESSION_COOKIE_NAME)
    if sid:
        sess = db.query(UserSession).filter(UserSession.id == sid).first()
        if sess:
            sess.is_active = False
            sess.resume_token = None  # Clear resume token
            db.commit()

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        samesite="lax",
    )
    return {"ok": True}

# --- Resume session (unprotected) ---
@app.post("/api/auth/resume")
async def resume_session(resume_data: ResumeToken, response: Response, db: Session = Depends(get_db)):
    # Find session by resume token
    session = (
        db.query(UserSession)
        .filter(UserSession.resume_token == resume_data.resume_token, UserSession.is_active == True)
        .first()
    )
    
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired resume token")
    
    # Set the session cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.id,
        httponly=True,
        samesite="lax",
        secure=False,  # True in production
        max_age=SESSION_TTL_MINUTES * 60,
        path="/",
    )
    
    return {"ok": True}

# --- Me (protected) ---
@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user_from_session)):
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "created_at": current_user.created_at.isoformat(),
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        "is_admin": current_user.is_admin,
    }

# --- Admin: Dashboard (admin only) ---
@app.get("/api/admin/dashboard")
async def admin_dashboard(current_user: User = Depends(get_current_admin_user)):
    return {
        "message": "Admin Dashboard",
        "admin_user": current_user.username,
        "timestamp": datetime.utcnow().isoformat(),
        "stats": {
            "total_users": "Coming soon...",
            "total_sessions": "Coming soon...",
            "total_chats": "Coming soon..."
        }
    }

# --- Admin: File Upload (admin only) ---
@app.post("/api/admin/upload-file")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin_user)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Read file content
    file_content = await file.read()
    
    # Upload to S3
    result = upload_file_to_s3(file_content, file.filename)
    
    if result["success"]:
        return {
            "success": True,
            "message": result["message"],
            "filename": result["filename"],
            "s3_key": result["s3_key"],
            "uploaded_by": current_user.username,
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        raise HTTPException(status_code=500, detail=result["message"])

# --- Chat (protected) ---
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user_from_session),
    db: Session = Depends(get_db),
):
    try:
        # Get or create chat session
        if request.chat_session_id:
            chat_session = (
                db.query(ChatSession)
                .filter(ChatSession.id == request.chat_session_id, ChatSession.user_id == current_user.id)
                .first()
            )
            if not chat_session:
                raise HTTPException(status_code=404, detail="Chat session not found")
        else:
            session_name = generate_session_name(request.message)
            chat_session = ChatSession(user_id=current_user.id, session_name=session_name)
            db.add(chat_session)
            db.commit()
            db.refresh(chat_session)

        # Optionally update default name
        if chat_session.session_name == "New Chat":
            session_name = generate_session_name(request.message)
            chat_session.session_name = session_name
            db.commit()

        # Search the database
        results = search_db(request.message)
        if not results:
            return ChatResponse(
                response="I couldn't find relevant information in the documents to answer your question. Could you try rephrasing it or asking about a different topic?",
                sources=[],
                timestamp=datetime.now().isoformat(),
                success=True,
            )

        # Generate AI response
        ai_response = generate_chat_response(request.message, results)

        # Prepare sources
        sources_info: List[SourceInfo] = []
        if request.include_sources:
            for doc, score in results[: request.max_results]:
                source_filename = os.path.basename(doc.metadata.get("source", "Unknown"))
                page = str(doc.metadata.get("page", "N/A"))
                preview = doc.page_content[:200].replace("\n", " ").strip()

                sources_info.append(
                    SourceInfo(filename=source_filename, page=page, score=score, preview=preview)
                )

        # Store user message
        user_message = ChatMessage(
            chat_session_id=chat_session.id,
            role="user",
            content=request.message,
        )
        db.add(user_message)

        # Store assistant message with sources (convert to dict for JSONB)
        sources_dict = [s.dict() for s in sources_info]
        assistant_message = ChatMessage(
            chat_session_id=chat_session.id,
            role="assistant",
            content=ai_response,
            sources=sources_dict,
        )
        db.add(assistant_message)
        db.commit()

        return ChatResponse(
            response=ai_response,
            sources=sources_info,
            timestamp=datetime.now().isoformat(),
            success=True,
        )

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return ChatResponse(
            response="I'm sorry, I encountered an error while processing your request. Please try again.",
            sources=[],
            timestamp=datetime.now().isoformat(),
            success=False,
            error_message=str(e),
        )

# --- Add chunks (unprotected by default; lock down if needed) ---
@app.post("/api/add_chunks")
async def add_chunks(chunks: List[DocumentChunk]):
    try:
        chunk_dicts = [chunk.dict() for chunk in chunks]
        response = add_chunks_to_chroma(chunk_dicts)
        return response
    except Exception as e:
        print(f"Error in add_chunks endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add chunks: {str(e)}")

# --- Sessions list (protected) ---
@app.get("/api/chat/sessions")
async def get_chat_sessions(
    current_user: User = Depends(get_current_user_from_session),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id, ChatSession.is_active == True)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return [
        {
            "id": str(session.id),
            "name": session.session_name,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }
        for session in sessions
    ]

# --- Messages in a session (protected) ---
@app.get("/api/chat/sessions/{session_id}/messages")
async def get_chat_messages(
    session_id: str,
    current_user: User = Depends(get_current_user_from_session),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.chat_session_id == session_id)
        .order_by(ChatMessage.timestamp)
        .all()
    )
    return [
        {
            "id": str(msg.id),
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
            "sources": msg.sources,
        }
        for msg in messages
    ]

# --- Delete session (protected) ---
@app.delete("/api/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_user_from_session),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    session.is_active = False
    db.commit()
    return {"message": "Chat session deleted successfully"}

# --- Rename session (protected) ---
@app.put("/api/chat/sessions/{session_id}/rename")
async def rename_chat_session(
    session_id: str,
    new_name: str,
    current_user: User = Depends(get_current_user_from_session),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    session.session_name = new_name.strip()[:255]
    db.commit()
    return {"message": "Chat session renamed successfully", "new_name": session.session_name}

@app.get("/api/stats", response_model=dict)
async def get_stats():
    try:
        return {
            "status": "available",
            "timestamp": datetime.now().isoformat(),
            "message": "Statistics endpoint - implement based on your Chroma DB",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
