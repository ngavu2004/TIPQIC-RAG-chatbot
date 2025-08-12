# Authentication System Test Suite

This test suite provides comprehensive end-to-end testing for the TIPQIC RAG chatbot authentication system.

## 🧪 What This Tests

The test suite covers the complete authentication flow:

1. **Initial Page Load** - Verifies login page appears on startup
2. **User Registration** - Tests new user signup functionality
3. **User Login** - Tests existing user login
4. **Chat Interface Access** - Verifies authenticated users can access chat
5. **Page Reload Persistence** - Tests session persistence after browser refresh
6. **Logout Functionality** - Tests proper logout and session clearing
7. **Post-Logout State** - Verifies logout state persists after reload
8. **Multiple Browser Sessions** - Tests isolation between different browser sessions

## 📋 Prerequisites

1. **Chrome Browser** - Required for Selenium testing
2. **Python Dependencies** - Will be installed automatically
3. **Running Services** - API and Frontend must be running

## 🚀 Quick Start

### 1. Start Your Services

First, make sure your services are running:

```bash
# Terminal 1: Start API server
python api/main.py

# Terminal 2: Start Frontend server  
streamlit run frontend/app.py
```

### 2. Run the Tests

```bash
# Navigate to test directory
cd test_auth_system

# Run the test suite
python run_tests.py
```

## 📁 Test Structure

```
test_auth_system/
├── test_config.py          # Test configuration and utilities
├── test_auth_flow.py       # Main test suite
├── run_tests.py           # Test runner script
├── requirements.txt       # Test dependencies
├── README.md             # This file
└── screenshots/          # Test screenshots (auto-created)
```

## 🔧 Configuration

Edit `test_config.py` to customize:

- **Test URLs** - Frontend and API endpoints
- **Test Credentials** - Username/password for testing
- **Timeouts** - Wait times for elements
- **Headless Mode** - Set `headless: True` for background testing
- **Screenshot Directory** - Where to save test screenshots

## 📊 Test Results

The test suite provides detailed results:

- **Pass/Fail Status** for each test
- **Success Rate** percentage
- **Screenshots** at each test step
- **Debug Information** about page state

## 🐛 Debugging

### Screenshots
Screenshots are automatically saved in the `screenshots/` directory for each test step.

### Debug Output
The test suite provides detailed debug information:
- Current URL and page title
- Element presence/absence
- Test step descriptions

### Common Issues

1. **Services Not Running**
   - Ensure API server is on port 8000
   - Ensure Frontend server is on port 8501

2. **Chrome Driver Issues**
   - Make sure Chrome browser is installed
   - Test suite will automatically download ChromeDriver

3. **Element Not Found**
   - Check if the UI has changed
   - Verify selectors in `test_config.py`

## 🧹 Cleanup

The test suite creates a test user that you may want to clean up:

```sql
-- Connect to your PostgreSQL database and run:
DELETE FROM users WHERE username = 'testuser';
```

## 📝 Customization

### Adding New Tests

1. Add test method to `AuthFlowTester` class in `test_auth_flow.py`
2. Add test to the `tests` list in `run_all_tests()`
3. Follow the existing pattern for assertions and screenshots

### Modifying Test Data

Edit `TEST_CONFIG` in `test_config.py`:
```python
TEST_CONFIG = {
    "test_username": "your_test_user",
    "test_password": "your_test_password",
    # ... other settings
}
```

## 🎯 Test Coverage

This test suite ensures:

- ✅ **Authentication Flow** - Complete login/logout cycle
- ✅ **Session Persistence** - Login state survives page reloads
- ✅ **Session Isolation** - Multiple browsers don't interfere
- ✅ **UI State Management** - Correct pages shown at each step
- ✅ **Error Handling** - Graceful failure with debugging info

## 📞 Support

If tests fail:

1. Check the debug output for specific error messages
2. Review screenshots in the `screenshots/` directory
3. Verify services are running and accessible
4. Check that UI elements haven't changed 