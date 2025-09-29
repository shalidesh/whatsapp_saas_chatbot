from datetime import datetime, timedelta
import structlog
from typing import Optional, List, Dict, Any
import asyncio
import httpx  # ✅ Add httpx for async HTTP requests

from ..tasks.celery_app import celery_app
from ..services.document_service import DocumentService
from ..services.vector_service import VectorService
from ..models.document import Document, DocumentStatus
from ..models.business import Business
from ..config.database import db_session

logger = structlog.get_logger(__name__)

@celery_app.task(bind=True, max_retries=3)
def process_document_upload(self, document_id: int, file_path: str, business_id: int):
    """Process uploaded document for embedding generation"""
    try:
        logger.info("Starting document processing", 
                   document_id=document_id, file_path=file_path)
        
        document_service = DocumentService()
        vector_service = VectorService()
        
        # Update document status to processing
        document = db_session.query(Document).get(document_id)
        if not document:
            logger.error("Document not found", document_id=document_id)
            return
        
        document.status = DocumentStatus.PROCESSING
        db_session.commit()
        
        # Extract text from document (async call wrapped)
        try:
            if file_path.startswith('http'):
                # Handle URL-based documents
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    extracted_text = loop.run_until_complete(
                        document_service._extract_text_from_url(file_path)
                    )
                finally:
                    loop.close()
            else:
                # Handle file-based documents (sync)
                extracted_text = document_service.extract_text(file_path)
                
        except Exception as e:
            logger.error("Failed to extract text from document", 
                        document_id=document_id, error=str(e))
            document.status = DocumentStatus.FAILED
            document.processing_error = f"Text extraction failed: {str(e)}"
            db_session.commit()
            return
        
        if not extracted_text or len(extracted_text.strip()) < 10:
            logger.warning("No meaningful text extracted from document", 
                          document_id=document_id)
            document.status = DocumentStatus.FAILED
            document.processing_error = "No meaningful text content found"
            db_session.commit()
            return
        
        # Add to vector database (async call wrapped)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(
                    vector_service.add_document(
                        document_id=document_id,
                        content=extracted_text,
                        business_id=business_id
                    )
                )
            finally:
                loop.close()
        except Exception as e:
            logger.error("Failed to add document to vector database", 
                        document_id=document_id, error=str(e))
            document.status = DocumentStatus.FAILED
            document.processing_error = f"Vector indexing failed: {str(e)}"
            db_session.commit()
            
            # Retry task if not at max retries
            if self.request.retries < self.max_retries:
                logger.info("Retrying document processing", 
                           document_id=document_id, 
                           retry_count=self.request.retries + 1)
                raise self.retry(countdown=60 * (2 ** self.request.retries))
            return
        
        if success:
            # Update document status and metadata
            document.status = DocumentStatus.PROCESSED
            document.extracted_text = extracted_text[:1000]  # Store preview
            document.chunk_count = len(extracted_text) // 1000 + 1  # Estimate chunks
            document.updated_at = datetime.utcnow()
            db_session.commit()
            
            logger.info("Document processed successfully", 
                       document_id=document_id, 
                       text_length=len(extracted_text))
        else:
            document.status = DocumentStatus.FAILED
            document.processing_error = "Failed to index document"
            db_session.commit()
            
            logger.error("Document processing failed", document_id=document_id)
            
    except Exception as e:
        logger.error("Unexpected error processing document", 
                    document_id=document_id, error=str(e))
        
        # Update document status to failed
        try:
            document = db_session.query(Document).get(document_id)
            if document:
                document.status = DocumentStatus.FAILED
                document.processing_error = f"Processing error: {str(e)}"
                db_session.commit()
        except:
            pass
        
        # Retry task
        if self.request.retries < self.max_retries:
            logger.info("Retrying document processing due to error", 
                       document_id=document_id, 
                       retry_count=self.request.retries + 1)
            raise self.retry(countdown=60 * (2 ** self.request.retries))

@celery_app.task
def process_website_content(document_id: int, url: str, business_id: int):
    """Process website content for indexing"""
    try:
        logger.info("Processing website content", 
                   document_id=document_id, url=url)
        
        document_service = DocumentService()
        vector_service = VectorService()
        
        # Update document status
        document = db_session.query(Document).get(document_id)
        if not document:
            logger.error("Document not found", document_id=document_id)
            return
        
        document.status = DocumentStatus.PROCESSING
        db_session.commit()
        
        # Extract content from website (async)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                extracted_text = loop.run_until_complete(
                    document_service._extract_text_from_url(url)
                )
            finally:
                loop.close()
        except Exception as e:
            logger.error("Failed to extract website content", 
                        document_id=document_id, url=url, error=str(e))
            document.status = DocumentStatus.FAILED
            document.processing_error = f"Website extraction failed: {str(e)}"
            db_session.commit()
            return
        
        if not extracted_text or len(extracted_text.strip()) < 50:
            logger.warning("Insufficient content extracted from website", 
                          document_id=document_id, url=url)
            document.status = DocumentStatus.FAILED
            document.processing_error = "Insufficient website content"
            db_session.commit()
            return
        
        # Add to vector database (async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(
                vector_service.add_document(
                    document_id=document_id,
                    content=extracted_text,
                    business_id=business_id
                )
            )
        finally:
            loop.close()
        
        if success:
            document.status = DocumentStatus.PROCESSED
            document.extracted_text = extracted_text[:1000]
            document.chunk_count = len(extracted_text) // 1000 + 1
            document.updated_at = datetime.utcnow()
            db_session.commit()
            
            logger.info("Website content processed successfully", 
                       document_id=document_id, url=url)
        else:
            document.status = DocumentStatus.FAILED
            document.processing_error = "Failed to index website content"
            db_session.commit()
            
    except Exception as e:
        logger.error("Error processing website content", 
                    document_id=document_id, url=url, error=str(e))
        
        # Update status to failed
        try:
            document = db_session.query(Document).get(document_id)
            if document:
                document.status = DocumentStatus.FAILED
                document.processing_error = str(e)
                db_session.commit()
        except:
            pass

