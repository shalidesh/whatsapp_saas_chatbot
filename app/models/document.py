from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean, Enum
from sqlalchemy.orm import relationship
from .user import Base
import enum

class DocumentType(enum.Enum):
    PDF = "pdf"
    SPREADSHEET = "spreadsheet"
    WEBSITE = "website"

class DocumentStatus(enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"

class Document(Base):
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey('businesses.id'), nullable=False)
    
    # Document Info
    name = Column(String(255), nullable=False)
    document_type = Column(Enum(DocumentType), nullable=False)
    file_path = Column(String(500))  # S3 path for files
    url = Column(String(500))  # For websites/spreadsheets
    file_size = Column(Integer)
    
    # Processing Status
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED)
    processing_error = Column(Text)
    
    # Content & Embeddings
    extracted_text = Column(Text)
    chunk_count = Column(Integer, default=0)
    embedding_model = Column(String(100), default='text-embedding-ada-002')
    
    # Changed from 'metadata' to 'document_metadata' to avoid SQLAlchemy conflict
    document_metadata = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    business = relationship("Business", backref="documents")
    
    def to_dict(self):
        return {
            'id': self.id,
            'business_id': self.business_id,
            'name': self.name,
            'document_type': self.document_type.value,
            'file_path': self.file_path,
            'url': self.url,
            'file_size': self.file_size,
            'status': self.status.value,
            'processing_error': self.processing_error,
            'chunk_count': self.chunk_count,
            'embedding_model': self.embedding_model,
            'document_metadata': self.document_metadata,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }