from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import structlog

from ...models.user import User
from ...models.business import Business
from ...models.message import Message, MessageDirection, MessageStatus
from ...models.document import Document, DocumentStatus
from ...config.database import db_session
from ...middleware.auth import get_current_user
from ...services.document_service import DocumentService
from ...tasks.document_processing import process_document_upload
from .analytics import AnalyticsService

logger = structlog.get_logger(__name__)

dashboard_router = APIRouter()
analytics_service = AnalyticsService()

# Pydantic models
class BusinessSettingsUpdate(BaseModel):
    business_id: int
    name: Optional[str] = None
    description: Optional[str] = None
    website_url: Optional[str] = None
    whatsapp_phone_number: Optional[str] = None
    business_category: Optional[str] = None
    ai_persona: Optional[str] = None
    supported_languages: Optional[List[str]] = None
    default_language: Optional[str] = None

class OverviewResponse(BaseModel):
    business: dict
    statistics: dict
    recent_messages: List[dict]

class MessagesResponse(BaseModel):
    messages: List[dict]
    pagination: dict

class AnalyticsResponse(BaseModel):
    daily_stats: List[dict]
    language_distribution: List[dict]
    response_time_distribution: List[dict]
    common_queries: List[dict]

class DocumentsResponse(BaseModel):
    documents: List[dict]

class DocumentUploadResponse(BaseModel):
    message: str
    document: dict

class BusinessSettingsResponse(BaseModel):
    business: dict