@celery_app.task
def rebuild_knowledge_base(business_id: int):
    """Rebuild entire knowledge base for a business"""
    try:
        logger.info("Rebuilding knowledge base", business_id=business_id)
        
        vector_service = VectorService()
        
        # Get all processed documents for the business
        documents = db_session.query(Document).filter(
            Document.business_id == business_id,
            Document.status == DocumentStatus.PROCESSED,
            Document.is_active == True
        ).all()
        
        if not documents:
            logger.info("No documents found for knowledge base rebuild", 
                       business_id=business_id)
            return
        
        # Clear existing vector data for this business (if method exists)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Assuming you have a clear_business_data method
                if hasattr(vector_service, 'clear_business_data'):
                    loop.run_until_complete(vector_service.clear_business_data(business_id))
            finally:
                loop.close()
        except Exception as e:
            logger.warning("Failed to clear existing vector data", 
                          business_id=business_id, error=str(e))
        
        # Reprocess each document
        successful_rebuilds = 0
        failed_rebuilds = 0
        
        for document in documents:
            try:
                # Re-extract text
                document_service = DocumentService()
                
                if document.file_path:
                    content = document_service.extract_text(document.file_path)
                elif document.url:
                    # Async call for URL content
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        content = loop.run_until_complete(
                            document_service._extract_text_from_url(document.url)
                        )
                    finally:
                        loop.close()
                else:
                    continue
                
                # Add to vector database (async)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    success = loop.run_until_complete(
                        vector_service.add_document(
                            document_id=document.id,
                            content=content,
                            business_id=business_id
                        )
                    )
                finally:
                    loop.close()
                
                if success:
                    successful_rebuilds += 1
                    logger.debug("Document rebuilt successfully", 
                               document_id=document.id)
                else:
                    failed_rebuilds += 1
                    logger.warning("Failed to rebuild document", 
                                 document_id=document.id)
                    
            except Exception as e:
                failed_rebuilds += 1
                logger.error("Error rebuilding document", 
                           document_id=document.id, error=str(e))
        
        logger.info("Knowledge base rebuild completed", 
                   business_id=business_id,
                   successful=successful_rebuilds,
                   failed=failed_rebuilds)
        
    except Exception as e:
        logger.error("Error rebuilding knowledge base", 
                    business_id=business_id, error=str(e))

@celery_app.task
def cleanup_failed_documents():
    """Clean up documents that failed processing"""
    try:
        logger.info("Starting cleanup of failed documents")
        
        # Find documents that have been in failed state for more than 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        failed_documents = db_session.query(Document).filter(
            Document.status == DocumentStatus.FAILED,
            Document.updated_at < cutoff_time
        ).all()
        
        cleaned_count = 0
        for document in failed_documents:
            try:
                # Delete from S3 if it's a file
                if document.file_path:
                    document_service = DocumentService()
                    try:
                        document_service.s3_client.delete_object(
                            Bucket=document_service.bucket_name,
                            Key=document.file_path
                        )
                    except Exception as e:
                        logger.warning("Failed to delete S3 file", 
                                     document_id=document.id, error=str(e))
                
                # Mark as inactive instead of deleting
                document.is_active = False
                db_session.commit()
                cleaned_count += 1
                
            except Exception as e:
                logger.error("Error cleaning up failed document", 
                           document_id=document.id, error=str(e))
        
        logger.info("Failed documents cleanup completed", 
                   cleaned_count=cleaned_count)
        
    except Exception as e:
        logger.error("Error during failed documents cleanup", error=str(e))

@celery_app.task
def generate_document_preview(document_id: int):
    """Generate preview for a document"""
    try:
        logger.info("Generating document preview", document_id=document_id)
        
        document = db_session.query(Document).get(document_id)
        if not document:
            logger.error("Document not found for preview generation", 
                        document_id=document_id)
            return
        
        document_service = DocumentService()
        
        # Extract text
        if document.file_path:
            content = document_service.extract_text(document.file_path)
        elif document.url:
            content = document_service.extract_text(document.url)
        else:
            logger.warning("No file path or URL for document", 
                          document_id=document_id)
            return
        
        # Generate preview (first 500 characters)
        preview = content[:500] + "..." if len(content) > 500 else content
        
        # Update document with preview
        document.extracted_text = preview
        document.updated_at = datetime.utcnow()
        db_session.commit()
        
        logger.info("Document preview generated successfully", 
                   document_id=document_id, preview_length=len(preview))
        
    except Exception as e:
        logger.error("Error generating document preview", 
                    document_id=document_id, error=str(e))

