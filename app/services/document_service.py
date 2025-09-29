import os
import boto3
from fastapi import UploadFile  # ✅ Replace werkzeug.datastructures.FileStorage
import PyPDF2
import httpx  # ✅ Replace requests for async
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO
import structlog

from ..models.document import Document, DocumentType, DocumentStatus
from ..config.database import db_session
from ..config.settings import config

logger = structlog.get_logger(__name__)

class DocumentService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY
        )
        self.bucket_name = config.S3_BUCKET_NAME
        
        # Allowed file extensions
        self.allowed_extensions = {
            'pdf': DocumentType.PDF,
            'xlsx': DocumentType.SPREADSHEET,
            'xls': DocumentType.SPREADSHEET,
            'csv': DocumentType.SPREADSHEET
        }
    
    async def upload_document(self, business_id: int, file: UploadFile, 
                            document_type: str = None) -> Document:
        """Upload document to S3 and create database record (FastAPI version)"""
        try:
            if not file or not file.filename:
                raise ValueError("No file provided")
            
            # Secure filename (manual implementation since we don't have werkzeug)
            filename = self._secure_filename(file.filename)
            file_extension = filename.rsplit('.', 1)[1].lower()
            
            if file_extension not in self.allowed_extensions:
                raise ValueError(f"File type {file_extension} not supported")
            
            # Determine document type
            if not document_type:
                document_type = self.allowed_extensions[file_extension].value
            
            # Generate S3 key
            s3_key = f"businesses/{business_id}/documents/{filename}"
            
            # Read file content
            file_content = await file.read()
            file_size = len(file_content)
            
            # Upload to S3
            self.s3_client.upload_fileobj(
                BytesIO(file_content),
                self.bucket_name,
                s3_key,
                ExtraArgs={'ContentType': file.content_type or 'application/octet-stream'}
            )
            
            # Create document record
            document = Document(
                business_id=business_id,
                name=filename,
                document_type=DocumentType(document_type),
                file_path=s3_key,
                file_size=file_size,
                status=DocumentStatus.UPLOADED
            )
            
            db_session.add(document)
            db_session.commit()
            
            logger.info("Document uploaded successfully", 
                       document_id=document.id, filename=filename)
            
            return document
            
        except Exception as e:
            logger.error("Error uploading document", error=str(e))
            raise
    
    def create_document_from_url(self, business_id: int, document_type: str, 
                               url: str) -> Document:
        """Create document from URL (website/spreadsheet)"""
        try:
            # Validate URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Create document record
            document = Document(
                business_id=business_id,
                name=self._extract_name_from_url(url),
                document_type=DocumentType(document_type),
                url=url,
                status=DocumentStatus.UPLOADED
            )
            
            db_session.add(document)
            db_session.commit()
            
            logger.info("Document created from URL", 
                       document_id=document.id, url=url)
            
            return document
            
        except Exception as e:
            logger.error("Error creating document from URL", error=str(e))
            raise
    
    def extract_text(self, file_path_or_url: str) -> str:
        """Extract text from document"""
        try:
            if file_path_or_url.startswith('http'):
                return self._extract_text_from_url(file_path_or_url)
            else:
                return self._extract_text_from_file(file_path_or_url)
                
        except Exception as e:
            logger.error("Error extracting text", error=str(e))
            raise
    
    def _extract_text_from_file(self, s3_key: str) -> str:
        """Extract text from S3 file"""
        try:
            # Download file from S3
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            file_content = response['Body'].read()
            
            # Determine file type and extract text
            if s3_key.lower().endswith('.pdf'):
                return self._extract_pdf_text(file_content)
            elif s3_key.lower().endswith(('.xlsx', '.xls')):
                return self._extract_excel_text(file_content)
            elif s3_key.lower().endswith('.csv'):
                return self._extract_csv_text(file_content)
            else:
                raise ValueError("Unsupported file type")
                
        except Exception as e:
            logger.error("Error extracting text from file", s3_key=s3_key, error=str(e))
            raise
    
    async def _extract_text_from_url(self, url: str) -> str:
        """Extract text from URL (async version)"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
            
            if 'google.com/spreadsheets' in url or url.endswith(('.xlsx', '.xls', '.csv')):
                # Handle spreadsheet URLs
                if 'google.com/spreadsheets' in url:
                    # Convert Google Sheets URL to CSV export URL
                    if '/edit' in url:
                        sheet_id = url.split('/d/')[1].split('/')[0]
                        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            response = await client.get(csv_url, headers=headers)
                
                return self._extract_csv_text(response.content)
            else:
                # Handle regular websites
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Extract text
                text = soup.get_text()
                
                # Clean up text
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                return text
                
        except Exception as e:
            logger.error("Error extracting text from URL", url=url, error=str(e))
            raise
    
    def _extract_pdf_text(self, file_content: bytes) -> str:
        """Extract text from PDF"""
        try:
            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
            
        except Exception as e:
            logger.error("Error extracting PDF text", error=str(e))
            raise
    
    def _extract_excel_text(self, file_content: bytes) -> str:
        """Extract text from Excel file"""
        try:
            excel_file = BytesIO(file_content)
            
            # Read all sheets
            xlsx = pd.ExcelFile(excel_file)
            text_parts = []
            
            for sheet_name in xlsx.sheet_names:
                df = pd.read_excel(xlsx, sheet_name=sheet_name)
                
                # Convert DataFrame to text
                sheet_text = f"Sheet: {sheet_name}\n"
                sheet_text += df.to_string(index=False, na_rep='')
                text_parts.append(sheet_text)
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.error("Error extracting Excel text", error=str(e))
            raise
    
    def _extract_csv_text(self, file_content: bytes) -> str:
        """Extract text from CSV file"""
        try:
            csv_file = BytesIO(file_content)
            df = pd.read_csv(csv_file)
            
            # Convert DataFrame to text
            return df.to_string(index=False, na_rep='')
            
        except Exception as e:
            logger.error("Error extracting CSV text", error=str(e))
            raise
    
    async def _get_file_size(self, file: UploadFile) -> int:
        """Get file size (FastAPI UploadFile version)"""
        try:
            # Method 1: Read content and get length (most reliable)
            content = await file.read()
            size = len(content)
            
            # Reset file position to beginning for future reads
            await file.seek(0)
            
            return size
            
        except Exception as e:
            logger.error("Error getting file size", error=str(e))
            return 0
    
    def _extract_name_from_url(self, url: str) -> str:
        """Extract document name from URL"""
        try:
            if 'google.com/spreadsheets' in url:
                return "Google Spreadsheet"
            else:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                return parsed.netloc or "Website Document"
        except:
            return "Document"

    def delete_document(self, document_id: int, business_id: int) -> bool:
        """Delete document"""
        try:
            document = db_session.query(Document).filter(
                Document.id == document_id,
                Document.business_id == business_id
            ).first()
            
            if not document:
                return False
            
            # Delete from S3 if it's a file
            if document.file_path:
                try:
                    self.s3_client.delete_object(
                        Bucket=self.bucket_name,
                        Key=document.file_path
                    )
                except Exception as e:
                    logger.warning("Error deleting file from S3", error=str(e))
            
            # Mark as inactive
            document.is_active = False
            db_session.commit()
            
            logger.info("Document deleted", document_id=document_id)
            return True
            
        except Exception as e:
            logger.error("Error deleting document", error=str(e))
            return False
        
    def _secure_filename(self, filename: str) -> str:
        """Secure filename implementation (replacing werkzeug)"""
        import re
        filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        return filename[:255]  # Limit length