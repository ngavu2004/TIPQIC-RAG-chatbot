# File Upload System Documentation

## Overview

The TIPQIC RAG Chatbot now supports a flexible file upload system that can handle multiple file sources and upload them to S3. This system is designed to be extensible for future requirements.

## Architecture

### Core Components

1. **FileSource** - Abstract base class for file sources
2. **S3UploadManager** - Handles S3 uploads from any source
3. **FileUploadService** - High-level service coordinating uploads
4. **Admin Endpoints** - REST API for file operations

### Supported Sources

#### ✅ Currently Implemented
- **Local File System** (`LocalFileSource`)
  - Reads files from local `uploads/` directory
  - Automatic directory creation
  - File metadata extraction

#### 🔄 Future Implementation
- **Database Storage** (`DatabaseFileSource`)
  - Files stored in PostgreSQL with Base64 encoding
  - Metadata tracking (uploader, timestamp, etc.)
  - Ready for implementation when needed

#### 🚀 Extensible
- **Cloud Storage** (Google Drive, Dropbox, etc.)
- **FTP/SFTP Servers**
- **API Endpoints**
- **Custom Sources**

## API Endpoints

### File Upload Endpoints

#### 1. Direct File Upload
```http
POST /api/admin/upload-file
Content-Type: multipart/form-data

file: [binary file data]
```

#### 2. Upload from Source
```http
POST /api/admin/upload-from-source
Content-Type: application/x-www-form-urlencoded

source_name: string
file_identifier: string
s3_filename: string (optional)
```

#### 3. List Source Files
```http
GET /api/admin/list-source-files/{source_name}
```

#### 4. Get Available Sources
```http
GET /api/admin/available-sources
```

## Usage Examples

### 1. Upload Local File
```python
# Frontend automatically handles this
uploaded_file = st.file_uploader("Choose file")
# File gets uploaded to S3 via /api/admin/upload-file
```

### 2. Upload from Local Source
```python
# List files in local source
GET /api/admin/list-source-files/local

# Upload specific file
POST /api/admin/upload-from-source
{
    "source_name": "local",
    "file_identifier": "document.pdf",
    "s3_filename": "processed_document.pdf"
}
```

### 3. Future: Upload from Database
```python
# When database source is implemented
POST /api/admin/upload-from-source
{
    "source_name": "database",
    "file_identifier": "file_uuid_here",
    "s3_filename": "exported_file.pdf"
}
```

## Frontend Interface

### Tab 1: Direct Upload
- File picker for local files
- Drag-and-drop interface
- File validation and preview
- Direct S3 upload

### Tab 2: Upload from Source
- Source selection dropdown
- File listing from selected source
- Optional S3 filename override
- Batch upload capabilities (future)

## Database Schema

### StoredFile Model (Future)
```sql
CREATE TABLE stored_files (
    id UUID PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size INTEGER NOT NULL,
    content_type VARCHAR(100),
    file_content TEXT NOT NULL,  -- Base64 encoded
    uploaded_by UUID REFERENCES users(id),
    uploaded_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);
```

## Configuration

### S3 Configuration
```python
S3_BUCKET_NAME = "tipchatbot"
S3_FILES_PREFIX = "files/"
```

### Local Source Configuration
```python
LOCAL_UPLOAD_PATH = "uploads/"
```

## Security Features

- **Admin-only access** to all upload endpoints
- **File type validation** (txt, pdf, doc, docx, csv, json, xml, md)
- **File size limits** (configurable)
- **S3 access control** via IAM policies
- **Upload tracking** (who, when, what)

## Error Handling

- **Source not found** - Graceful fallback
- **File not found** - Clear error messages
- **S3 upload failures** - Detailed error reporting
- **Network issues** - Retry mechanisms

## Future Enhancements

### Planned Features
1. **Database File Storage**
   - Complete implementation of `DatabaseFileSource`
   - File metadata management
   - Version control

2. **Batch Operations**
   - Multiple file selection
   - Bulk upload from sources
   - Progress tracking

3. **File Processing**
   - Automatic file conversion
   - OCR for images
   - Metadata extraction

4. **Advanced Sources**
   - Google Drive integration
   - Dropbox API
   - FTP/SFTP support
   - Custom API endpoints

### Extensibility
The system is designed to be easily extended:

```python
class CustomFileSource(FileSource):
    def get_file_content(self, file_identifier: str) -> bytes:
        # Custom implementation
        pass
    
    def get_file_info(self, file_identifier: str) -> Dict:
        # Custom metadata
        pass
    
    def list_files(self) -> List[Dict]:
        # Custom file listing
        pass

# Register new source
file_upload_service.register_source("custom", CustomFileSource())
```

## Troubleshooting

### Common Issues

1. **"Source not found" Error**
   - Check if source is registered
   - Verify source name spelling
   - Check source availability

2. **"File not found" Error**
   - Verify file exists in source
   - Check file permissions
   - Validate file identifier

3. **S3 Upload Failures**
   - Check AWS credentials
   - Verify S3 bucket exists
   - Check IAM permissions

### Debug Mode
Enable debug logging for detailed error information:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
``` 