# In the validate_document_links function, update the metadata usage:

@celery_app.task
def validate_document_links():
    """Validate all document links and mark broken ones (async version)"""
    try:
        logger.info("Starting document link validation")
        
        # Get all URL-based documents
        url_documents = db_session.query(Document).filter(
            Document.url.isnot(None),
            Document.is_active == True
        ).all()
        
        validated_count = 0
        broken_count = 0
        
        # Use async httpx for validation
        async def validate_links():
            nonlocal validated_count, broken_count
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                for document in url_documents:
                    try:
                        response = await client.head(document.url)
                        if response.status_code >= 400:
                            # Mark as failed
                            document.status = DocumentStatus.FAILED
                            document.processing_error = f"URL returned status {response.status_code}"
                            broken_count += 1
                        else:
                            # Update last validated time
                            doc_metadata = document.document_metadata or {}
                            doc_metadata['last_validated'] = datetime.utcnow().isoformat()
                            document.document_metadata = doc_metadata
                            validated_count += 1
                        
                        db_session.commit()
                        
                    except Exception as e:
                        logger.warning("Failed to validate document URL", 
                                     document_id=document.id, url=document.url, error=str(e))
                        document.status = DocumentStatus.FAILED
                        document.processing_error = f"URL validation failed: {str(e)}"
                        broken_count += 1
                        db_session.commit()
        
        # Run async validation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(validate_links())
        finally:
            loop.close()
        
        logger.info("Document link validation completed", 
                   validated=validated_count, broken=broken_count)
        
    except Exception as e:
        logger.error("Error during document link validation", error=str(e))

@celery_app.task
def update_document_statistics():
    """Update document processing statistics"""
    try:
        logger.info("Updating document statistics")
        
        businesses = db_session.query(Business).filter(
            Business.is_active == True
        ).all()
        
        for business in businesses:
            try:
                # Count documents by status
                total_docs = db_session.query(Document).filter(
                    Document.business_id == business.id,
                    Document.is_active == True
                ).count()
                
                processed_docs = db_session.query(Document).filter(
                    Document.business_id == business.id,
                    Document.status == DocumentStatus.PROCESSED,
                    Document.is_active == True
                ).count()
                
                # Update business metadata (if you add a metadata field to Business model)
                metadata = {
                    'document_stats': {
                        'total_documents': total_docs,
                        'processed_documents': processed_docs,
                        'processing_rate': (processed_docs / total_docs * 100) if total_docs > 0 else 0,
                        'last_updated': datetime.utcnow().isoformat()
                    }
                }
                
                logger.debug("Updated document statistics for business", 
                           business_id=business.id, stats=metadata)
                
            except Exception as e:
                logger.error("Error updating stats for business", 
                           business_id=business.id, error=str(e))
        
        logger.info("Document statistics update completed")
        
    except Exception as e:
        logger.error("Error updating document statistics", error=str(e))

@celery_app.task
def schedule_periodic_tasks():
    """Schedule periodic maintenance tasks"""
    try:
        # Schedule cleanup task
        cleanup_failed_documents.delay()
        
        # Schedule link validation (daily)
        validate_document_links.delay()
        
        # Schedule statistics update
        update_document_statistics.delay()
        
        logger.info("Periodic document tasks scheduled")
        
    except Exception as e:
        logger.error("Error scheduling periodic tasks", error=str(e))

# Task monitoring helpers
def get_document_processing_status(document_id: int) -> Dict[str, Any]:
    """Get current processing status of a document"""
    try:
        document = db_session.query(Document).get(document_id)
        if not document:
            return {'error': 'Document not found'}
        
        return {
            'document_id': document_id,
            'status': document.status.value,
            'processing_error': document.processing_error,
            'chunk_count': document.chunk_count,
            'created_at': document.created_at.isoformat(),
            'updated_at': document.updated_at.isoformat()
        }
        
    except Exception as e:
        logger.error("Error getting document processing status", 
                    document_id=document_id, error=str(e))
        return {'error': 'Failed to get status'}

def get_business_processing_queue(business_id: int) -> Dict[str, Any]:
    """Get processing queue status for a business"""
    try:
        processing_docs = db_session.query(Document).filter(
            Document.business_id == business_id,
            Document.status == DocumentStatus.PROCESSING
        ).count()
        
        pending_docs = db_session.query(Document).filter(
            Document.business_id == business_id,
            Document.status == DocumentStatus.UPLOADED
        ).count()
        
        return {
            'business_id': business_id,
            'processing_documents': processing_docs,
            'pending_documents': pending_docs
        }
        
    except Exception as e:
        logger.error("Error getting business processing queue", 
                    business_id=business_id, error=str(e))
        return {'error': 'Failed to get queue status'}