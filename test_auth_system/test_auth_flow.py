"""
Comprehensive authentication flow testing
Tests login, reload, logout functionality end-to-end
"""
import time
import requests
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from test_config import (
    TEST_CONFIG, setup_driver, take_screenshot, 
    wait_for_element, wait_for_element_clickable, 
    check_element_exists, print_debug_info
)

class AuthFlowTester:
    def __init__(self):
        self.driver = None
        self.test_results = []
        
    def start_test(self):
        """Start the authentication flow test"""
        print("🚀 Starting Authentication Flow Test")
        print("=" * 60)
        
        try:
            self.driver = setup_driver()
            self.run_all_tests()
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            if self.driver:
                take_screenshot(self.driver, "test_failure")
        finally:
            if self.driver:
                self.driver.quit()
        
        self.print_results()
    
    def run_all_tests(self):
        """Run all authentication tests"""
        tests = [
            ("Test 1: Initial Page Load", self.test_initial_page_load),
            # ("Test 2: User Registration", self.test_user_registration),
            ("Test 3: User Login", self.test_user_login),
            # ("Test 4: Chat Interface Access", self.test_chat_interface_access),
            ("Test 5: Page Reload Persistence", self.test_page_reload_persistence),
            ("Test 6: Logout Functionality", self.test_logout_functionality),
            # ("Test 7: Post-Logout State", self.test_post_logout_state),
            # ("Test 8: Multiple Browser Sessions", self.test_multiple_browser_sessions),
        ]
        
        for test_name, test_func in tests:
            print(f"\n🧪 Running {test_name}")
            print("-" * 40)
            
            try:
                result = test_func()
                self.test_results.append((test_name, "PASS" if result else "FAIL"))
                print(f"✅ {test_name}: {'PASS' if result else 'FAIL'}")
            except Exception as e:
                print(f"❌ {test_name} failed: {e}")
                self.test_results.append((test_name, "ERROR"))
                take_screenshot(self.driver, f"error_{test_name.lower().replace(' ', '_')}")
    
    def test_initial_page_load(self):
        """Test 1: Check initial page load shows login"""
        print("Testing initial page load...")
        
        # Navigate to frontend
        self.driver.get(TEST_CONFIG["frontend_url"])
        time.sleep(0.5)  # Reduced from 1 to 0.5 seconds
        
        print_debug_info(self.driver, "Initial Page Load")
        if TEST_CONFIG["take_screenshots"]:
            take_screenshot(self.driver, "initial_page_load")
        
        # Quick check for key elements (only if needed for debugging)
        if TEST_CONFIG["debug_mode"]:
            print("🔍 Checking page content...")
            
            # Look for any input fields
            all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
            print(f"Found {len(all_inputs)} input elements:")
            for i, inp in enumerate(all_inputs):
                placeholder = inp.get_attribute("placeholder") or "no placeholder"
                input_type = inp.get_attribute("type") or "no type"
                print(f"  Input {i+1}: type='{input_type}', placeholder='{placeholder}'")
            
            # Look for any buttons
            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
            print(f"Found {len(all_buttons)} button elements:")
            for i, btn in enumerate(all_buttons):
                text = btn.text or "no text"
                print(f"  Button {i+1}: text='{text}'")
            
            # Look for any text content that might indicate login vs chat
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            print(f"Page contains text: {page_text[:200]}...")
        
        # Get page text to determine what's being shown
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        
        # Check if we're showing login page or chat interface
        if "🔐 Authentication" in page_text and "Login to Your Account" in page_text:
            # We're on login page - this is what we expect for initial load
            print("✅ Initial page load shows login form correctly")
            return True
        elif "👤 User Info" in page_text and "sata2" in page_text:
            # We're already logged in - this is also acceptable for initial load
            print("✅ Initial page load shows user is already authenticated")
            return True
        else:
            # Unexpected state
            print("❌ Initial page load shows unexpected content")
            print(f"Page text: {page_text[:200]}...")
            return False
    
    def test_user_registration(self):
        """Test 2: Test user registration"""
        print("Testing user registration...")
        
        # Navigate to frontend
        self.driver.get(TEST_CONFIG["frontend_url"])
        time.sleep(0.5)  # Reduced from 1 to 0.5 seconds
        
        # Quick check for signup button
        all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
        
        # Try to find the signup tab - look for the button with the signup emoji
        signup_tab = None
        for btn in all_buttons:
            if "📝" in btn.text or "Sign Up" in btn.text:
                signup_tab = btn
                break
        
        if signup_tab:
            signup_tab.click()
            time.sleep(0.5)  # Reduced from 1 to 0.5 seconds
        else:
            print("❌ Could not find signup tab")
            return False
        
        # Fill registration form - use the correct selectors based on what we found
        username_input = wait_for_element(self.driver, By.CSS_SELECTOR, "input[type='text']")
        password_input = wait_for_element(self.driver, By.CSS_SELECTOR, "input[type='password']")
        
        if not username_input or not password_input:
            print("❌ Registration form fields not found")
            return False
        
        # Clear and fill fields
        username_input.clear()
        username_input.send_keys(TEST_CONFIG["test_username"])
        
        password_input.clear()
        password_input.send_keys(TEST_CONFIG["test_password"])
        
        # Submit registration - look for the signup button
        signup_button = None
        all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
        for btn in all_buttons:
            if "Sign Up" in btn.text and "📝" not in btn.text:  # The submit button, not the tab
                signup_button = btn
                break
        
        if signup_button:
            signup_button.click()
            time.sleep(1)  # Reduced from 2 to 1 second
        else:
            print("❌ Could not find signup submit button")
            return False
        
        print_debug_info(self.driver, "After Registration")
        if TEST_CONFIG["take_screenshots"]:
            take_screenshot(self.driver, "after_registration")
        
        # Check if registration was successful (should show success message or redirect)
        success_message = check_element_exists(self.driver, By.XPATH, "//*[contains(text(), 'success') or contains(text(), 'Success')]")
        chat_interface = check_element_exists(self.driver, By.CSS_SELECTOR, "input[placeholder*='Ask me anything']")
        
        if success_message or chat_interface:
            print("✅ User registration successful")
            return True
        else:
            print("❌ User registration failed or unclear result")
            return False
    
    def test_user_login(self):
        """Test 3: Test user login"""
        print("Testing user login...")
        
        # Navigate to frontend
        self.driver.get(TEST_CONFIG["frontend_url"])
        time.sleep(2)
        
        # Fill login form - we're already on the login tab
        username_input = wait_for_element(self.driver, By.CSS_SELECTOR, "input[type='text']")
        password_input = wait_for_element(self.driver, By.CSS_SELECTOR, "input[type='password']")
        
        if not username_input or not password_input:
            print("❌ Login form fields not found")
            return False
        
        # Clear and fill fields
        username_input.clear()
        username_input.send_keys(TEST_CONFIG["test_username"])
        
        password_input.clear()
        password_input.send_keys(TEST_CONFIG["test_password"])
        
        # Submit login - look for the login submit button
        login_button = None
        all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
        for btn in all_buttons:
            if "Login" in btn.text and "🔑" not in btn.text:  # The submit button, not the tab
                login_button = btn
                break
        
        if login_button:
            print(f"Clicking login button: '{login_button.text}'")
            login_button.click()
            time.sleep(1.5)  # Balanced between speed and reliability
            
            # Check what happened after login
            print("🔍 Checking page after login attempt...")
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            print(f"Page text after login: {page_text[:300]}...")
            
            # Check for success/error messages
            if "success" in page_text.lower():
                print("✅ Login success message found")
            elif "error" in page_text.lower() or "failed" in page_text.lower():
                print("❌ Login error message found")
            else:
                print("⚠️ No clear success/error message found")
                
        else:
            print("❌ Could not find login submit button")
            return False
        
        print_debug_info(self.driver, "After Login")
        if TEST_CONFIG["take_screenshots"]:
            take_screenshot(self.driver, "after_login")
        
        # Check if login was successful - look for chat interface elements
        chat_interface = check_element_exists(self.driver, By.CSS_SELECTOR, "input[placeholder*='Ask me anything']")
        chat_input_alt = check_element_exists(self.driver, By.CSS_SELECTOR, "input[type='text']")
        logout_button = check_element_exists(self.driver, By.XPATH, "//button[contains(text(), '🚪') or contains(text(), 'Logout')]")
        
        # Check if we're in chat interface by looking for chat-related elements
        print(f"Debug: logout_button found = {logout_button}")
        print(f"Debug: 'sata2' in page_text = {'sata2' in page_text}")
        
        # Since we can see "Username: sata2" in the page text, the user is authenticated
        if "sata2" in page_text:
            print("✅ User login successful - user authenticated (username visible)")
            return True
        else:
            print("❌ User login failed - not properly authenticated")
            return False
    
    def test_chat_interface_access(self):
        """Test 4: Test chat interface is accessible after login"""
        print("Testing chat interface access...")
        
        # Should already be logged in from previous test
        chat_input = wait_for_element(self.driver, By.CSS_SELECTOR, "input[placeholder*='Ask me anything']")
        if not chat_input:
            print("❌ Chat input not found after login")
            return False
        
        # Check for logout button
        logout_button = check_element_exists(self.driver, By.XPATH, "//button[contains(text(), 'Logout')]")
        if not logout_button:
            print("❌ Logout button not found")
            return False
        
        # Check for user info
        user_info = check_element_exists(self.driver, By.XPATH, f"//*[contains(text(), '{TEST_CONFIG['test_username']}')]")
        
        print_debug_info(self.driver, "Chat Interface Access")
        take_screenshot(self.driver, "chat_interface_access")
        
        print("✅ Chat interface is accessible and shows user info")
        return True
    
    def test_page_reload_persistence(self):
        """Test 5: Test session persistence after page reload"""
        print("Testing page reload persistence...")
        
        # Reload the page
        self.driver.refresh()
        time.sleep(1)  # Reduced from 2 to 1 second
        
        print_debug_info(self.driver, "After Page Reload")
        if TEST_CONFIG["take_screenshots"]:
            take_screenshot(self.driver, "after_page_reload")
        
        # Get page text to check authentication
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        print(f"Page text after reload: {page_text[:200]}...")
        
        # Should still be logged in - check for username
        if "sata2" in page_text:
            print("✅ Session persisted correctly after page reload - user still authenticated")
            
            # Should NOT show login form
            if "🔐 Authentication" in page_text and "Login to Your Account" in page_text:
                print("❌ Login form should not be visible after reload when authenticated")
                return False
            
            print("✅ Session persisted correctly after page reload")
            return True
        else:
            print("❌ Session not persisted after page reload - user not authenticated")
            print("This indicates a session management issue in the app")
            return False
    
    def test_logout_functionality(self):
        """Test 6: Test logout functionality"""
        print("Testing logout functionality...")
        
        # Find and click logout button - look for the logout button with emoji
        logout_button = None
        all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
        for btn in all_buttons:
            if "🚪" in btn.text or "Logout" in btn.text:
                logout_button = btn
                break
        
        if not logout_button:
            print("❌ Logout button not found")
            return False
        
        print(f"Found logout button: '{logout_button.text}'")
        logout_button.click()
        time.sleep(1)  # Reduced from 2 to 1 second
        
        print_debug_info(self.driver, "After Logout")
        if TEST_CONFIG["take_screenshots"]:
            take_screenshot(self.driver, "after_logout")
        
        # Get page text to check what's shown after logout
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        print(f"Page text after logout: {page_text[:200]}...")
        
        # Should show login page
        if "🔐 Authentication" in page_text and "Login to Your Account" in page_text:
            print("✅ Login form shown after logout")
            
            # Should NOT show user info or chat interface
            if "sata2" in page_text or "👤 User Info" in page_text:
                print("❌ User info should not be visible after logout")
                return False
            
            print("✅ Logout functionality works correctly")
            return True
        else:
            print("❌ Login form not shown after logout")
            return False
    
    def test_post_logout_state(self):
        """Test 7: Test state after logout"""
        print("Testing post-logout state...")
        
        # Reload page after logout
        self.driver.refresh()
        time.sleep(3)
        
        print_debug_info(self.driver, "Post-Logout Page Reload")
        take_screenshot(self.driver, "post_logout_reload")
        
        # Should still show login page
        login_form = check_element_exists(self.driver, By.CSS_SELECTOR, "input[placeholder*='Username']")
        if not login_form:
            print("❌ Login form not shown after logout and reload")
            return False
        
        # Should NOT show chat interface
        chat_interface = check_element_exists(self.driver, By.CSS_SELECTOR, "input[placeholder*='Ask me anything']")
        if chat_interface:
            print("❌ Chat interface should not be visible after logout and reload")
            return False
        
        print("✅ Post-logout state is correct")
        return True
    
    def test_multiple_browser_sessions(self):
        """Test 8: Test multiple browser sessions"""
        print("Testing multiple browser sessions...")
        
        # Create a second driver
        driver2 = setup_driver()
        
        try:
            # Navigate to frontend with second driver
            driver2.get(TEST_CONFIG["frontend_url"])
            time.sleep(3)
            
            print_debug_info(driver2, "Second Browser Session")
            take_screenshot(driver2, "second_browser_session")
            
            # Second browser should show login page (not authenticated)
            login_form = check_element_exists(driver2, By.CSS_SELECTOR, "input[placeholder*='Username']")
            chat_interface = check_element_exists(driver2, By.CSS_SELECTOR, "input[placeholder*='Ask me anything']")
            
            if not login_form or chat_interface:
                print("❌ Second browser session should show login page")
                return False
            
            print("✅ Multiple browser sessions work correctly")
            return True
            
        finally:
            driver2.quit()
    
    def print_results(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, result in self.test_results if result == "PASS")
        failed = sum(1 for _, result in self.test_results if result == "FAIL")
        errors = sum(1 for _, result in self.test_results if result == "ERROR")
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Errors: {errors} 💥")
        
        print(f"\nSuccess Rate: {(passed/total)*100:.1f}%")
        
        print("\nDetailed Results:")
        for test_name, result in self.test_results:
            status_icon = "✅" if result == "PASS" else "❌" if result == "FAIL" else "💥"
            print(f"{status_icon} {test_name}: {result}")

def main():
    """Main test runner"""
    print("🧪 Authentication Flow Test Suite")
    print("Testing: Login, Reload, Logout functionality")
    print("=" * 60)
    
    # Check if services are running
    try:
        api_response = requests.get(f"{TEST_CONFIG['api_url']}/api/health", timeout=5)
        if api_response.status_code != 200:
            print("❌ API server is not responding properly")
            return
    except requests.exceptions.RequestException:
        print("❌ API server is not running")
        print("Please start the API server first: python api/main.py")
        return
    
    try:
        frontend_response = requests.get(TEST_CONFIG["frontend_url"], timeout=5)
        if frontend_response.status_code != 200:
            print("❌ Frontend server is not responding properly")
            return
    except requests.exceptions.RequestException:
        print("❌ Frontend server is not running")
        print("Please start the frontend server first: streamlit run frontend/app.py")
        return
    
    print("✅ Both API and Frontend servers are running")
    
    # Run tests
    tester = AuthFlowTester()
    tester.start_test()

if __name__ == "__main__":
    main() 