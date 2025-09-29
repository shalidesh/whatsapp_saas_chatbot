from fastapi import APIRouter, HTTPException, status, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import structlog
import redis
import pika
from celery import Celery
import asyncio
import json
from datetime import datetime, timedelta

from ...services.whatsapp_service import WhatsAppService
from ...services.ai_service import WhatsAppAIAgent
from ...tasks.ai_processing import process_whatsapp_message
from ...models.message import Message, MessageDirection, MessageStatus
from ...models.business import Business
from ...config.database import db_session
from ...config.settings import config
from .client import whatsapp_client

logger = structlog.get_logger(__name__)

whatsapp_router = APIRouter()

whatsapp_service = WhatsAppService()
ai_agent = WhatsAppAIAgent()

# Pydantic models
class SendMessageRequest(BaseModel):
    to: str
    message: str

class SendMessageResponse(BaseModel):
    status: str

class WebhookResponse(BaseModel):
    status: str
    message: Optional[str] = None

class CeleryWorkerInfo(BaseModel):
    hostname: str
    status: str
    active_tasks: int
    processed_tasks: int
    load_avg: Optional[List[float]] = None
    pool: Optional[Dict[str, Any]] = None

class CeleryStatusResponse(BaseModel):
    celery_running: bool
    redis_connected: bool
    rabbitmq_connected: bool
    active_workers: int
    workers: List[CeleryWorkerInfo] = []
    broker_url: str
    result_backend: str
    queues: List[str] = []
    error_details: Optional[str] = None
    last_check: datetime

@whatsapp_router.get("/webhook")
async def verify_webhook(
    mode: str = Query(alias="hub.mode"),
    token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge")
):
    """Verify WhatsApp webhook"""
    try:
        verified_challenge = whatsapp_service.verify_webhook(mode, token, challenge)
        
        if verified_challenge:
            return PlainTextResponse(content=verified_challenge, status_code=200)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Verification failed"
            )
    except Exception as e:
        logger.error("Error verifying webhook", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook verification error"
        )

@whatsapp_router.post("/webhook", response_model=WebhookResponse)
async def handle_webhook(request: Request):
    """Handle incoming WhatsApp messages"""
    try:
        webhook_data = await request.json()  
        if not webhook_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data received"
            )
        
        # Parse message
        parsed_message = whatsapp_service.parse_webhook_message(webhook_data)

        # print(parsed_message)
        
        if not parsed_message:
            logger.info("No message to process in webhook")
            return WebhookResponse(status="ok")
        
        # Find business by phone number
        business = await find_business_by_phone(config.WHATSAPP_PHONE_NUMBER_ID)
        
        if not business:
            logger.error("Business not found for phone number", 
                        phone=config.WHATSAPP_PHONE_NUMBER_ID)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        # Store message in database
        message = Message(
            business_id=business.id,
            whatsapp_message_id=parsed_message['message_id'],
            direction=MessageDirection.INBOUND,
            content=parsed_message['content'],
            content_type=parsed_message['message_type'],
            sender_phone=parsed_message['from_phone'],
            recipient_phone=config.WHATSAPP_PHONE_NUMBER_ID,
            sender_name=parsed_message['sender_name'],
            status=MessageStatus.RECEIVED,
            message_metadata={}  # Use message_metadata instead of metadata
        )
        
        db_session.add(message)
        db_session.commit()
        
        # Process message asynchronously
        process_whatsapp_message.delay(
            message_id=message.id,
            business_id=business.id,
            content=parsed_message['content'],
            sender_phone=parsed_message['from_phone']
        )
        
        logger.info("Message queued for processing", 
                   message_id=message.id,
                   sender_phone=parsed_message['from_phone'])
        
        return WebhookResponse(status="ok")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error handling webhook", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

async def find_business_by_phone(phone_number: str) -> Optional[Business]:
    """Find business by WhatsApp phone number"""
    try:
        print(phone_number)
        return db_session.query(Business).filter(
            Business.whatsapp_phone_number == phone_number,
            Business.is_active == True
        ).first()
    except Exception as e:
        logger.error("Error finding business by phone", error=str(e))
        return None

@whatsapp_router.post("/send-message", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest):
    """Send message via WhatsApp (for testing)"""
    try:
        if not request.to or not request.message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing to or message"
            )
        
        success = await whatsapp_service.send_message(request.to, request.message)
        
        if success:
            return SendMessageResponse(status="sent")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send message"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error sending message", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# Additional webhook management endpoints
