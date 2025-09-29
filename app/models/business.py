from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .user import Base

class Business(Base):
    __tablename__ = 'businesses'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    website_url = Column(String(500))
    whatsapp_phone_number = Column(String(20),nullable=False)
    business_category = Column(String(100))
    
    # AI Configuration
    ai_persona = Column(Text, default="You are a helpful business assistant.")
    supported_languages = Column(JSON, default=['si', 'en'])  # Sinhala, English
    default_language = Column(String(10), default='si')
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", backref="businesses")
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'website_url': self.website_url,
            'whatsapp_phone_number': self.whatsapp_phone_number,
            'business_category': self.business_category,
            'ai_persona': self.ai_persona,
            'supported_languages': self.supported_languages,
            'default_language': self.default_language,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }