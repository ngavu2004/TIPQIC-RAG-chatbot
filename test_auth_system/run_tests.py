#!/usr/bin/env python3
"""
Simple test runner for authentication system
"""
import os
import sys
import subprocess
import time
import requests

def check_service(url, service_name, timeout=5):
    """Check if a service is running"""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            print(f"✅ {service_name} is running at {url}")
            return True
        else:
            print(f"❌ {service_name} is not responding properly at {url}")
            return False
    except requests.exceptions.RequestException:
        print(f"❌ {service_name} is not running at {url}")
        return False

def main():
    """Main test runner"""
    print("🧪 Authentication System Test Runner")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("test_auth_flow.py"):
        print("❌ Please run this script from the test_auth_system directory")
        sys.exit(1)
    
    # Check if services are running
    print("\n🔍 Checking if services are running...")
    
    api_running = check_service("http://localhost:8000/api/health", "API Server")
    frontend_running = check_service("http://localhost:8501", "Frontend Server")
    
    if not api_running or not frontend_running:
        print("\n❌ Required services are not running!")
        print("\nPlease start the services first:")
        print("1. Start API server: python api/main.py")
        print("2. Start Frontend server: streamlit run frontend/app.py")
        print("\nThen run this test again.")
        sys.exit(1)
    
    print("\n✅ All services are running!")
    
    # Install test dependencies if needed
    print("\n📦 Checking test dependencies...")
    try:
        import selenium
        import requests
        print("✅ Test dependencies are installed")
    except ImportError:
        print("❌ Test dependencies are missing")
        print("Installing test dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Test dependencies installed")
    
    # Run the tests
    print("\n🚀 Starting authentication flow tests...")
    print("=" * 50)
    
    try:
        from test_auth_flow import main as run_tests
        run_tests()
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        sys.exit(1)
    
    print("\n🎉 Test execution completed!")

if __name__ == "__main__":
    main() 