@whatsapp_router.get("/webhook/status")
async def get_webhook_status():
    """Get webhook status and configuration"""
    try:
        return {
            "status": "active",
            "phone_number_id": config.WHATSAPP_PHONE_NUMBER_ID,
            "webhook_url": f"{config.BASE_URL}/api/whatsapp/webhook",
            "verify_token_configured": bool(config.WHATSAPP_WEBHOOK_VERIFY_TOKEN)
        }
    except Exception as e:
        logger.error("Error getting webhook status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get webhook status"
        )

@whatsapp_router.get("/debug/celery-status", response_model=CeleryStatusResponse)
async def get_celery_status():
    """Check Celery workers, Redis, and RabbitMQ status"""
    try:
        # Initialize status response
        celery_status = CeleryStatusResponse(
            celery_running=False,
            redis_connected=False,
            rabbitmq_connected=False,
            active_workers=0,
            workers=[],
            broker_url=getattr(config, 'CELERY_BROKER_URL', 'redis://redis:6379/0'),
            result_backend=getattr(config, 'CELERY_RESULT_BACKEND', 'redis://redis:6379/0'),
            queues=[],
            last_check=datetime.utcnow()
        )
        
        error_details = []
        
        # Check Redis connection
        try:
            redis_client = redis.Redis.from_url(celery_status.result_backend, decode_responses=True)
            redis_client.ping()
            celery_status.redis_connected = True
            logger.info("Redis connection successful")
        except Exception as e:
            error_details.append(f"Redis connection failed: {str(e)}")
            logger.error("Redis connection failed", error=str(e))
        
        # Check RabbitMQ connection
        try:
            # Parse RabbitMQ URL from broker URL if it's RabbitMQ
            broker_url = celery_status.broker_url
            if 'rabbitmq' in broker_url or 'amqp' in broker_url:
                # Simple connection test for RabbitMQ
                connection_params = pika.URLParameters(broker_url)
                connection = pika.BlockingConnection(connection_params)
                channel = connection.channel()
                channel.close()
                connection.close()
                celery_status.rabbitmq_connected = True
                logger.info("RabbitMQ connection successful")
            else:
                # If using Redis as broker, skip RabbitMQ check
                celery_status.rabbitmq_connected = True
                logger.info("Using Redis as broker, RabbitMQ check skipped")
        except Exception as e:
            error_details.append(f"RabbitMQ connection failed: {str(e)}")
            logger.error("RabbitMQ connection failed", error=str(e))
        
        # Check Celery workers
        try:
            # Create Celery app instance for inspection
            celery_app = Celery('tasks')
            celery_app.config_from_object(config, namespace='CELERY')
            
            # Get worker statistics
            inspect = celery_app.control.inspect()
            
            # Check if workers are active (with timeout)
            try:
                stats = inspect.stats()
                active_tasks = inspect.active()
                reserved_tasks = inspect.reserved()
                
                if stats:
                    celery_status.celery_running = True
                    celery_status.active_workers = len(stats)
                    
                    for hostname, worker_stats in stats.items():
                        worker_info = CeleryWorkerInfo(
                            hostname=hostname,
                            status="online",
                            active_tasks=len(active_tasks.get(hostname, [])) if active_tasks else 0,
                            processed_tasks=worker_stats.get('total', {}).get('tasks.ai_processing.process_whatsapp_message', 0),
                            load_avg=worker_stats.get('rusage', {}).get('utime', None),
                            pool=worker_stats.get('pool', {})
                        )
                        celery_status.workers.append(worker_info)
                    
                    logger.info("Celery workers found", count=celery_status.active_workers)
                else:
                    error_details.append("No Celery workers found or workers not responding")
                    logger.warning("No Celery workers found")
                    
            except Exception as worker_e:
                error_details.append(f"Failed to get worker stats: {str(worker_e)}")
                logger.error("Failed to get worker stats", error=str(worker_e))
                
                # Try alternative method - check if any workers are registered
                try:
                    registered = inspect.registered()
                    if registered:
                        celery_status.celery_running = True
                        celery_status.active_workers = len(registered)
                        logger.info("Celery workers detected via registered tasks")
                except Exception as reg_e:
                    error_details.append(f"Alternative worker check failed: {str(reg_e)}")
                    logger.error("Alternative worker check failed", error=str(reg_e))
            
            # Get queue information
            try:
                active_queues = inspect.active_queues()
                if active_queues:
                    all_queues = set()
                    for worker_queues in active_queues.values():
                        for queue in worker_queues:
                            all_queues.add(queue.get('name', 'unknown'))
                    celery_status.queues = list(all_queues)
            except Exception as queue_e:
                error_details.append(f"Failed to get queue info: {str(queue_e)}")
                logger.error("Failed to get queue info", error=str(queue_e))
                
        except Exception as celery_e:
            error_details.append(f"Celery inspection failed: {str(celery_e)}")
            logger.error("Celery inspection failed", error=str(celery_e))
        
        # Set error details if any errors occurred
        if error_details:
            celery_status.error_details = "; ".join(error_details)
        
        # Log overall status
        logger.info("Celery status check completed",
                   celery_running=celery_status.celery_running,
                   redis_connected=celery_status.redis_connected,
                   rabbitmq_connected=celery_status.rabbitmq_connected,
                   active_workers=celery_status.active_workers)
        
        return celery_status
        
    except Exception as e:
        logger.error("Error checking Celery status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check Celery status: {str(e)}"
        )

