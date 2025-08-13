# Scripts Directory

This directory contains utility scripts for the TIPQIC RAG Chatbot system.

## Available Scripts

### `create_test_user.py`
Creates a test user with admin privileges for development and testing.

**Usage:**
```bash
python scripts/create_test_user.py
```

**Creates:**
- Username: `sata2`
- Password: `qwertyuiop`
- Email: `test@example.com`
- Admin: `True`

### `create_admin_user.py`
Makes an existing user an admin (alternative to creating a new admin user).

**Usage:**
```bash
python scripts/create_admin_user.py
```

**Requires:**
- User `sata2` must already exist in the database

## Setup Documentation

### `AWS_SETUP.md`
Complete guide for setting up AWS S3 integration for admin file uploads.

**Includes:**
- AWS credentials configuration
- S3 bucket setup
- IAM permissions
- Troubleshooting guide

### `FILE_UPLOAD_SYSTEM.md`
Comprehensive documentation for the flexible file upload system.

**Includes:**
- Architecture overview
- Multiple file source support
- API endpoints
- Future extensibility
- Database file storage (planned)

## Running Scripts

All scripts should be run from the project root directory:

```bash
# Activate virtual environment
source .rag_env/bin/activate

# Run scripts
python scripts/create_test_user.py
python scripts/create_admin_user.py
```

## Notes

- Scripts require the virtual environment to be activated
- Database must be running and accessible
- Scripts will create/modify database records
- Use with caution in production environments 