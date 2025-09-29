from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import func, desc, and_
import structlog

from ...models.message import Message, MessageDirection, MessageStatus
from ...models.document import Document, DocumentStatus
from ...models.business import Business
from ...config.database import db_session

logger = structlog.get_logger(__name__)

class AnalyticsService:
    """Service for generating business analytics and insights"""
    
    def __init__(self):
        pass
    
    def get_message_analytics(self, business_id: int, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive message analytics for a business"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Basic message counts
            total_messages = db_session.query(Message).filter(
                Message.business_id == business_id,
                Message.created_at >= start_date
            ).count()
            
            inbound_messages = db_session.query(Message).filter(
                Message.business_id == business_id,
                Message.direction == MessageDirection.INBOUND,
                Message.created_at >= start_date
            ).count()
            
            outbound_messages = db_session.query(Message).filter(
                Message.business_id == business_id,
                Message.direction == MessageDirection.OUTBOUND,
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
                Message.created_at >= start_date,
                Message.processing_time_ms.isnot(None)
            ).scalar() or 0
            
            # Average confidence score
            avg_confidence = db_session.query(
                func.avg(Message.confidence_score)
            ).filter(
                Message.business_id == business_id,
                Message.direction == MessageDirection.INBOUND,
                Message.status == MessageStatus.RESPONDED,
                Message.created_at >= start_date,
                Message.confidence_score.isnot(None)
            ).scalar() or 0
            
            # Calculate performance grade
            performance_grade = get_performance_grade(response_rate, avg_response_time, avg_confidence)
            
            return {
                'total_messages': total_messages,
                'inbound_messages': inbound_messages,
                'outbound_messages': outbound_messages,
                'responded_messages': responded_messages,
                'response_rate': round(response_rate, 2),
                'avg_response_time_ms': round(avg_response_time, 2),
                'avg_confidence_score': round(avg_confidence, 2),
                'performance_grade': performance_grade,
                'period_days': days
            }
            
        except Exception as e:
            logger.error("Error getting message analytics", 
                        business_id=business_id, error=str(e))
            return {}
    
    def get_daily_message_trends(self, business_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily message trends"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            daily_stats = db_session.query(
                func.date(Message.created_at).label('date'),
                func.count(Message.id).label('total'),
                func.sum(func.case([(Message.direction == MessageDirection.INBOUND, 1)], else_=0)).label('inbound'),
                func.sum(func.case([(Message.direction == MessageDirection.OUTBOUND, 1)], else_=0)).label('outbound'),
                func.sum(func.case([(and_(Message.direction == MessageDirection.INBOUND, 
                                         Message.status == MessageStatus.RESPONDED), 1)], else_=0)).label('responded')
            ).filter(
                Message.business_id == business_id,
                Message.created_at >= start_date
            ).group_by(func.date(Message.created_at)).order_by(func.date(Message.created_at)).all()
            
            trends = []
            for stat in daily_stats:
                response_rate = (stat.responded / stat.inbound * 100) if stat.inbound > 0 else 0
                trends.append({
                    'date': stat.date.isoformat(),
                    'total': stat.total,
                    'inbound': stat.inbound or 0,
                    'outbound': stat.outbound or 0,
                    'responded': stat.responded or 0,
                    'response_rate': round(response_rate, 2)
                })
            
            return trends
            
        except Exception as e:
            logger.error("Error getting daily message trends", 
                        business_id=business_id, error=str(e))
            return []
    
    def get_language_distribution(self, business_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get language distribution of messages"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            language_stats = db_session.query(
                Message.language_detected,
                func.count(Message.id).label('count')
            ).filter(
                Message.business_id == business_id,
                Message.direction == MessageDirection.INBOUND,
                Message.created_at >= start_date,
                Message.language_detected.isnot(None)
            ).group_by(Message.language_detected).all()
            
            # Map language codes to names
            language_names = {
                'si': 'Sinhala',
                'en': 'English',
                'ta': 'Tamil'
            }
            
            distribution = []
            total_messages = sum(stat.count for stat in language_stats)
            
            for stat in language_stats:
                percentage = (stat.count / total_messages * 100) if total_messages > 0 else 0
                distribution.append({
                    'language_code': stat.language_detected,
                    'language_name': language_names.get(stat.language_detected, stat.language_detected),
                    'count': stat.count,
                    'percentage': round(percentage, 2)
                })
            
            return sorted(distribution, key=lambda x: x['count'], reverse=True)
            
        except Exception as e:
            logger.error("Error getting language distribution", 
                        business_id=business_id, error=str(e))
            return []
    
    def get_response_time_distribution(self, business_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get response time distribution"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            response_time_stats = db_session.query(
                func.case([
                    (Message.processing_time_ms < 1000, 'Under 1s'),
                    (Message.processing_time_ms < 3000, '1-3s'),
                    (Message.processing_time_ms < 5000, '3-5s'),
                    (Message.processing_time_ms < 10000, '5-10s'),
                ], else_='Over 10s').label('bucket'),
                func.count(Message.id).label('count')
            ).filter(
                Message.business_id == business_id,
                Message.direction == MessageDirection.INBOUND,
                Message.status == MessageStatus.RESPONDED,
                Message.created_at >= start_date,
                Message.processing_time_ms.isnot(None)
            ).group_by('bucket').all()
            
            distribution = []
            total_responses = sum(stat.count for stat in response_time_stats)
            
            for stat in response_time_stats:
                percentage = (stat.count / total_responses * 100) if total_responses > 0 else 0
                distribution.append({
                    'bucket': stat.bucket,
                    'count': stat.count,
                    'percentage': round(percentage, 2)
                })
            
            return distribution
            
        except Exception as e:
            logger.error("Error getting response time distribution", 
                        business_id=business_id, error=str(e))
            return []
    
    def get_confidence_score_distribution(self, business_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get AI confidence score distribution"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            confidence_stats = db_session.query(
                func.case([
                    (Message.confidence_score < 20, 'Very Low (0-19)'),
                    (Message.confidence_score < 40, 'Low (20-39)'),
                    (Message.confidence_score < 60, 'Medium (40-59)'),
                    (Message.confidence_score < 80, 'High (60-79)'),
                ], else_='Very High (80-100)').label('bucket'),
                func.count(Message.id).label('count')
            ).filter(
                Message.business_id == business_id,
                Message.direction == MessageDirection.INBOUND,
                Message.status == MessageStatus.RESPONDED,
                Message.created_at >= start_date,
                Message.confidence_score.isnot(None)
            ).group_by('bucket').all()
            
            distribution = []
            total_responses = sum(stat.count for stat in confidence_stats)
            
            for stat in confidence_stats:
                percentage = (stat.count / total_responses * 100) if total_responses > 0 else 0
                distribution.append({
                    'bucket': stat.bucket,
                    'count': stat.count,
                    'percentage': round(percentage, 2)
                })
            
            return distribution
            
        except Exception as e:
            logger.error("Error getting confidence score distribution", 
                        business_id=business_id, error=str(e))
            return []
    
    def get_common_queries(self, business_id: int, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most common user queries"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Simple approach - group by exact content (for similar queries)
            # In production, you'd want semantic clustering of similar queries
            common_queries = db_session.query(
                Message.content,
                func.count(Message.id).label('frequency')
            ).filter(
                Message.business_id == business_id,
                Message.direction == MessageDirection.INBOUND,
                Message.created_at >= start_date,
                func.length(Message.content) < 200,  # Exclude very long messages
                func.length(Message.content) > 5     # Exclude very short messages
            ).group_by(Message.content).order_by(desc('frequency')).limit(limit).all()
            
            queries = []
            for query in common_queries:
                # Truncate very long queries for display
                display_query = query.content[:100] + '...' if len(query.content) > 100 else query.content
                queries.append({
                    'query': display_query,
                    'full_query': query.content,
                    'frequency': query.frequency
                })
            
            return queries
            
        except Exception as e:
            logger.error("Error getting common queries", 
                        business_id=business_id, error=str(e))
            return []
    
    def get_peak_hours(self, business_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get peak hours for message activity"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            hourly_stats = db_session.query(
                func.extract('hour', Message.created_at).label('hour'),
                func.count(Message.id).label('count')
            ).filter(
                Message.business_id == business_id,
                Message.direction == MessageDirection.INBOUND,
                Message.created_at >= start_date
            ).group_by(func.extract('hour', Message.created_at)).order_by('hour').all()
            
            peak_hours = []
            for stat in hourly_stats:
                hour_12 = int(stat.hour)
                period = "AM" if hour_12 < 12 else "PM"
                display_hour = hour_12 if hour_12 <= 12 else hour_12 - 12
                if display_hour == 0:
                    display_hour = 12
                
                peak_hours.append({
                    'hour': int(stat.hour),
                    'display_hour': f"{display_hour}:00 {period}",
                    'count': stat.count
                })
            
            return sorted(peak_hours, key=lambda x: x['count'], reverse=True)
            
        except Exception as e:
            logger.error("Error getting peak hours", 
                        business_id=business_id, error=str(e))
            return []
    
    def get_document_analytics(self, business_id: int) -> Dict[str, Any]:
        """Get document processing analytics"""
        try:
            total_documents = db_session.query(Document).filter(
                Document.business_id == business_id,
                Document.is_active == True
            ).count()
            
            processed_documents = db_session.query(Document).filter(
                Document.business_id == business_id,
                Document.status == DocumentStatus.PROCESSED,
                Document.is_active == True
            ).count()
            
            processing_documents = db_session.query(Document).filter(
                Document.business_id == business_id,
                Document.status == DocumentStatus.PROCESSING,
                Document.is_active == True
            ).count()
            
            failed_documents = db_session.query(Document).filter(
                Document.business_id == business_id,
                Document.status == DocumentStatus.FAILED,
                Document.is_active == True
            ).count()
            
            # Document types distribution
            doc_types = db_session.query(
                Document.document_type,
                func.count(Document.id).label('count')
            ).filter(
                Document.business_id == business_id,
                Document.is_active == True
            ).group_by(Document.document_type).all()
            
            type_distribution = [
                {
                    'type': doc_type.document_type.value,
                    'count': doc_type.count
                }
                for doc_type in doc_types
            ]
            
            processing_rate = (processed_documents / total_documents * 100) if total_documents > 0 else 0
            
            return {
                'total_documents': total_documents,
                'processed_documents': processed_documents,
                'processing_documents': processing_documents,
                'failed_documents': failed_documents,
                'processing_rate': round(processing_rate, 2),
                'type_distribution': type_distribution
            }
            
        except Exception as e:
            logger.error("Error getting document analytics", 
                        business_id=business_id, error=str(e))
            return {}
    
    def get_user_engagement_metrics(self, business_id: int, days: int = 30) -> Dict[str, Any]:
        """Get user engagement metrics"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Unique users (by phone number)
            unique_users = db_session.query(
                func.count(func.distinct(Message.sender_phone))
            ).filter(
                Message.business_id == business_id,
                Message.direction == MessageDirection.INBOUND,
                Message.created_at >= start_date,
                Message.sender_phone.isnot(None)
            ).scalar() or 0
            
            # Returning users (users with more than 1 message)
            returning_users = db_session.query(
                func.count(func.distinct(Message.sender_phone))
            ).filter(
                Message.business_id == business_id,
                Message.direction == MessageDirection.INBOUND,
                Message.created_at >= start_date,
                Message.sender_phone.isnot(None)
            ).having(func.count(Message.id) > 1).scalar() or 0
            
            # Average messages per user
            avg_messages_per_user = db_session.query(
                func.avg(func.count(Message.id))
            ).filter(
                Message.business_id == business_id,
                Message.direction == MessageDirection.INBOUND,
                Message.created_at >= start_date,
                Message.sender_phone.isnot(None)
            ).group_by(Message.sender_phone).scalar() or 0
            
            return_rate = (returning_users / unique_users * 100) if unique_users > 0 else 0
            
            return {
                'unique_users': unique_users,
                'returning_users': returning_users,
                'new_users': unique_users - returning_users,
                'return_rate': round(return_rate, 2),
                'avg_messages_per_user': round(avg_messages_per_user, 2)
            }
            
        except Exception as e:
            logger.error("Error getting user engagement metrics", 
                        business_id=business_id, error=str(e))
            return {}
    
    def generate_comprehensive_report(self, business_id: int, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive analytics report"""
        try:
            logger.info("Generating comprehensive analytics report", 
                       business_id=business_id, days=days)
            
            report = {
                'business_id': business_id,
                'period_days': days,
                'generated_at': datetime.utcnow().isoformat(),
                'message_analytics': self.get_message_analytics(business_id, days),
                'daily_trends': self.get_daily_message_trends(business_id, days),
                'language_distribution': self.get_language_distribution(business_id, days),
                'response_time_distribution': self.get_response_time_distribution(business_id, days),
                'confidence_distribution': self.get_confidence_score_distribution(business_id, days),
                'common_queries': self.get_common_queries(business_id, days),
                'peak_hours': self.get_peak_hours(business_id, days),
                'document_analytics': self.get_document_analytics(business_id),
                'engagement_metrics': self.get_user_engagement_metrics(business_id, days)
            }
            
            return report
            
        except Exception as e:
            logger.error("Error generating comprehensive report", 
                        business_id=business_id, error=str(e))
            return {}

# Helper functions for analytics
def calculate_growth_rate(current_value: float, previous_value: float) -> float:
    """Calculate growth rate percentage"""
    if previous_value == 0:
        return 100.0 if current_value > 0 else 0.0
    return ((current_value - previous_value) / previous_value) * 100

def get_performance_grade(response_rate: float, avg_response_time: float, avg_confidence: float) -> str:
    """Calculate overall performance grade"""
    score = 0
    
    # Response rate scoring (40% weight)
    if response_rate >= 95:
        score += 40
    elif response_rate >= 90:
        score += 35
    elif response_rate >= 80:
        score += 30
    elif response_rate >= 70:
        score += 25
    else:
        score += 20
    
    # Response time scoring (30% weight)
    if avg_response_time <= 2000:  # 2 seconds
        score += 30
    elif avg_response_time <= 5000:  # 5 seconds
        score += 25
    elif avg_response_time <= 10000:  # 10 seconds
        score += 20
    else:
        score += 15
    
    # Confidence scoring (30% weight)
    if avg_confidence >= 85:
        score += 30
    elif avg_confidence >= 75:
        score += 25
    elif avg_confidence >= 65:
        score += 20
    else:
        score += 15
    
    # Grade assignment
    if score >= 90:
        return 'A+'
    elif score >= 85:
        return 'A'
    elif score >= 80:
        return 'B+'
    elif score >= 75:
        return 'B'
    elif score >= 70:
        return 'C+'
    elif score >= 65:
        return 'C'
    else:
        return 'D'