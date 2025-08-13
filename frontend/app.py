import streamlit as st
import requests
from typing import Dict, List, Optional
from streamlit_cookies_manager import EncryptedCookieManager

# ========== Page config ==========
st.set_page_config(
    page_title="TIPQIC RAG Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

# Light theme hint (optional)
st.markdown("""
<script>document.documentElement.setAttribute('data-theme','light');</script>
""", unsafe_allow_html=True)

# ========== Config ==========
API_BASE_URL = "http://localhost:8000"

# ========== Cookie manager ==========
cookies = EncryptedCookieManager(
    prefix="tipqic/",
    password='your-secret-key-change-in-production'
)

# ========== Single HTTP session (keeps backend cookie) ==========
def get_http() -> requests.Session:
    if "http" not in st.session_state:
        st.session_state.http = requests.Session()
        st.session_state.http.headers.update({
            'User-Agent': 'TIPQIC-Chatbot/1.0'
        })
    return st.session_state.http

# ========== API helpers (no tokens; cookie-based) ==========
def check_api_health() -> bool:
    try:
        r = get_http().get(f"{API_BASE_URL}/api/health", timeout=5)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False

def login_user(username: str, password: str) -> Dict:
    http = get_http()
    try:
        r = http.post(
            f"{API_BASE_URL}/api/auth/login",
            json={"username": username, "password": password},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            # Save resume token to browser storage
            if "resume_token" in data and cookies.ready():
                try:
                    cookies["resume_token"] = data["resume_token"]
                    cookies.save()
                except:
                    pass  # Cookie save failed, continue anyway
            return {"success": True, **data}
        return {"success": False, "error_message": f"{r.status_code} - {r.text}"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error_message": f"Connection Error: {e}"}

def logout_user() -> bool:
    try:
        r = get_http().post(f"{API_BASE_URL}/api/auth/logout", timeout=10)
        # FastAPI should delete the httpOnly cookie
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False

def signup_user(username: str, password: str, email: Optional[str]) -> Dict:
    try:
        r = get_http().post(
            f"{API_BASE_URL}/api/auth/signup",
            json={"username": username, "password": password, "email": email},
            timeout=10,
        )
        if r.status_code == 200:
            return {"success": True, **(r.json() if r.headers.get("content-type","").startswith("application/json") else {})}
        return {"success": False, "error_message": f"{r.status_code} - {r.text}"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error_message": f"Connection Error: {e}"}



def get_chat_sessions() -> List[Dict]:
    http = get_http()
    try:
        r = http.get(f"{API_BASE_URL}/api/chat/sessions", timeout=10)
        return r.json() if r.status_code == 200 else []
    except requests.exceptions.RequestException:
        return []

def get_chat_messages(session_id: str) -> List[Dict]:
    http = get_http()
    try:
        r = http.get(f"{API_BASE_URL}/api/chat/sessions/{session_id}/messages", timeout=10)
        return r.json() if r.status_code == 200 else []
    except requests.exceptions.RequestException:
        return []

def delete_chat_session(session_id: str) -> bool:
    http = get_http()
    try:
        r = http.delete(f"{API_BASE_URL}/api/chat/sessions/{session_id}", timeout=10)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False

def rename_chat_session(session_id: str, new_name: str) -> bool:
    http = get_http()
    try:
        r = http.put(
            f"{API_BASE_URL}/api/chat/sessions/{session_id}/rename",
            params={"new_name": new_name},
            timeout=10,
        )
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False

def send_chat_message(message: str, session_id: Optional[str], max_results: int, include_sources: bool) -> Optional[Dict]:
    http = get_http()
    try:
        r = http.post(
            f"{API_BASE_URL}/api/chat",
            json={
                "message": message,
                "chat_session_id": session_id,
                "max_results": max_results,
                "include_sources": include_sources,
            },
            timeout=30,
        )
        if r.status_code == 200:
            return r.json()
        else:
            st.error(f"API Error: {r.status_code} - {r.text}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error: {e}")
        return None

# ========== Auth ==========
def is_authenticated() -> bool:
    http = get_http()
    
    # Try to get current user info
    try:
        r = http.get(f"{API_BASE_URL}/api/auth/me", timeout=5)
        if r.status_code == 200:
            st.session_state.user = r.json()
            return True
    except requests.exceptions.RequestException:
        pass  # API unavailable, try resume

    # Try resume with resume_token stored in browser
    if cookies.ready():
        try:
            resume_token = cookies.get("resume_token")
            if resume_token:
                try:
                    rr = http.post(f"{API_BASE_URL}/api/auth/resume", json={"resume_token": resume_token}, timeout=5)
                    if rr.status_code == 200:
                        r2 = http.get(f"{API_BASE_URL}/api/auth/me", timeout=5)
                        if r2.status_code == 200:
                            st.session_state.user = r2.json()
                            return True
                except requests.exceptions.RequestException:
                    pass
        except:
            pass  # Cookie access failed
    
    st.session_state.user = None
    return False

def do_logout():
    http = get_http()
    try:
        http.post(f"{API_BASE_URL}/api/auth/logout", timeout=5)
    except: 
        pass
    try:
        http.cookies.clear()  # drop any local cookie jar
    except: 
        pass
    if cookies.ready():
        try:
            if "resume_token" in cookies:
                del cookies["resume_token"]
                cookies.save()
        except:
            pass  # Cookie clear failed, continue anyway
    for k in ("user", "auth_cache", "current_session_id", "messages"):
        st.session_state.pop(k, None)
    st.query_params.update({"page": "login"})
    st.rerun()

# ========== UI helpers ==========
def display_chat_message(message: str, is_user: bool = True):
    css_class = "user-message" if is_user else "bot-message"
    role = "👤 You" if is_user else "🤖 TIPQIC Bot"
    st.markdown(
        f"""
        <div class="chat-message {css_class}">
            <strong>{role}:</strong><br>{message}
        </div>
        """,
        unsafe_allow_html=True,
    )

def display_sources(sources: List[Dict]):
    if not sources:
        return
    st.markdown("### 📚 Sources")
    for i, source in enumerate(sources, 1):
        filename = source.get('filename', source.get('source', 'Unknown'))
        page = source.get('page', 'N/A')
        preview = source.get('preview', source.get('content', ''))
        score = source.get('score', None)
        with st.expander(f"Source {i}: {filename} (Page {page})"):
            st.markdown(f"**File:** {filename}")
            st.markdown(f"**Page:** {page}")
            if isinstance(score, (int, float)):
                st.markdown(f"**Relevance Score:** {score:.3f}")
            st.markdown(f"**Preview:** {preview}")

# ========== Pages ==========
def show_login_page():
    st.markdown('<h1 class="main-header">🔐 Authentication</h1>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])

    with tab1:
        st.subheader("Login to Your Account")
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submit_button = st.form_submit_button("Login")
            if submit_button:
                if username and password:
                    with st.spinner("Logging in..."):
                        result = login_user(username, password)
                    if result.get("success"):
                        # After login, /api/auth/me should succeed
                        st.session_state.pop("auth_cache", None)
                        st.success("Login successful! Redirecting to chat...")
                        st.query_params.update({"page": "main"})
                        st.rerun()
                    else:
                        st.error(f"Login failed: {result.get('error_message','Unknown error')}")
                else:
                    st.error("Please enter both username and password")

    with tab2:
        st.subheader("Create New Account")
        with st.form("signup_form"):
            new_username = st.text_input("Username", key="signup_username")
            new_password = st.text_input("Password", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
            email = st.text_input("Email (Optional)", key="signup_email")
            signup_submit = st.form_submit_button("Sign Up")
            if signup_submit:
                if new_username and new_password and confirm_password:
                    if new_password == confirm_password:
                        with st.spinner("Creating account..."):
                            result = signup_user(new_username, new_password, email)
                        if result.get("success"):
                            st.success("Account created! Please log in.")
                            st.query_params.update({"page": "login"})
                        else:
                            st.error(f"Signup failed: {result.get('error_message','Unknown error')}")
                    else:
                        st.error("Passwords do not match")
                else:
                    st.error("Please fill in all required fields")

def show_session_management():
    with st.sidebar:
        st.header("💬 Chat Sessions")
        if is_authenticated():
            sessions = get_chat_sessions()
        else:
            sessions = []
            st.info("Please log in to manage chat sessions")
            return

        if st.button("🆕 New Chat"):
            st.session_state.current_session_id = None
            st.session_state.messages = []
            st.rerun()

        st.markdown("---")

        if sessions:
            st.subheader("Your Sessions")
            for session in sessions:
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    if st.button(f"📝 {session['name']}", key=f"session_{session['id']}"):
                        st.session_state.current_session_id = session['id']
                        msgs = get_chat_messages(session['id'])
                        st.session_state.messages = [
                            {"role": m["role"], "content": m["content"], "sources": m.get("sources", [])}
                            for m in msgs
                        ]
                        st.rerun()
                with col2:
                    rename_key = f"renaming_{session['id']}"
                    if rename_key not in st.session_state:
                        st.session_state[rename_key] = False
                    if st.button("✏️", key=f"rename_{session['id']}", help="Rename session"):
                        st.session_state[rename_key] = True
                        st.rerun()
                    if st.session_state[rename_key]:
                        new_name = st.text_input("New name:", value=session['name'], key=f"rename_input_{session['id']}")
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.button("💾", key=f"save_rename_{session['id']}", help="Save"):
                                if new_name.strip():
                                    if rename_chat_session(session['id'], new_name.strip()):
                                        st.success("Session renamed!")
                                        st.session_state[rename_key] = False
                                        st.rerun()
                                    else:
                                        st.error("Failed to rename session")
                                else:
                                    st.error("Session name cannot be empty")
                        with col_cancel:
                            if st.button("❌", key=f"cancel_rename_{session['id']}", help="Cancel"):
                                st.session_state[rename_key] = False
                                st.rerun()
                with col3:
                    if st.button("🗑️", key=f"delete_{session['id']}", help="Delete session"):
                        if delete_chat_session(session['id']):
                            st.success("Session deleted!")
                            st.rerun()
        else:
            st.info("No chat sessions yet. Start a new chat!")

def show_user_info():
    with st.sidebar:
        st.header("👤 User Info")
        if is_authenticated():
            me = st.session_state.get("user")
            if me:
                st.write(f"**Username:** {me.get('username','')}")
                if me.get('email'):
                    st.write(f"**Email:** {me['email']}")
                created = me.get('created_at')
                if created:
                    st.write(f"**Member since:** {created[:10]}")
                if me.get('is_admin'):
                    st.success("👑 **Admin User**")
        else:
            st.write("**Not logged in**")

        st.markdown("---")

        if is_authenticated():
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚪 Logout"):
                    do_logout()
            with col2:
                me = st.session_state.get("user")
                if me and me.get('is_admin'):
                    if st.button("⚙️ Admin"):
                        st.query_params.update({"page": "admin"})
                        st.rerun()

def show_admin_page():
    st.markdown('<h1 class="main-header">⚙️ Admin Dashboard</h1>', unsafe_allow_html=True)
    
    me = st.session_state.get("user")
    if not me or not me.get('is_admin'):
        st.error("❌ Admin access required")
        st.info("You need admin privileges to access this page.")
        if st.button("← Back to Chat"):
            st.query_params.update({"page": "main"})
            st.rerun()
        return
    
    st.success(f"👑 Welcome, Admin {me.get('username')}!")
    
    # File Upload Section
    st.subheader("📁 File Upload to S3")
    st.info("Upload files to s3://tipchatbot/files/")
    
    # Tab for different upload methods
    upload_tab1, upload_tab2 = st.tabs(["📤 Direct Upload", "🗄️ Upload from Source"])
    
    with upload_tab1:
        st.subheader("Upload Local File")
        uploaded_file = st.file_uploader(
            "Choose a file to upload",
            type=['txt', 'pdf', 'doc', 'docx', 'csv', 'json', 'xml', 'md'],
            help="Select a file to upload to S3 bucket"
        )
        
        if uploaded_file is not None:
            st.write(f"**Selected file:** {uploaded_file.name}")
            st.write(f"**File size:** {uploaded_file.size} bytes")
            st.write(f"**File type:** {uploaded_file.type}")
            
            if st.button("🚀 Upload to S3"):
                with st.spinner("Uploading file to S3..."):
                    try:
                        # Prepare file for upload
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        
                        # Upload to backend
                        http = get_http()
                        response = http.post(
                            f"{API_BASE_URL}/api/admin/upload-file",
                            files=files,
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"✅ {result['message']}")
                            st.info(f"**S3 Key:** {result['s3_key']}")
                            st.info(f"**Uploaded by:** {result['uploaded_by']}")
                            st.info(f"**Timestamp:** {result['timestamp']}")
                        else:
                            st.error(f"❌ Upload failed: {response.status_code} - {response.text}")
                            
                    except Exception as e:
                        st.error(f"❌ Upload error: {str(e)}")
    
    with upload_tab2:
        st.subheader("Upload from File Source")
        
        # Get available sources
        try:
            http = get_http()
            response = http.get(f"{API_BASE_URL}/api/admin/available-sources", timeout=10)
            if response.status_code == 200:
                sources_data = response.json()
                available_sources = sources_data.get("sources", [])
            else:
                available_sources = ["local"]  # Fallback
        except:
            available_sources = ["local"]  # Fallback
        
        source_name = st.selectbox(
            "Select file source",
            available_sources,
            help="Choose the source to upload files from"
        )
        
        if source_name:
            # List files from selected source
            try:
                response = http.get(f"{API_BASE_URL}/api/admin/list-source-files/{source_name}", timeout=10)
                if response.status_code == 200:
                    files_data = response.json()
                    source_files = files_data.get("files", [])
                    
                    if source_files:
                        st.write(f"**Available files in {source_name}:**")
                        file_options = [f"{f['filename']} ({f['size']} bytes)" for f in source_files]
                        selected_file_info = st.selectbox("Select file to upload", file_options)
                        
                        if selected_file_info:
                            # Extract filename from selection
                            selected_filename = selected_file_info.split(" (")[0]
                            
                            # Optional S3 filename override
                            s3_filename = st.text_input(
                                "S3 filename (optional, leave empty to use original)",
                                value=selected_filename,
                                help="Custom filename for S3 (optional)"
                            )
                            
                            if st.button("🚀 Upload from Source"):
                                with st.spinner(f"Uploading {selected_filename} from {source_name}..."):
                                    try:
                                        response = http.post(
                                            f"{API_BASE_URL}/api/admin/upload-from-source",
                                            params={
                                                "source_name": source_name,
                                                "file_identifier": selected_filename,
                                                "s3_filename": s3_filename if s3_filename != selected_filename else None
                                            },
                                            timeout=30
                                        )
                                        
                                        if response.status_code == 200:
                                            result = response.json()
                                            st.success(f"✅ {result['message']}")
                                            st.info(f"**S3 Key:** {result['s3_key']}")
                                            st.info(f"**Source:** {result['source']}")
                                            st.info(f"**Uploaded by:** {result['uploaded_by']}")
                                            st.info(f"**Timestamp:** {result['timestamp']}")
                                        else:
                                            st.error(f"❌ Upload failed: {response.status_code} - {response.text}")
                                            
                                    except Exception as e:
                                        st.error(f"❌ Upload error: {str(e)}")
                    else:
                        st.info(f"No files found in {source_name} source")
                else:
                    st.error(f"Failed to list files from {source_name}")
            except Exception as e:
                st.error(f"Error accessing {source_name}: {str(e)}")
    
    st.markdown("---")
    
    # Admin dashboard content
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 System Statistics")
        st.info("Statistics will be implemented here...")
        
        if st.button("🔄 Refresh Stats"):
            st.info("Stats refresh functionality coming soon...")
    
    with col2:
        st.subheader("👥 User Management")
        st.info("User management features coming soon...")
        
        if st.button("👤 Manage Users"):
            st.info("User management interface coming soon...")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📝 Chat Sessions"):
            st.info("Chat session management coming soon...")
    with col2:
        if st.button("🗄️ Database"):
            st.info("Database management coming soon...")
    with col3:
        if st.button("🔧 Settings"):
            st.info("System settings coming soon...")
    
    st.markdown("---")
    
    if st.button("← Back to Chat"):
        st.query_params.update({"page": "main"})
        st.rerun()

def show_chat_interface():
    api_healthy = check_api_health()

    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.markdown('<h1 class="main-header">🤖 TIVA</h1>', unsafe_allow_html=True)

    if is_authenticated():
        if st.session_state.current_session_id:
            sessions = get_chat_sessions()
            current_session = next((s for s in sessions if s['id'] == st.session_state.current_session_id), None)
            st.markdown(f"**Current Session:** {current_session['name'] if current_session else 'New Chat'}")
        else:
            st.markdown("**Current Session:** New Chat")

    show_user_info()
    show_session_management()

    with st.sidebar:
        st.markdown("---")
        st.header("⚙️ Chat Settings")
        max_results = st.slider("Max Results", min_value=1, max_value=10, value=5)
        include_sources = st.checkbox("Include Sources", value=True)
        if st.button("🗑️ Clear Current Chat"):
            st.session_state.messages = []
            st.rerun()

    if is_authenticated():
        for msg in st.session_state.messages:
            display_chat_message(msg["content"], is_user=(msg["role"] == "user"))
            if msg.get("sources"):
                display_sources(msg["sources"])

    if is_authenticated():
        if prompt := st.chat_input("Ask me anything about TIPQIC...", disabled=not api_healthy):
            st.session_state.messages.append({"role": "user", "content": prompt})
            display_chat_message(prompt, is_user=True)
            with st.spinner("🤔 Thinking..."):
                resp = send_chat_message(
                    prompt,
                    st.session_state.current_session_id,
                    max_results,
                    include_sources
                )
            if resp and resp.get("success"):
                bot_msg = {
                    "role": "assistant",
                    "content": resp["response"],
                    "sources": resp.get("sources", [])
                }
                st.session_state.messages.append(bot_msg)
                display_chat_message(resp["response"], is_user=False)
                if include_sources and resp.get("sources"):
                    display_sources(resp["sources"])
                st.rerun()
            elif resp and not resp.get("success"):
                st.error(f"Error: {resp.get('error_message','Unknown error')}")
            else:
                st.error("Failed to get response from the chatbot. Please try again.")
    else:
        st.info("🔐 Please log in to start chatting!")

    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            Made with ❤️ using Streamlit and FastAPI |
            <a href="http://localhost:8000/docs" target="_blank">API Docs</a>
        </div>
        """,
        unsafe_allow_html=True
    )

def main():
    # Wait for cookies to be ready
    if not cookies.ready():
        st.info("🔄 Initializing...")
        st.stop()

    if not check_api_health():
        st.error("❌ API is not accessible")
        st.info("Make sure the FastAPI server is running on http://localhost:8000")
        st.code("python api/main.py")
        return

    # Initialize session state
    if "http" not in st.session_state:
        st.session_state.http = requests.Session()
        st.session_state.http.headers.update({
            'User-Agent': 'TIPQIC-Chatbot/1.0'
        })

    current_page = st.query_params.get("page", "main")

    if is_authenticated():
        me = st.session_state.get("user")
        if current_page == "login":
            st.query_params.update({"page": "main"})
            st.rerun()
        elif current_page == "admin":
            if me and me.get('is_admin'):
                show_admin_page()
            else:
                st.error("❌ Admin access required")
                st.query_params.update({"page": "main"})
                st.rerun()
        else:
            show_chat_interface()
    else:
        if current_page in ["main", "admin"]:
            st.query_params.update({"page": "login"})
            st.rerun()
        else:
            show_login_page()

if __name__ == "__main__":
    main()
