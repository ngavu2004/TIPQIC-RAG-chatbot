import os
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from msal import PublicClientApplication
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TeamsIntegration:
    """Microsoft Teams Planner integration for creating tasks using delegated permissions"""
    
    def __init__(self):
        self.client_id = os.getenv("MS_CLIENT_ID")
        self.tenant_id = os.getenv("MS_TENANT_ID")
        self.test1_plan_id = os.getenv("MS_PLAN_ID", "yMANgBto5k2ofB5NUQb9NmQAHeN1")
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.scopes = ["Tasks.ReadWrite", "User.Read"]
        
        # Initialize MSAL app
        self.app = None
        self.access_token = None
        self.token_expires_at = None
        
        if self.client_id and self.tenant_id:
            self.app = PublicClientApplication(
                client_id=self.client_id,
                authority=self.authority
            )
            logger.info("Teams integration initialized successfully")
        else:
            logger.warning("Teams integration not configured - missing environment variables")
    
    def is_configured(self) -> bool:
        """Check if Teams integration is properly configured"""
        return self.app is not None and self.client_id and self.tenant_id
    
    def get_access_token(self) -> Optional[str]:
        """Get access token for Microsoft Graph API using delegated permissions"""
        try:
            if not self.app:
                logger.error("MSAL app not initialized")
                return None
            
            # Check if we have a valid token
            if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
                logger.debug("Using existing access token")
                return self.access_token
            
            # Try to get token silently first (if user already logged in)
            accounts = self.app.get_accounts()
            if accounts:
                logger.info(f"Found {len(accounts)} existing account(s)")
                result = self.app.acquire_token_silent(self.scopes, account=accounts[0])
                if result and 'access_token' in result:
                    self.access_token = result['access_token']
                    self.token_expires_at = datetime.fromtimestamp(result['expires_in'] + datetime.now().timestamp())
                    logger.info("Successfully obtained access token silently")
                    return self.access_token
            
            # If no silent token, do interactive login at startup
            logger.info("No existing session found. Starting interactive login...")
            logger.info("Please complete the authentication in your browser...")
            
            result = self.app.acquire_token_interactive(self.scopes)
            
            if 'access_token' in result:
                self.access_token = result['access_token']
                self.token_expires_at = datetime.fromtimestamp(result['expires_in'] + datetime.now().timestamp())
                logger.info("✅ Successfully obtained access token through interactive login")
                return self.access_token
            else:
                logger.error(f"❌ Failed to get access token: {result.get('error_description', 'Unknown error')}")
                return None
            
        except Exception as e:
            logger.error(f"Error getting access token: {str(e)}")
            return None
    
    def create_task_in_test1_plan(self, title: str, description: str = "", due_date: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """Create a task in the test1 plan"""
        try:
            if not self.is_configured():
                logger.warning("Teams integration not configured")
                return None
            
            access_token = self.get_access_token()
            if not access_token:
                logger.info("No access token available - user must authenticate through frontend first")
                return None
            
            # First, verify we can access the test1 plan
            logger.info("Verifying access to test1 plan...")
            plans_response = requests.get(
                "https://graph.microsoft.com/v1.0/me/planner/plans",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if plans_response.status_code != 200:
                logger.error(f"Failed to list plans: {plans_response.status_code} - {plans_response.text}")
                return None
            
            plans = plans_response.json()
            test1_plan = None
            
            # Find the "test1" plan specifically
            for plan in plans['value']:
                if plan['title'] == 'test1':
                    test1_plan = plan
                    logger.info(f"Found target plan: {plan['title']} (ID: {plan['id']})")
                    break
            
            if not test1_plan:
                logger.error("test1 plan not found in user's plans")
                return None
            
            # Get buckets for the test1 plan
            buckets_response = requests.get(
                f"https://graph.microsoft.com/v1.0/planner/plans/{test1_plan['id']}/buckets",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if buckets_response.status_code != 200:
                logger.error(f"Failed to get buckets: {buckets_response.status_code} - {buckets_response.text}")
                return None
            
            buckets = buckets_response.json()
            if not buckets['value']:
                logger.error("No buckets found in test1 plan")
                return None
            
            # Use the first bucket (usually "To do")
            bucket = buckets['value'][0]
            logger.info(f"Using bucket: {bucket['name']}")
            
            # Prepare task data
            task_data = {
                "planId": test1_plan['id'],
                "bucketId": bucket['id'],
                "title": title,
                "details": {
                    "description": description
                }
            }
            
            # Add due date if provided
            if due_date:
                task_data["dueDateTime"] = due_date.isoformat() + "Z"
            
            # Create the task
            create_response = requests.post(
                "https://graph.microsoft.com/v1.0/planner/tasks",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=task_data
            )
            
            if create_response.status_code == 201:
                task = create_response.json()
                logger.info(f"✅ Successfully created task in Teams: {task['title']} (ID: {task['id']})")
                return {
                    "teams_task_id": task['id'],
                    "title": task['title'],
                    "created": task['createdDateTime'],
                    "plan": "test1",
                    "bucket": bucket['name']
                }
            else:
                logger.error(f"Failed to create task: {create_response.status_code} - {create_response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating task in Teams: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """Test the Teams integration connection"""
        try:
            if not self.is_configured():
                logger.debug("Teams integration not configured")
                return False
            
            access_token = self.get_access_token()
            if not access_token:
                logger.debug("No access token available for connection test")
                return False
            
            # Try to get the test1 plan details
            response = requests.get(
                f"https://graph.microsoft.com/v1.0/planner/plans/{self.test1_plan_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                plan = response.json()
                logger.info(f"✅ Teams integration test successful - connected to plan: {plan['title']}")
                return True
            else:
                logger.debug(f"Teams integration test failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.debug(f"Teams integration test error: {str(e)}")
            return False

# Create global instance
teams_integration = TeamsIntegration() 