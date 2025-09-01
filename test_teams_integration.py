import requests
import os
import base64
import json
from msal import PublicClientApplication
from datetime import datetime, timedelta

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed. Using system environment variables.")
except Exception as e:
    print(f"⚠️  Could not load .env file: {e}")

# Configuration - Read from environment variables
CLIENT_ID = os.getenv("MS_CLIENT_ID")
TENANT_ID = os.getenv("MS_TENANT_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Tasks.ReadWrite", "User.Read"]  # Delegated permissions

def decode_jwt_token(token):
    """Decode JWT token to see what permissions it has"""
    try:
        # Split the token into parts
        parts = token.split('.')
        if len(parts) != 3:
            print("❌ Invalid JWT token format")
            return None
        
        # Decode the payload (second part)
        payload = parts[1]
        # Add padding if needed
        payload += '=' * (4 - len(payload) % 4)
        
        # Decode base64
        decoded = base64.b64decode(payload)
        claims = json.loads(decoded)
        
        print("🔍 JWT Token Claims:")
        print(f"   App ID: {claims.get('appid', 'N/A')}")
        print(f"   App Name: {claims.get('app_displayname', 'N/A')}")
        print(f"   Tenant ID: {claims.get('tid', 'N/A')}")
        print(f"   Issued At: {datetime.fromtimestamp(claims.get('iat', 0))}")
        print(f"   Expires At: {datetime.fromtimestamp(claims.get('exp', 0))}")
        print(f"   Audience: {claims.get('aud', 'N/A')}")
        
        # Check for roles (application permissions)
        if 'roles' in claims:
            print(f"   Roles (Application Permissions): {claims['roles']}")
        else:
            print("   Roles: None (No application permissions)")
        
        # Check for scp (delegated permissions)
        if 'scp' in claims:
            print(f"   Scopes (Delegated Permissions): {claims['scp']}")
        else:
            print("   Scopes: None (No delegated permissions)")
        
        return claims
    except Exception as e:
        print(f"❌ Error decoding JWT token: {str(e)}")
        return None

def get_access_token():
    """Get access token for Microsoft Graph API using delegated permissions"""
    try:
        app = PublicClientApplication(
            CLIENT_ID, 
            authority=AUTHORITY
        )
        
        # Try to get token silently first (if user already logged in)
        accounts = app.get_accounts()
        if accounts:
            print(f"🔍 Found {len(accounts)} existing account(s)")
            result = app.acquire_token_silent(SCOPES, account=accounts[0])
            if result and 'access_token' in result:
                print("✅ Successfully obtained access token silently")
                return result['access_token']
        
        # If no silent token, do interactive login
        print("🔐 No existing session found. Please log in...")
        result = app.acquire_token_interactive(SCOPES)
        
        if 'access_token' in result:
            print("✅ Successfully obtained access token through login")
            return result['access_token']
        else:
            print(f"❌ Failed to get access token: {result.get('error_description', 'Unknown error')}")
            return None
    except Exception as e:
        print(f"❌ Error getting access token: {str(e)}")
        return None

