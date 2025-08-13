"""
File Upload Manager for TIPQIC RAG Chatbot
Supports multiple file sources: local files, database files, and future sources
"""
import os
import boto3
from typing import Dict, List, Optional, Union, BinaryIO
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
import io

class FileSource:
    """Base class for file sources"""
    
    def get_file_content(self, file_identifier: str) -> bytes:
        """Get file content from source"""
        raise NotImplementedError
    
    def get_file_info(self, file_identifier: str) -> Dict:
        """Get file metadata from source"""
        raise NotImplementedError
    
    def list_files(self) -> List[Dict]:
        """List available files from source"""
        raise NotImplementedError

class LocalFileSource(FileSource):
    """Local file system source"""
    
    def __init__(self, base_path: str = "uploads/"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    def get_file_content(self, file_identifier: str) -> bytes:
        file_path = os.path.join(self.base_path, file_identifier)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_identifier}")
        
        with open(file_path, 'rb') as f:
            return f.read()
    
    def get_file_info(self, file_identifier: str) -> Dict:
        file_path = os.path.join(self.base_path, file_identifier)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_identifier}")
        
        stat = os.stat(file_path)
        return {
            "filename": file_identifier,
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "source": "local"
        }
    
    def list_files(self) -> List[Dict]:
        files = []
        if os.path.exists(self.base_path):
            for filename in os.listdir(self.base_path):
                if os.path.isfile(os.path.join(self.base_path, filename)):
                    files.append(self.get_file_info(filename))
        return files

class DatabaseFileSource(FileSource):
    """Database file source (for future implementation)"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_file_content(self, file_identifier: str) -> bytes:
        # TODO: Implement database file retrieval
        # This would query a file_storage table
        raise NotImplementedError("Database file source not yet implemented")
    
    def get_file_info(self, file_identifier: str) -> Dict:
        # TODO: Implement database file info retrieval
        raise NotImplementedError("Database file source not yet implemented")
    
    def list_files(self) -> List[Dict]:
        # TODO: Implement database file listing
        raise NotImplementedError("Database file source not yet implemented")

class S3UploadManager:
    """Manages file uploads to S3 with support for multiple sources"""
    
    def __init__(self, bucket_name: str = "tipchatbot", files_prefix: str = "files/"):
        self.bucket_name = bucket_name
        self.files_prefix = files_prefix
        self.s3_client = boto3.client('s3')
    
    def upload_from_stream(self, file_content: bytes, filename: str, content_type: str = None) -> Dict:
        """Upload file content from memory stream"""
        try:
            s3_key = f"{self.files_prefix}{filename}"
            
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                **extra_args
            )
            
            return {
                "success": True,
                "s3_key": s3_key,
                "filename": filename,
                "message": f"File uploaded successfully to s3://{self.bucket_name}/{s3_key}"
            }
        except ClientError as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to upload file to S3"
            }
    
    def upload_from_file_source(self, file_source: FileSource, file_identifier: str, s3_filename: str = None) -> Dict:
        """Upload file from any file source"""
        try:
            # Get file content from source
            file_content = file_source.get_file_content(file_identifier)
            file_info = file_source.get_file_info(file_identifier)
            
            # Use original filename if not specified
            if not s3_filename:
                s3_filename = file_info.get("filename", file_identifier)
            
            # Upload to S3
            return self.upload_from_stream(file_content, s3_filename)
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to upload from {file_source.__class__.__name__}"
            }
    
    def upload_from_fastapi_file(self, file: UploadFile) -> Dict:
        """Upload file from FastAPI UploadFile"""
        if not file.filename:
            return {
                "success": False,
                "error": "No filename provided",
                "message": "File must have a filename"
            }
        
        try:
            file_content = file.file.read()
            content_type = file.content_type
            
            return self.upload_from_stream(file_content, file.filename, content_type)
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to read and upload file"
            }

class FileUploadService:
    """High-level service for file uploads with multiple sources"""
    
    def __init__(self, s3_manager: S3UploadManager):
        self.s3_manager = s3_manager
        self.sources: Dict[str, FileSource] = {}
    
    def register_source(self, name: str, source: FileSource):
        """Register a file source"""
        self.sources[name] = source
    
    def upload_from_source(self, source_name: str, file_identifier: str, s3_filename: str = None) -> Dict:
        """Upload file from a registered source"""
        if source_name not in self.sources:
            return {
                "success": False,
                "error": f"Source '{source_name}' not found",
                "message": f"Available sources: {list(self.sources.keys())}"
            }
        
        source = self.sources[source_name]
        return self.s3_manager.upload_from_file_source(source, file_identifier, s3_filename)
    
    def upload_from_fastapi(self, file: UploadFile) -> Dict:
        """Upload file from FastAPI UploadFile"""
        return self.s3_manager.upload_from_fastapi_file(file)
    
    def list_source_files(self, source_name: str) -> List[Dict]:
        """List files from a specific source"""
        if source_name not in self.sources:
            return []
        
        return self.sources[source_name].list_files()
    
    def get_available_sources(self) -> List[str]:
        """Get list of available file sources"""
        return list(self.sources.keys())

# Global file upload service instance
file_upload_service = FileUploadService(
    S3UploadManager(bucket_name="tipchatbot", files_prefix="files/")
)

# Register default sources
file_upload_service.register_source("local", LocalFileSource()) 