@dashboard_router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    business_id: int = Query(..., description="Business ID"),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard overview"""
    try:
        # Verify business ownership
        business = db_session.query(Business).filter(
            Business.id == business_id,
            Business.user_id == current_user.id
        ).first()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        # Get date range (last 30 days by default)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        # Message statistics
        total_messages = db_session.query(Message).filter(
            Message.business_id == business_id,
            Message.created_at >= start_date
        ).count()
        
        inbound_messages = db_session.query(Message).filter(
            Message.business_id == business_id,
            Message.direction == MessageDirection.INBOUND,
            Message.created_at >= start_date
        ).count()
        
        responded_messages = db_session.query(Message).filter(
            Message.business_id == business_id,
            Message.direction == MessageDirection.INBOUND,
            Message.status == MessageStatus.RESPONDED,
            Message.created_at >= start_date
        ).count()
        
        # Response rate
        response_rate = (responded_messages / inbound_messages * 100) if inbound_messages > 0 else 0
        
        # Average response time
        avg_response_time = db_session.query(
            func.avg(Message.processing_time_ms)
        ).filter(
            Message.business_id == business_id,
            Message.direction == MessageDirection.INBOUND,
            Message.status == MessageStatus.RESPONDED,
            Message.created_at >= start_date
        ).scalar() or 0
        
        # Document statistics
        total_documents = db_session.query(Document).filter(
            Document.business_id == business_id,
            Document.is_active == True
        ).count()
        
        processed_documents = db_session.query(Document).filter(
            Document.business_id == business_id,
            Document.status == DocumentStatus.PROCESSED,
            Document.is_active == True
        ).count()
        
        # Recent messages
        recent_messages = db_session.query(Message).filter(
            Message.business_id == business_id
        ).order_by(desc(Message.created_at)).limit(10).all()
        
        overview_data = OverviewResponse(
            business=business.to_dict(),
            statistics={
                'total_messages': total_messages,
                'inbound_messages': inbound_messages,
                'responded_messages': responded_messages,
                'response_rate': round(response_rate, 2),
                'avg_response_time_ms': round(avg_response_time, 2),
                'total_documents': total_documents,
                'processed_documents': processed_documents
            },
            recent_messages=[msg.to_dict() for msg in recent_messages]
        )
        
        return overview_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting dashboard overview", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get overview"
        )

@dashboard_router.get("/messages", response_model=MessagesResponse)
async def get_messages(
    business_id: int = Query(..., description="Business ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    direction: Optional[str] = Query(None, description="Message direction: inbound or outbound"),
    status: Optional[str] = Query(None, description="Message status"),
    current_user: User = Depends(get_current_user)
):
    """Get messages with pagination"""
    try:
        # Verify business ownership
        business = db_session.query(Business).filter(
            Business.id == business_id,
            Business.user_id == current_user.id
        ).first()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        # Build query
        query = db_session.query(Message).filter(Message.business_id == business_id)
        
        if direction:
            query = query.filter(Message.direction == MessageDirection(direction))
        
        if status:
            query = query.filter(Message.status == MessageStatus(status))
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        messages = query.order_by(desc(Message.created_at)).offset(offset).limit(limit).all()
        
        return MessagesResponse(
            messages=[msg.to_dict() for msg in messages],
            pagination={
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting messages", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get messages"
        )

@dashboard_router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    business_id: int = Query(..., description="Business ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user)
):
    """Get analytics data"""
    try:
        # Verify business ownership
        business = db_session.query(Business).filter(
            Business.id == business_id,
            Business.user_id == current_user.id
        ).first()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Daily message counts
        daily_stats = db_session.query(
            func.date(Message.created_at).label('date'),
            func.count(Message.id).label('total'),
            func.sum(func.case([(Message.direction == MessageDirection.INBOUND, 1)], else_=0)).label('inbound'),
            func.sum(func.case([(Message.direction == MessageDirection.OUTBOUND, 1)], else_=0)).label('outbound')
        ).filter(
            Message.business_id == business_id,
            Message.created_at >= start_date
        ).group_by(func.date(Message.created_at)).all()
        
        # Language distribution
        language_stats = db_session.query(
            Message.language_detected,
            func.count(Message.id).label('count')
        ).filter(
            Message.business_id == business_id,
            Message.direction == MessageDirection.INBOUND,
            Message.created_at >= start_date,
            Message.language_detected.isnot(None)
        ).group_by(Message.language_detected).all()
        
        # Response time distribution
        response_time_stats = db_session.query(
            func.case([
                (Message.processing_time_ms < 1000, 'Under 1s'),
                (Message.processing_time_ms < 5000, '1-5s'),
                (Message.processing_time_ms < 10000, '5-10s'),
            ], else_='Over 10s').label('bucket'),
            func.count(Message.id).label('count')
        ).filter(
            Message.business_id == business_id,
            Message.direction == MessageDirection.INBOUND,
            Message.status == MessageStatus.RESPONDED,
            Message.created_at >= start_date
        ).group_by('bucket').all()
        
        # Common queries (simplified - would need proper NLP analysis)
        common_queries = db_session.query(
            Message.content,
            func.count(Message.id).label('frequency')
        ).filter(
            Message.business_id == business_id,
            Message.direction == MessageDirection.INBOUND,
            Message.created_at >= start_date,
            func.length(Message.content) < 100  # Short queries only
        ).group_by(Message.content).order_by(desc('frequency')).limit(10).all()
        
        return AnalyticsResponse(
            daily_stats=[
                {
                    'date': stat.date.isoformat(),
                    'total': stat.total,
                    'inbound': stat.inbound or 0,
                    'outbound': stat.outbound or 0
                }
                for stat in daily_stats
            ],
            language_distribution=[
                {'language': stat[0], 'count': stat[1]}
                for stat in language_stats
            ],
            response_time_distribution=[
                {'bucket': stat[0], 'count': stat[1]}
                for stat in response_time_stats
            ],
            common_queries=[
                {'query': query[0][:50] + '...' if len(query[0]) > 50 else query[0], 'frequency': query[1]}
                for query in common_queries
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting analytics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analytics"
        )

@dashboard_router.get("/documents", response_model=DocumentsResponse)
async def get_documents(
    business_id: int = Query(..., description="Business ID"),
    current_user: User = Depends(get_current_user)
):
    """Get business documents"""
    try:
        # Verify business ownership
        business = db_session.query(Business).filter(
            Business.id == business_id,
            Business.user_id == current_user.id
        ).first()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        documents = db_session.query(Document).filter(
            Document.business_id == business_id,
            Document.is_active == True
        ).order_by(desc(Document.created_at)).all()
        
        return DocumentsResponse(
            documents=[doc.to_dict() for doc in documents]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting documents", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get documents"
        )

@dashboard_router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    business_id: int = Form(...),
    document_type: str = Form(...),
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user)
):
    """Upload document"""
    try:
        # Verify business ownership
        business = db_session.query(Business).filter(
            Business.id == business_id,
            Business.user_id == current_user.id
        ).first()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        document_service = DocumentService()
        
        if document_type in ['website', 'spreadsheet'] and url:
            # Handle URL-based documents
            document = document_service.create_document_from_url(
                business_id=business_id,
                document_type=document_type,
                url=url
            )
        elif file and file.filename:
            # Handle file uploads
            document = await document_service.upload_document(
                business_id=business_id,
                file=file,
                document_type=document_type
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file or URL provided"
            )
        
        if document:
            # Queue document processing
            process_document_upload.delay(
                document_id=document.id,
                file_path=document.file_path or document.url,
                business_id=business_id
            )
            
            return DocumentUploadResponse(
                message="Document uploaded successfully",
                document=document.to_dict()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload document"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error uploading document", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document"
        )

@dashboard_router.get("/business/settings", response_model=BusinessSettingsResponse)
async def get_business_settings(
    business_id: int = Query(..., description="Business ID"),
    current_user: User = Depends(get_current_user)
):
    """Get business settings"""
    try:
        # Verify business ownership
        business = db_session.query(Business).filter(
            Business.id == business_id,
            Business.user_id == current_user.id
        ).first()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        return BusinessSettingsResponse(business=business.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting business settings", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get business settings"
        )

@dashboard_router.put("/business/settings", response_model=BusinessSettingsResponse)
async def update_business_settings(
    request: BusinessSettingsUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update business settings"""
    try:
        # Verify business ownership
        business = db_session.query(Business).filter(
            Business.id == request.business_id,
            Business.user_id == current_user.id
        ).first()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        # Update business settings
        if request.name is not None:
            business.name = request.name.strip()
        if request.description is not None:
            business.description = request.description.strip()
        if request.website_url is not None:
            business.website_url = request.website_url.strip()
        if request.whatsapp_phone_number is not None:
            business.whatsapp_phone_number = request.whatsapp_phone_number.strip()
        if request.business_category is not None:
            business.business_category = request.business_category.strip()
        if request.ai_persona is not None:
            business.ai_persona = request.ai_persona.strip()
        if request.supported_languages is not None:
            business.supported_languages = request.supported_languages
        if request.default_language is not None:
            business.default_language = request.default_language
        
        business.updated_at = datetime.utcnow()
        db_session.commit()
        
        logger.info("Business settings updated", 
                   business_id=request.business_id, user_id=current_user.id)
        
        return BusinessSettingsResponse(business=business.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating business settings", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update business settings"
        )

# Additional endpoint using the AnalyticsService
@dashboard_router.get("/comprehensive-analytics")
async def get_comprehensive_analytics(
    business_id: int = Query(..., description="Business ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive analytics report"""
    try:
        # Verify business ownership
        business = db_session.query(Business).filter(
            Business.id == business_id,
            Business.user_id == current_user.id
        ).first()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        # Use the analytics service for comprehensive report
        report = analytics_service.generate_comprehensive_report(business_id, days)
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting comprehensive analytics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get comprehensive analytics"
        )