def test_tasks_permission(access_token):
    """Test if Tasks.ReadWrite permission is working with delegated auth"""
    try:
        print("\n📋 Testing Tasks.ReadWrite permission...")
        
        print("🔍 With delegated permissions, we can access your personal data:")
        print("1. List your Microsoft Planner plans")
        print("2. Create tasks in your plans")
        print("3. Read your existing tasks")
        
        # First, let's check the token details
        print(f"\n🔑 Token details:")
        print(f"   Token length: {len(access_token)} characters")
        print(f"   Token starts with: {access_token[:20]}...")
        
        # Test 1: List Microsoft Planner plans
        print("\n🧪 Test 1: Listing your Microsoft Planner plans...")
        plans_response = requests.get(
            "https://graph.microsoft.com/v1.0/me/planner/plans",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        print(f"📝 Plans response status: {plans_response.status_code}")
        
        if plans_response.status_code == 200:
            plans = plans_response.json()
            print(f"✅ Successfully found {len(plans['value'])} plans:")
            
            # Find the "test1" plan specifically
            test1_plan = None
            for i, plan in enumerate(plans['value'], 1):
                print(f"  {i}. {plan['title']} (ID: {plan['id']})")
                if plan['title'] == 'test1':
                    test1_plan = plan
                    print(f"     🎯 Found target plan: {plan['title']}")
            
            # Test 2: Try to create a task only in the "test1" plan
            if test1_plan:
                print(f"\n🧪 Test 2: Creating a test task in plan '{test1_plan['title']}'...")
                
                # First, get buckets for this plan
                buckets_response = requests.get(
                    f"https://graph.microsoft.com/v1.0/planner/plans/{test1_plan['id']}/buckets",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if buckets_response.status_code == 200:
                    buckets = buckets_response.json()
                    if buckets['value']:
                        bucket = buckets['value'][0]
                        print(f"   Using bucket: {bucket['name']}")
                        
                        task_data = {
                            "planId": test1_plan['id'],
                            "bucketId": bucket['id'],
                            "title": f"Test Task from TIPQIC Bot - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                            "details": {
                                "description": "This is a test task created by the TIPQIC RAG Chatbot integration."
                            }
                        }
                        
                        create_response = requests.post(
                            "https://graph.microsoft.com/v1.0/planner/tasks",
                            headers={
                                "Authorization": f"Bearer {access_token}",
                                "Content-Type": "application/json"
                            },
                            json=task_data
                        )
                        
                        print(f"📝 Create task response status: {create_response.status_code}")
                        
                        if create_response.status_code == 201:
                            task = create_response.json()
                            print(f"🎉 SUCCESS! Created task: {task['title']}")
                            print(f"   Task ID: {task['id']}")
                            print(f"   Created: {task['createdDateTime']}")
                            return True
                        else:
                            print(f"❌ Failed to create task: {create_response.status_code}")
                            print(f"   Response: {create_response.text}")
                            return False
                    else:
                        print("⚠️ No buckets found in this plan")
                        return False
                else:
                    print(f"❌ Failed to get buckets: {buckets_response.status_code}")
                    return False
            else:
                print("⚠️ 'test1' plan not found")
                print("   Available plans:")
                for plan in plans['value']:
                    print(f"     - {plan['title']} (ID: {plan['id']})")
                return False
        else:
            print(f"❌ Failed to list plans: {plans_response.status_code}")
            print(f"   Response: {plans_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing tasks permission: {str(e)}")
        return None

def main():
    print("🔧 Microsoft Graph API - Test Tasks Permission")
    print("Reading configuration from environment variables...")
    print()
    
    # Check if configuration is set
    if not CLIENT_ID:
        print("❌ MS_CLIENT_ID environment variable not set")
    if not TENANT_ID:
        print("❌ MS_TENANT_ID environment variable not set")
    
    print()
    
    # Check if all required environment variables are set
    if not all([CLIENT_ID, TENANT_ID]):
        print("❌ Missing required environment variables. Please set:")
        print("   - MS_CLIENT_ID")
        print("   - MS_TENANT_ID")
        print("\nYou can set these in your .env file or export them in your shell.")
        return
    
    # Step 1: Get access token
    print("1️⃣ Getting access token...")
    access_token = get_access_token()
    if not access_token:
        print("❌ Cannot proceed without access token")
        return
    
    # Step 1.5: Decode the token to see what permissions it has
    print("\n🔍 Decoding JWT token to check permissions...")
    token_claims = decode_jwt_token(access_token)
    
    # Step 2: Test tasks permission
    print("\n2️⃣ Testing tasks permission...")
    success = test_tasks_permission(access_token)
    
    if success:
        print(f"\n🎉 SUCCESS! Basic connectivity working")
        print("=" * 50)
        print("✅ Tasks permission test completed successfully!")
        print("\n📋 Next steps:")
        print("1. Get a user ID from your organization")
        print("2. Get a To Do list ID for that user")
        print("3. We can then create test tasks in that user's To Do list")
    else:
        print("\n❌ FAILED! Could not test tasks permission")
        print("=" * 50)
        print("❌ Tasks permission test failed!")
        print("\n🔧 Troubleshooting:")
        print("1. Check your Azure App Registration permissions")
        print("2. Verify MS_CLIENT_ID, MS_CLIENT_SECRET, MS_TENANT_ID are correct")
        print("3. Ensure your app has Tasks.ReadWrite permission")
        print("4. Grant admin consent for the permissions")

if __name__ == "__main__":
    main()
