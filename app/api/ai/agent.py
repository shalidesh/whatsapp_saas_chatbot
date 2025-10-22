from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel
import structlog

from ...services.ai_service import WhatsAppAIAgent
from ...middleware.auth import get_current_user
from ...models.business import Business
from ...models.user import User
from ...config.database import db_session

logger = structlog.get_logger(__name__)

ai_router = APIRouter()
ai_agent = WhatsAppAIAgent()
# Pydantic models
class TestMessageRequest(BaseModel):
    message: str
    business_id: int

class AIResponse(BaseModel):
    response: str
    language_detected: str
    confidence: int
    processing_time_ms: int

class TestMessageResponse(BaseModel):
    status: str
    ai_response: AIResponse

class AgentConfig(BaseModel):
    business_name: str
    ai_persona: str
    supported_languages: list
    default_language: str
    vector_db_type: str
    status: str

class AgentStatusResponse(BaseModel):
    status: str
    agent_config: AgentConfig

class ReloadKnowledgeRequest(BaseModel):
    business_id: int

class ReloadKnowledgeResponse(BaseModel):
    status: str
    message: str
    task_id: str

@ai_router.post("/test-message", response_model=TestMessageResponse)
async def test_ai_message(
    request: TestMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """Test AI agent response (for development/debugging)"""
    try:
        # Verify business ownership
        business = db_session.query(Business).filter(
            Business.id == request.business_id,
            Business.user_id == current_user.id,
            Business.is_active == True
        ).first()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found or access denied"
            )
        
        # Process message with AI agent (async call)
        response = await ai_agent.process_message(
            message=request.message,
            business_id=request.business_id,
            sender_phone="test_user"
        )
        
        logger.info("AI test message processed", 
                   business_id=request.business_id, 
                   user_id=current_user.id)
        
        return TestMessageResponse(
            status="success",
            ai_response=AIResponse(**response)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error testing AI message", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message"
        )

@ai_router.get("/agent-status", response_model=AgentStatusResponse)
async def get_agent_status(
    business_id: int = Query(..., description="Business ID"),
    current_user: User = Depends(get_current_user)
):
    """Get AI agent status and configuration"""
    try:
        # Verify business ownership
        business = db_session.query(Business).filter(
            Business.id == business_id,
            Business.user_id == current_user.id,
            Business.is_active == True
        ).first()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found or access denied"
            )
        
        # Get agent configuration
        agent_config = AgentConfig(
            business_name=business.name,
            ai_persona=business.ai_persona,
            supported_languages=business.supported_languages,
            default_language=business.default_language,
            vector_db_type="faiss",  # Could be made configurable
            status="active"
        )
        
        return AgentStatusResponse(
            status="success",
            agent_config=agent_config
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting agent status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent status"
        )

@ai_router.post("/reload-knowledge", response_model=ReloadKnowledgeResponse)
async def reload_knowledge_base(
    request: ReloadKnowledgeRequest,
    current_user: User = Depends(get_current_user)
):
    """Reload knowledge base for a business"""
    try:
        # Verify business ownership
        business = db_session.query(Business).filter(
            Business.id == request.business_id,
            Business.user_id == current_user.id,
            Business.is_active == True
        ).first()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found or access denied"
            )
        
        # Trigger knowledge base reload (this would typically be a Celery task)
        from ...tasks.document_processing import rebuild_knowledge_base
        task = rebuild_knowledge_base.delay(request.business_id)
        
        logger.info("Knowledge base reload triggered", 
                   business_id=request.business_id, 
                   task_id=task.id)
        
        return ReloadKnowledgeResponse(
            status="success",
            message="Knowledge base reload initiated",
            task_id=str(task.id)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error reloading knowledge base", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reload knowledge base"
        )

# Additional endpoints for tool management
@ai_router.get("/tools")
async def get_available_tools():
    """Get list of available AI tools"""
    try:
        from .tools import get_tool_descriptions
        tools = get_tool_descriptions()
        
        return {
            "status": "success",
            "tools": tools
        }
        
    except Exception as e:
        logger.error("Error getting available tools", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get available tools"
        )

@ai_router.post("/test-tool")
async def test_tool(
    tool_name: str,
    query: str,
    business_id: int,
    current_user: User = Depends(get_current_user)
):
    """Test individual AI tool (for debugging)"""
    try:
        # Verify business ownership
        business = db_session.query(Business).filter(
            Business.id == business_id,
            Business.user_id == current_user.id,
            Business.is_active == True
        ).first()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found or access denied"
            )
        
        # Import simple tool functions
        from .tools import (
            search_business_documents_simple,
            web_search_simple,
            translate_to_sinhala_simple,
            get_business_info_simple
        )
        
        # Execute the appropriate tool
        if tool_name == "search_business_documents":
            result = await search_business_documents_simple(query, business_id)
        elif tool_name == "web_search":
            result = await web_search_simple(query)
        elif tool_name == "translate_to_sinhala":
            result = await translate_to_sinhala_simple(query)
        elif tool_name == "get_business_info":
            result = get_business_info_simple(business.to_dict())
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown tool: {tool_name}"
            )
        
        logger.info("AI tool tested", 
                   tool_name=tool_name,
                   business_id=business_id, 
                   user_id=current_user.id)
        
        return {
            "status": "success",
            "tool_name": tool_name,
            "query": query,
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error testing AI tool", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test AI tool"
        )