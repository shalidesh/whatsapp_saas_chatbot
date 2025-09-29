import asyncio
from celery import Celery
from datetime import datetime
import structlog

from ..tasks.celery_app import celery_app
from ..services.ai_service import WhatsAppAIAgent
from ..services.whatsapp_service import WhatsAppService
from ..models.message import Message, MessageStatus, MessageDirection
from ..config.database import db_session

logger = structlog.get_logger(__name__)

ai_agent = WhatsAppAIAgent()
whatsapp_service = WhatsAppService()

@celery_app.task(bind=True, max_retries=3)
def process_whatsapp_message(self, message_id: int, business_id: int, 
                           content: str, sender_phone: str):
    """Process WhatsApp message with AI agent"""
    try:
        logger.info("Processing WhatsApp message TASK Started", 
                   message_id=message_id, business_id=business_id)
         
        
        # Update message status
        message = db_session.query(Message).get(message_id)
        if not message:
            logger.error("Message not found", message_id=message_id)
            return
        
        message.status = MessageStatus.PROCESSING
        db_session.commit()
        
        # Process with AI agent (run async function in sync context)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            ai_response = loop.run_until_complete(
                ai_agent.process_message(content, business_id, sender_phone)
            )

            # Send response via WhatsApp (async call)
            success = loop.run_until_complete(
                whatsapp_service.send_message(
                    to=sender_phone,
                    message=ai_response['response']
                )
            )
        except Exception as e:
            logger.error("Error in async processing", error=str(e))
            success = False
            ai_response = {'response': 'Error processing request', 'language_detected': 'en',
                          'processing_time_ms': 0, 'confidence': 0}
        finally:
            # Properly close the event loop and clean up
            try:
                # Cancel all running tasks
                pending_tasks = asyncio.all_tasks(loop)
                for task in pending_tasks:
                    task.cancel()

                # Wait for tasks to be cancelled
                if pending_tasks:
                    loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))

                loop.close()
            except Exception as cleanup_error:
                logger.error("Error during event loop cleanup", error=str(cleanup_error))
        
        if success:
            # Store outbound message
            outbound_message = Message(
                business_id=business_id,
                direction=MessageDirection.OUTBOUND,
                content=ai_response['response'],
                sender_phone=message.recipient_phone,
                recipient_phone=sender_phone,
                status=MessageStatus.RESPONDED,
                language_detected=ai_response['language_detected'],
                processing_time_ms=ai_response['processing_time_ms'],
                confidence_score=ai_response['confidence']
            )
            
            db_session.add(outbound_message)
            
            # Update original message
            message.status = MessageStatus.RESPONDED
            message.ai_response = ai_response['response']
            message.language_detected = ai_response['language_detected']
            message.processing_time_ms = ai_response['processing_time_ms']
            message.confidence_score = ai_response['confidence']
            
            db_session.commit()

            logger.info("Message processed successfully",
                       message_id=message_id,
                       processing_time=ai_response['processing_time_ms'])
        else:
            # Mark as failed
            message.status = MessageStatus.FAILED
            db_session.commit()

            logger.error("Failed to send WhatsApp response",
                        message_id=message_id)
            
    except Exception as e:
        logger.error("Error processing WhatsApp message TASK", 
                    message_id=message_id, error=str(e))
        
        # Update message status to failed
        try:
            message = db_session.query(Message).get(message_id)
            if message:
                message.status = MessageStatus.FAILED
                db_session.commit()
        except:
            pass
        
        # Retry task
        if self.request.retries < self.max_retries:
            logger.info("Retrying message processing",
                       message_id=message_id,
                       retry_count=self.request.retries + 1)
            raise self.retry(countdown=60 * (2 ** self.request.retries))
    finally:
        # Always clean up database session
        try:
            db_session.close()
        except Exception as db_cleanup_error:
            logger.error("Error cleaning up database session", error=str(db_cleanup_error))
        
@celery_app.task
def process_document_upload(document_id: int, file_path: str, business_id: int):
    """Process uploaded document for embedding generation"""
    try:
        from ..services.document_service import DocumentService
        from ..services.vector_service import VectorService
        
        document_service = DocumentService()
        vector_service = VectorService()
        
        logger.info("Processing document upload", 
                   document_id=document_id, file_path=file_path)
        
        # Extract text from document
        extracted_text = document_service.extract_text(file_path)
        
        if extracted_text:
            # Add to vector database
            success = vector_service.add_document(
                document_id=document_id,
                content=extracted_text,
                business_id=business_id
            )
            
            if success:
                # Update document status
                from ..models.document import Document, DocumentStatus
                document = db_session.query(Document).get(document_id)
                if document:
                    document.status = DocumentStatus.PROCESSED
                    document.extracted_text = extracted_text[:1000]  # Store preview
                    db_session.commit()
                
                logger.info("Document processed successfully", 
                           document_id=document_id)
            else:
                raise Exception("Failed to add document to vector database")
        else:
            raise Exception("Failed to extract text from document")
            
    except Exception as e:
        logger.error("Error processing document", 
                    document_id=document_id, error=str(e))
        
        # Update document status to failed
        try:
            from ..models.document import Document, DocumentStatus
            document = db_session.query(Document).get(document_id)
            if document:
                document.status = DocumentStatus.FAILED
                document.processing_error = str(e)
                db_session.commit()
        except:
            pass
        finally:
            # Always clean up database session
            try:
                db_session.close()
            except Exception as db_cleanup_error:
                logger.error("Error cleaning up database session in document processing", error=str(db_cleanup_error))