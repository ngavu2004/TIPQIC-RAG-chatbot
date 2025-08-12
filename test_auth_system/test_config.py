"""
Test configuration for authentication system testing
"""
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Test Configuration
TEST_CONFIG = {
    "frontend_url": "http://localhost:8501",
    "api_url": "http://localhost:8000",
    "api_health_endpoint": "/api/health",  # Correct health endpoint
    "test_username": "sata2",
    "test_password": "Qwertyuiop123#",
    "timeout": 2,  # Balanced between speed and reliability
    "headless": False,  # Set to True for headless testing
    "screenshot_dir": "screenshots",
    "take_screenshots": False,  # Set to True to enable screenshots
    "debug_mode": False  # Set to False for faster execution
}

# Create screenshot directory
os.makedirs(TEST_CONFIG["screenshot_dir"], exist_ok=True)

def setup_driver():
    """Setup Chrome driver with options"""
    chrome_options = Options()
    if TEST_CONFIG["headless"]:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(TEST_CONFIG["timeout"])
    return driver

def take_screenshot(driver, name):
    """Take a screenshot and save it"""
    timestamp = int(time.time())
    filename = f"{TEST_CONFIG['screenshot_dir']}/{name}_{timestamp}.png"
    driver.save_screenshot(filename)
    print(f"Screenshot saved: {filename}")
    return filename

def wait_for_element(driver, by, value, timeout=None):
    """Wait for element to be present and visible"""
    if timeout is None:
        timeout = TEST_CONFIG["timeout"]
    
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        print(f"Timeout waiting for element: {value}")
        return None

def wait_for_element_clickable(driver, by, value, timeout=None):
    """Wait for element to be clickable"""
    if timeout is None:
        timeout = TEST_CONFIG["timeout"]
    
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        return element
    except TimeoutException:
        print(f"Timeout waiting for clickable element: {value}")
        return None

def check_element_exists(driver, by, value):
    """Check if element exists without waiting"""
    try:
        driver.find_element(by, value)
        return True
    except NoSuchElementException:
        return False

def print_debug_info(driver, step_name):
    """Print debug information about current page state"""
    print(f"\n=== {step_name} ===")
    print(f"Current URL: {driver.current_url}")
    print(f"Page Title: {driver.title}")
    
    # Check for common elements
    elements_to_check = [
        ("Login Form", "input[placeholder*='Username']"),
        ("Password Field", "input[type='password']"),
        ("Login Button", "button"),
        ("Chat Input", "input[placeholder*='Ask me anything']"),
        ("Logout Button", "button"),
        ("User Info", "div")
    ]
    
    for element_name, selector in elements_to_check:
        exists = check_element_exists(driver, By.CSS_SELECTOR, selector)
        print(f"{element_name}: {'✓' if exists else '✗'}")
    
    print("=" * 50) 