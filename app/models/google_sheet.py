from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from .user import Base

class GoogleSheetConnection(Base):
    __tablename__ = 'google_sheet_connections'

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey('businesses.id'), nullable=False)

    # Sheet Info
    name = Column(String(255), nullable=False)
    sheet_url = Column(String(500), nullable=False)
    sheet_id = Column(String(255), nullable=False)  # Extracted from URL

    # Configuration
    cache_ttl_minutes = Column(Integer, default=10)  # Cache time-to-live
    query_columns = Column(JSON, default=[])  # Specific columns to use for queries

    # Metadata
    last_synced_at = Column(DateTime)
    last_sync_error = Column(Text)
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = relationship("Business", backref="google_sheets")

    def to_dict(self):
        return {
            'id': self.id,
            'business_id': self.business_id,
            'name': self.name,
            'sheet_url': self.sheet_url,
            'sheet_id': self.sheet_id,
            'cache_ttl_minutes': self.cache_ttl_minutes,
            'query_columns': self.query_columns,
            'last_synced_at': self.last_synced_at.isoformat() if self.last_synced_at else None,
            'last_sync_error': self.last_sync_error,
            'row_count': self.row_count,
            'column_count': self.column_count,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
