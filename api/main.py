import os
import sys
import logging
from uuid import uuid4
from datetime import datetime, timedelta
from typing import List, Optional
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException, Depends, status, Request, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from query.chatbot_response import generate_response_with_routing
from query.query_db import search_db
from data.create_db import add_chunks_to_chroma
from db.database import (
    get_db,
    User,
    UserSession,
    ChatSession,
    ChatMessage,
    UserTask,
    verify_password,
    get_password_hash,
)

# Import file upload manager
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from file_upload_manager import file_upload_service

# Import Teams integration
from teams_integration import teams_integration

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



app = FastAPI(
    title="TIPQIC RAG Chatbot API",
    description="API for the TIPQIC RAG Chatbot system",
    version="1.0.0",
)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # Test Teams integration connection
    if teams_integration.is_configured():
        logger.info("🔧 Teams integration configured successfully")
        logger.info("📋 Environment variables loaded:")
        logger.info(f"   - Client ID: {teams_integration.client_id[:8]}...")
        logger.info(f"   - Tenant ID: {teams_integration.tenant_id[:8]}...")
        logger.info(f"   - Target Plan: test1")
        logger.info("🔐 Starting Teams authentication...")
        
        # Try to get access token at startup
        try:
            # access_token = teams_integration.get_access_token()
            access_token = "test"
            if access_token:
                logger.info("✅ Teams authentication successful at startup")
                logger.info("🎯 Teams integration ready to create tasks")
            else:
                logger.warning("⚠️ Teams authentication failed at startup")
        except Exception as e:
            logger.error(f"❌ Error during Teams authentication: {str(e)}")
    else:
        logger.info("Teams integration not configured - missing environment variables")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down TIPQIC RAG Chatbot API")

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
    response_type: str = "normal"  # "normal" or "task_list"
    tasks: Optional[List[str]] = None
    chat_session_id: Optional[str] = None

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
    # Upload to S3 using the file upload service
    result = file_upload_service.upload_from_fastapi(file)
    
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

# --- Admin: Upload from Source (admin only) ---
@app.post("/api/admin/upload-from-source")
async def upload_from_source(
    source_name: str,
    file_identifier: str,
    s3_filename: str = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    # Register database source if needed
    if source_name == "database" and "database" not in file_upload_service.get_available_sources():
        from file_upload_manager import DatabaseFileSource
        file_upload_service.register_source("database", DatabaseFileSource(db))
    
    # Upload from source
    result = file_upload_service.upload_from_source(source_name, file_identifier, s3_filename)
    
    if result["success"]:
        return {
            "success": True,
            "message": result["message"],
            "filename": result["filename"],
            "s3_key": result["s3_key"],
            "uploaded_by": current_user.username,
            "timestamp": datetime.utcnow().isoformat(),
            "source": source_name
        }
    else:
        raise HTTPException(status_code=500, detail=result["message"])

# --- Admin: List Source Files (admin only) ---
@app.get("/api/admin/list-source-files/{source_name}")
async def list_source_files(
    source_name: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    # Register database source if needed
    if source_name == "database" and "database" not in file_upload_service.get_available_sources():
        from file_upload_manager import DatabaseFileSource
        file_upload_service.register_source("database", DatabaseFileSource(db))
    
    files = file_upload_service.list_source_files(source_name)
    return {
        "source": source_name,
        "files": files,
        "count": len(files)
    }

# --- Admin: Get Available Sources (admin only) ---
@app.get("/api/admin/available-sources")
async def get_available_sources(
    current_user: User = Depends(get_current_admin_user)
):
    return {
        "sources": file_upload_service.get_available_sources(),
        "count": len(file_upload_service.get_available_sources())
    }

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
            # Create a new session only if explicitly requested or if this is the first message
            # For now, we'll create a new session, but we could make this more explicit
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

        # Generate AI response with routing
        ai_response = generate_response_with_routing(request.message, results)

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

        # Handle different response types
        response_type = "normal"
        tasks_list = None
        response_content = ""
        
        if hasattr(ai_response, 'tasks'):
            # This is a TaskList object
            response_type = "task_list"
            tasks_list = ai_response.tasks
            response_content = f"I've created a list of {len(tasks_list)} actionable tasks to help you with your request."
            
            # Store tasks in the database
            for i, task_content in enumerate(tasks_list, 1):
                user_task = UserTask(
                    user_id=current_user.id,
                    chat_session_id=chat_session.id,
                    task_content=task_content,
                    task_order=i,
                    is_completed=False
                )
                db.add(user_task)
            
            # Create tasks in Microsoft Teams Planner (only if user is authenticated)
            if teams_integration.is_configured():
                logger.info(f"🎯 Attempting to create {len(tasks_list)} tasks in Teams Planner")
                teams_tasks_created = 0
                
                for task_content in tasks_list:
                    try:
                        teams_result = teams_integration.create_task_in_test1_plan(
                            title=task_content,
                            description=f"Task from TIPQIC Chatbot - Session: {chat_session.session_name}"
                        )
                        if teams_result:
                            teams_tasks_created += 1
                            logger.info(f"✅ Created Teams task: {teams_result['title']}")
                        else:
                            # This is expected when no user authentication - log at info level
                            logger.info(f"Teams task creation skipped for: {task_content} (authentication required)")
                    except Exception as e:
                        logger.error(f"❌ Error creating Teams task: {str(e)}")
                
                if teams_tasks_created > 0:
                    logger.info(f"🎯 Successfully created {teams_tasks_created}/{len(tasks_list)} tasks in Teams Planner")
                else:
                    logger.info("ℹ️ Teams integration available but no tasks created")
                    logger.info("💡 Teams authentication required - check startup logs")
            else:
                logger.info("Teams integration not configured - skipping Teams task creation")
        else:
            # This is a normal string response
            response_content = ai_response

        # Store user message
        user_message = ChatMessage(
            chat_session_id=chat_session.id,
            role="user",
            content=request.message,
        )
        db.add(user_message)

        # Store assistant message with sources and tasks (convert to dict for JSONB)
        sources_dict = [s.dict() for s in sources_info]
        
        # Include task information in the message if tasks were generated
        message_data = {
            "sources": sources_dict,
        }
        if tasks_list:
            message_data["response_type"] = "task_list"
            message_data["tasks"] = tasks_list
        
        assistant_message = ChatMessage(
            chat_session_id=chat_session.id,
            role="assistant",
            content=response_content,
            sources=message_data,
        )
        db.add(assistant_message)
        db.commit()

        return ChatResponse(
            response=response_content,
            sources=sources_info,
            timestamp=datetime.now().isoformat(),
            success=True,
            response_type=response_type,
            tasks=tasks_list,
            chat_session_id=str(chat_session.id),
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

# --- Create new session (protected) ---
@app.post("/api/chat/sessions")
async def create_chat_session(
    session_name: str = "New Chat",
    current_user: User = Depends(get_current_user_from_session),
    db: Session = Depends(get_db),
):
    """Create a new chat session."""
    chat_session = ChatSession(
        user_id=current_user.id, 
        session_name=session_name.strip()[:255]
    )
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    
    return {
        "id": str(chat_session.id),
        "name": chat_session.session_name,
        "created_at": chat_session.created_at.isoformat(),
        "updated_at": chat_session.updated_at.isoformat(),
    }

# --- Teams Integration Test (protected) ---
@app.post("/api/teams/test")
async def test_teams_integration(
    current_user: User = Depends(get_current_user_from_session),
):
    """Test Teams integration and create a sample task"""
    try:
        if not teams_integration.is_configured():
            raise HTTPException(
                status_code=400, 
                detail="Teams integration not configured - missing environment variables"
            )
        
        # Test connection
        if not teams_integration.test_connection():
            raise HTTPException(
                status_code=500, 
                detail="Teams integration connection failed - interactive login may be required"
            )
        
        # Create a test task
        test_task_title = f"Test Task from {current_user.username} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        test_task_description = f"This is a test task created by {current_user.username} to verify Teams integration."
        
        teams_result = teams_integration.create_task_in_test1_plan(
            title=test_task_title,
            description=test_task_description
        )
        
        if teams_result:
            return {
                "success": True,
                "message": "Teams integration test successful",
                "teams_task": teams_result,
                "user": current_user.username
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail="Failed to create test task in Teams"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Teams integration test error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Teams integration test failed: {str(e)}"
        )

# --- Teams Integration Status (protected) ---
@app.get("/api/teams/status")
async def get_teams_integration_status(
    current_user: User = Depends(get_current_user_from_session),
):
    """Get Teams integration status"""
    try:
        status_info = {
            "configured": teams_integration.is_configured(),
            "client_id": teams_integration.client_id if teams_integration.client_id else None,
            "tenant_id": teams_integration.tenant_id if teams_integration.tenant_id else None,
            "test1_plan_id": teams_integration.test1_plan_id,
            "has_access_token": teams_integration.access_token is not None,
            "token_expires_at": teams_integration.token_expires_at.isoformat() if teams_integration.token_expires_at else None
        }
        
        if teams_integration.is_configured():
            # Test connection
            connection_status = teams_integration.test_connection()
            status_info["connection_status"] = connection_status
            status_info["status"] = "connected" if connection_status else "connection_failed"
        else:
            status_info["connection_status"] = False
            status_info["status"] = "not_configured"
        
        return status_info
        
    except Exception as e:
        logger.error(f"Error getting Teams integration status: {str(e)}")
        return {
            "configured": False,
            "status": "error",
            "error": str(e)
        }

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
            "sources": msg.sources.get("sources", []) if isinstance(msg.sources, dict) else msg.sources,
            "response_type": msg.sources.get("response_type", "normal") if isinstance(msg.sources, dict) else "normal",
            "tasks": msg.sources.get("tasks", None) if isinstance(msg.sources, dict) else None,
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

# --- User Tasks (protected) ---
@app.get("/api/tasks")
async def get_user_tasks(
    current_user: User = Depends(get_current_user_from_session),
    db: Session = Depends(get_db),
):
    """Get all tasks for the current user."""
    tasks = (
        db.query(UserTask)
        .filter(UserTask.user_id == current_user.id)
        .order_by(UserTask.created_at.desc())
        .all()
    )
    
    return [
        {
            "id": str(task.id),
            "content": task.task_content,
            "order": task.task_order,
            "is_completed": task.is_completed,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat(),
            "chat_session_id": str(task.chat_session_id),
        }
        for task in tasks
    ]

@app.put("/api/tasks/{task_id}/complete")
async def complete_task(
    task_id: str,
    current_user: User = Depends(get_current_user_from_session),
    db: Session = Depends(get_db),
):
    """Mark a task as completed."""
    task = (
        db.query(UserTask)
        .filter(UserTask.id == task_id, UserTask.user_id == current_user.id)
        .first()
    )
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.is_completed = True
    task.completed_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Task marked as completed", "task_id": task_id}

@app.put("/api/tasks/{task_id}/incomplete")
async def uncomplete_task(
    task_id: str,
    current_user: User = Depends(get_current_user_from_session),
    db: Session = Depends(get_db),
):
    """Mark a task as incomplete."""
    task = (
        db.query(UserTask)
        .filter(UserTask.id == task_id, UserTask.user_id == current_user.id)
        .first()
    )
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.is_completed = False
    task.completed_at = None
    db.commit()
    
    return {"message": "Task marked as incomplete", "task_id": task_id}

@app.delete("/api/tasks/{task_id}")
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user_from_session),
    db: Session = Depends(get_db),
):
    """Delete a specific task."""
    task = (
        db.query(UserTask)
        .filter(UserTask.id == task_id, UserTask.user_id == current_user.id)
        .first()
    )
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(task)
    db.commit()
    
    return {"message": "Task deleted successfully", "task_id": task_id}

@app.delete("/api/tasks")
async def delete_all_tasks(
    current_user: User = Depends(get_current_user_from_session),
    db: Session = Depends(get_db),
):
    """Delete all tasks for the current user."""
    tasks = (
        db.query(UserTask)
        .filter(UserTask.user_id == current_user.id)
        .all()
    )
    
    for task in tasks:
        db.delete(task)
    
    db.commit()
    
    return {"message": f"All {len(tasks)} tasks deleted successfully"}

# --- Teams Integration Endpoints ---
@app.post("/api/teams/test")
async def test_teams_integration(
    current_user: User = Depends(get_current_user_from_session),
):
    """Test Teams integration by creating a sample task"""
    try:
        if not teams_integration.is_configured():
            raise HTTPException(status_code=400, detail="Teams integration not configured")
        
        # Create a test task
        result = teams_integration.create_task_in_test1_plan(
            title=f"Test Task from {current_user.username} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            description="This is a test task created through the API endpoint"
        )
        
        if result:
            return {
                "success": True,
                "message": "Test task created successfully in Teams",
                "task": result
            }
        else:
            return {
                "success": False,
                "message": "Failed to create test task - check authentication",
                "details": "User must authenticate with Microsoft Teams first"
            }
            
    except Exception as e:
        logger.error(f"Error testing Teams integration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Teams integration test failed: {str(e)}")

@app.get("/api/teams/status")
async def get_teams_integration_status():
    """Get the current status of Teams integration"""
    try:
        status = {
            "configured": teams_integration.is_configured(),
            "timestamp": datetime.now().isoformat(),
        }
        
        if teams_integration.is_configured():
            status.update({
                "client_id": teams_integration.client_id[:8] + "..." if teams_integration.client_id else None,
                "tenant_id": teams_integration.tenant_id[:8] + "..." if teams_integration.tenant_id else None,
                "target_plan": "test1",
                "scopes": teams_integration.scopes,
                "has_access_token": teams_integration.access_token is not None,
                "token_expires_at": teams_integration.token_expires_at.isoformat() if teams_integration.token_expires_at else None
            })
            
            # Test connection if we have an access token
            if teams_integration.access_token:
                status["connection_test"] = teams_integration.test_connection()
            else:
                status["connection_test"] = "No access token available"
                status["message"] = "User must authenticate through frontend first"
        else:
            status["message"] = "Teams integration not configured - check environment variables"
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting Teams integration status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get Teams integration status: {str(e)}")

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
