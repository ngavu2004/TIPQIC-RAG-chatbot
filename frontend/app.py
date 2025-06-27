import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional
import time

# Configure Streamlit page
st.set_page_config(
    page_title="TIPQIC RAG Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
    .user-message {
        background-color: #f0f2f6;
        border-left-color: #ff6b6b;
    }
    .bot-message {
        background-color: #e8f4fd;
        border-left-color: #1f77b4;
    }
    .source-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border: 1px solid #dee2e6;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

def check_api_health() -> bool:
    """Check if the API is running and healthy."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def get_api_stats() -> Optional[Dict]:
    """Get API statistics."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/stats", timeout=5)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException:
        pass
    return None

def send_chat_message(message: str, max_results: int = 5, include_sources: bool = True) -> Optional[Dict]:
    """Send a chat message to the API."""
    try:
        payload = {
            "message": message,
            "max_results": max_results,
            "include_sources": include_sources
        }
        response = requests.post(
            f"{API_BASE_URL}/api/chat",
            json=payload,
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error: {str(e)}")
    return None

def display_chat_message(message: str, is_user: bool = True):
    """Display a chat message with proper styling."""
    css_class = "user-message" if is_user else "bot-message"
    role = "👤 You" if is_user else "🤖 TIPQIC Bot"
    
    st.markdown(f"""
    <div class="chat-message {css_class}">
        <strong>{role}:</strong><br>
        {message}
    </div>
    """, unsafe_allow_html=True)

def display_sources(sources: List[Dict]):
    """Display source information in a formatted way."""
    if not sources:
        return
    
    st.markdown("### 📚 Sources")
    
    for i, source in enumerate(sources, 1):
        with st.expander(f"Source {i}: {source['filename']} (Page {source['page']}) - Score: {source['score']:.3f}"):
            st.markdown(f"**File:** {source['filename']}")
            st.markdown(f"**Page:** {source['page']}")
            st.markdown(f"**Relevance Score:** {source['score']:.3f}")
            st.markdown(f"**Preview:** {source['preview']}")

def main():
    # Header
    st.markdown('<h1 class="main-header">🤖 TIPQIC RAG Chatbot</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # API Health Check
        api_healthy = check_api_health()
        if api_healthy:
            st.success("✅ API is running")
        else:
            st.error("❌ API is not accessible")
            st.info("Make sure the FastAPI server is running on http://localhost:8000")
            st.code("python api/main.py")
        
        # Chat Settings
        st.subheader("Chat Settings")
        max_results = st.slider("Max Results", min_value=1, max_value=10, value=5)
        include_sources = st.checkbox("Include Sources", value=True)
        
        # API Stats
        st.subheader("📊 API Stats")
        if api_healthy:
            stats = get_api_stats()
            if stats:
                st.json(stats)
        
        # Clear Chat Button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            st.rerun()

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Main chat interface
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Display chat history
        for message in st.session_state.messages:
            if message["role"] == "user":
                display_chat_message(message["content"], is_user=True)
            else:
                display_chat_message(message["content"], is_user=False)
                if "sources" in message and message["sources"]:
                    display_sources(message["sources"])
        
        # Chat input
        if prompt := st.chat_input("Ask me anything about TIPQIC...", disabled=not api_healthy):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            display_chat_message(prompt, is_user=True)
            
            # Get bot response
            with st.spinner("🤔 Thinking..."):
                response = send_chat_message(prompt, max_results, include_sources)
            
            if response and response.get("success"):
                # Add bot response to chat history
                bot_message = {
                    "role": "assistant",
                    "content": response["response"],
                    "sources": response.get("sources", [])
                }
                st.session_state.messages.append(bot_message)
                
                # Display bot response
                display_chat_message(response["response"], is_user=False)
                if include_sources and response.get("sources"):
                    display_sources(response["sources"])
            
            elif response and not response.get("success"):
                error_msg = f"Error: {response.get('error_message', 'Unknown error')}"
                st.error(error_msg)
            else:
                st.error("Failed to get response from the chatbot. Please try again.")
    
    with col2:
        # Quick actions or example questions
        st.subheader("💡 Example Questions")
        example_questions = [
            "What is TIPQIC?",
            "How does the RAG system work?",
            "What are the main features?",
            "Tell me about the architecture",
            "How to get started?"
        ]
        
        for question in example_questions:
            if st.button(question, key=f"example_{question}", disabled=not api_healthy):
                # Add the example question as if user typed it
                st.session_state.messages.append({"role": "user", "content": question})
                st.rerun()

    # Footer
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

if __name__ == "__main__":
    main()