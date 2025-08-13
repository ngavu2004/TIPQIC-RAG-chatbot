# AWS S3 Setup for Admin File Upload

## Prerequisites

1. **AWS Account** with S3 access
2. **S3 Bucket**: `tipchatbot` (must exist)
3. **AWS Credentials** configured

## Setup Steps

### 1. Create S3 Bucket
```bash
aws s3 mb s3://tipchatbot
```

### 2. Configure AWS Credentials

#### Option A: AWS CLI Configuration
```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter your default region (e.g., us-east-1)
# Enter your output format (json)
```

#### Option B: Environment Variables
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

#### Option C: AWS Credentials File
Create `~/.aws/credentials`:
```ini
[default]
aws_access_key_id = your_access_key
aws_secret_access_key = your_secret_key
```

Create `~/.aws/config`:
```ini
[default]
region = us-east-1
```

### 3. Test S3 Access
```bash
aws s3 ls s3://tipchatbot/
```

## Admin File Upload Features

✅ **Supported File Types:**
- Text files (.txt)
- PDF documents (.pdf)
- Word documents (.doc, .docx)
- CSV files (.csv)
- JSON files (.json)
- XML files (.xml)
- Markdown files (.md)

✅ **Upload Path:**
- Files are uploaded to `s3://tipchatbot/files/`
- Each file gets a unique S3 key

✅ **Security:**
- Admin-only access
- File validation
- Error handling
- Upload progress tracking

## Usage

1. **Login as admin** (username: `sata2`, password: `Qwertyuiop123#`)
2. **Navigate to Admin Dashboard** (click ⚙️ Admin button)
3. **Select file** using the file uploader
4. **Click "🚀 Upload to S3"** to upload
5. **View upload results** with S3 key and metadata

## Troubleshooting

### Common Issues:

1. **"Access Denied" Error:**
   - Check AWS credentials
   - Verify S3 bucket exists
   - Ensure proper IAM permissions

2. **"Bucket Not Found" Error:**
   - Create the S3 bucket: `aws s3 mb s3://tipchatbot`

3. **"Invalid Credentials" Error:**
   - Reconfigure AWS credentials
   - Check environment variables

### IAM Permissions Required:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::tipchatbot",
                "arn:aws:s3:::tipchatbot/*"
            ]
        }
    ]
}
``` 