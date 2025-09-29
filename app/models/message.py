from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from .user import Base
import enum

class MessageDirection(enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"

class MessageStatus(enum.Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    RESPONDED = "responded"
    FAILED = "failed"

class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey('businesses.id'), nullable=False)
    whatsapp_message_id = Column(String(255), unique=True, index=True)
    
    # Message Content
    direction = Column(Enum(MessageDirection), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default='text')  # text, image, document, etc.
    language_detected = Column(String(10))
    
    # Sender/Recipient Info
    sender_phone = Column(String(20))
    recipient_phone = Column(String(20))
    sender_name = Column(String(255))
    
    # AI Processing
    status = Column(Enum(MessageStatus), default=MessageStatus.RECEIVED)
    ai_response = Column(Text)
    processing_time_ms = Column(Integer)
    confidence_score = Column(Integer)  # 0-100
    
    # Changed from 'metadata' to 'message_metadata' to avoid SQLAlchemy conflict
    message_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    business = relationship("Business", backref="messages")
    
    def to_dict(self):
        return {
            'id': self.id,
            'business_id': self.business_id,
            'whatsapp_message_id': self.whatsapp_message_id,
            'direction': self.direction.value,
            'content': self.content,
            'content_type': self.content_type,
            'language_detected': self.language_detected,
            'sender_phone': self.sender_phone,
            'recipient_phone': self.recipient_phone,
            'sender_name': self.sender_name,
            'status': self.status.value,
            'ai_response': self.ai_response,
            'processing_time_ms': self.processing_time_ms,
            'confidence_score': self.confidence_score,
            'message_metadata': self.message_metadata,
            'created_at': self.created_at.isoformat()
        }