# Health check endpoint that includes Celery status
@whatsapp_router.get("/health")
async def health_check():
    """Comprehensive health check including Celery status"""
    try:
        celery_status = await get_celery_status()
        
        overall_health = {
            "service": "whatsapp_webhook",
            "status": "healthy" if (
                celery_status.celery_running and 
                celery_status.redis_connected and
                celery_status.active_workers > 0
            ) else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "celery_workers": {
                    "status": "up" if celery_status.celery_running else "down",
                    "active_workers": celery_status.active_workers
                },
                "redis": {
                    "status": "up" if celery_status.redis_connected else "down"
                },
                "rabbitmq": {
                    "status": "up" if celery_status.rabbitmq_connected else "down"
                },
                "whatsapp_api": {
                    "status": "up",  # Could add actual WhatsApp API check here
                    "phone_number_id": config.WHATSAPP_PHONE_NUMBER_ID
                }
            }
        }
        
        if celery_status.error_details:
            overall_health["errors"] = celery_status.error_details
        
        return overall_health
        
    except Exception as e:
        logger.error("Error in health check", error=str(e))
        return {
            "service": "whatsapp_webhook",
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@whatsapp_router.post("/test-connection")
async def test_whatsapp_connection():
    """Test WhatsApp API connection"""
    try:
        # Try to get business profile to test connection
        profile = whatsapp_client.get_business_profile()
        
        if profile:
            return {
                "status": "connected",
                "business_profile": profile
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="WhatsApp API connection failed"
            )
            
    except Exception as e:
        logger.error("Error testing WhatsApp connection", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Connection test failed"
        )

# Advanced messaging endpoints
@whatsapp_router.post("/send-template")
async def send_template_message(
    to: str,
    template_name: str,
    language_code: str = "en",
    parameters: Optional[list] = None
):
    """Send WhatsApp template message"""
    try:
        message_id = await whatsapp_client.send_template_message(
            to=to,
            template_name=template_name,
            language_code=language_code,
            parameters=parameters or []
        )
        
        if message_id:
            return {"status": "sent", "message_id": message_id}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send template message"
            )
            
    except Exception as e:
        logger.error("Error sending template message", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Template message sending failed"
        )

@whatsapp_router.post("/send-interactive")
async def send_interactive_message(
    to: str,
    header: str,
    body: str,
    buttons: list
):
    """Send WhatsApp interactive message with buttons"""
    try:
        message_id = await whatsapp_client.send_interactive_message(
            to=to,
            header=header,
            body=body,
            buttons=buttons
        )
        
        if message_id:
            return {"status": "sent", "message_id": message_id}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send interactive message"
            )
            
    except Exception as e:
        logger.error("Error sending interactive message", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Interactive message sending failed"
        )

# Message status tracking
@whatsapp_router.post("/mark-read/{message_id}")
async def mark_message_read(message_id: str):
    """Mark a WhatsApp message as read"""
    try:
        success = await whatsapp_client.mark_message_as_read(message_id)
        
        if success:
            return {"status": "marked_as_read", "message_id": message_id}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to mark message as read"
            )
            
    except Exception as e:
        logger.error("Error marking message as read", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark message as read"
        )
    
@whatsapp_router.post("/debug/test-task")
async def test_celery_task():
    """Test Celery task execution"""
    try:
        from ...tasks.ai_processing import process_whatsapp_message
        
        result = process_whatsapp_message.delay(
            message_id=1000,
            business_id=4,
            content="Test message for debugging",
            sender_phone="+1234567890"
        )
        
        return {
            "task_id": result.id,
            "task_state": result.state,
            "message": "Test task queued successfully"
        }
        
    except Exception as e:
        logger.error("Error testing Celery task", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@whatsapp_router.get("/debug/task-status/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a specific task"""
    try:
        from ...tasks.celery_app import celery_app
        
        result = celery_app.AsyncResult(task_id)
        
        return {
            "task_id": task_id,
            "state": result.state,
            "result": result.result,
            "traceback": result.traceback if result.traceback else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))