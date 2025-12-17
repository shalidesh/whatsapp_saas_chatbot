import time
from typing import List, Dict, Any, Optional, TypedDict
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import Tool
from langgraph.graph import StateGraph, END
# Removed problematic ToolExecutor import
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langsmith import Client as LangSmithClient
# from langsmith import RunType
import structlog
import json
import requests
import numpy as np

from ..services.vector_service import VectorService, HuggingFaceEmbeddings
from ..services.web_search_service import WebSearchService
from ..services.google_sheets_service import GoogleSheetsService
from ..utils.sinhala_nlp import SinhalaNLP
from ..config.settings import config

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage as AzureSystemMessage, UserMessage as AzureUserMessage
from azure.core.credentials import AzureKeyCredential
# Keep existing imports but alias LangChain messages to avoid conflicts
from langchain_core.messages import HumanMessage, SystemMessage as LangChainSystemMessage


logger = structlog.get_logger(__name__)

# FIXED: Use TypedDict for LangGraph state instead of class
class AIAgentState(TypedDict):
    messages: List[Any]
    business_context: Dict[str, Any]
    search_results: List[Dict[str, Any]]
    google_sheets_results: List[Dict[str, Any]]
    web_search_results: List[Dict[str, Any]]
    final_response: str
    language: str
    confidence: int
    analysis: str

class WhatsAppAIAgent:
    def __init__(self):

        print(config.GITHUB_TOKEN)
        # github_token = self._clean_api_key(config.GITHUB_TOKEN)
        # GitHub Playground client setup
        self.github_client = ChatCompletionsClient(
            endpoint="https://models.github.ai/inference",
            credential=AzureKeyCredential(config.GITHUB_TOKEN),
        )
        self.model = "openai/gpt-4.1"

        # Embeddings and services - use Hugging Face API instead of local models
        model_name = config.HF_EMBEDDING_MODEL if not config.DEV_MODE else config.LITE_EMBEDDING_MODEL
        self.embeddings = HuggingFaceEmbeddings(
            api_key=config.HUGGINGFACE_API,
            model_name=f"sentence-transformers/{model_name}"
        )
        self.embedding_dimension = 384  # Standard dimension for MiniLM models
        self.vector_service = VectorService()
        self.web_search_service = WebSearchService()
        self.google_sheets_service = GoogleSheetsService()
        self.sinhala_nlp = SinhalaNLP()
        
        # Initialize LangSmith if API key is provided
        if hasattr(config, 'LANGCHAIN_API_KEY') and config.LANGCHAIN_API_KEY:
            self.langsmith_client = LangSmithClient(api_key=config.LANGCHAIN_API_KEY)
        else:
            self.langsmith_client = None
        
        # Initialize LangGraph workflow
        self.graph = self._create_agent_graph()

    def _clean_api_key(self, api_key: Optional[str]) -> Optional[str]:
        """Clean API key to remove whitespace and invalid characters"""
        if not api_key:
            return None
            
        # Remove whitespace, newlines, and other problematic characters
        cleaned = str(api_key).strip().replace('\n', '').replace('\r', '').replace('\t', '')
        
        if cleaned != api_key:
            logger.info("API key cleaned - had whitespace/newlines")
            
        return cleaned if cleaned else None
    
    def _create_agent_graph(self) -> StateGraph:
        """Create the LangGraph workflow for the AI agent"""

        # Create workflow graph with TypedDict state
        workflow = StateGraph(AIAgentState)

        # Add nodes
        workflow.add_node("analyze_query", self._analyze_query)
        workflow.add_node("search_internal", self._search_internal_data)
        workflow.add_node("search_google_sheets", self._search_google_sheets_data)
        workflow.add_node("search_web", self._search_web_data)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("translate_response", self._translate_response)

        # Set entry point
        workflow.set_entry_point("analyze_query")

        # Add edges
        workflow.add_edge("analyze_query", "search_internal")

        # NEW ROUTING LOGIC:
        # 1. After vector DB search, check if results are useful
        workflow.add_conditional_edges(
            "search_internal",
            self._route_after_vector_search,
            {
                "generate": "generate_response",  # If vector DB has useful results
                "google_sheets": "search_google_sheets"  # If vector DB empty/weak
            }
        )

        # 2. After Google Sheets search, check if results are useful
        workflow.add_conditional_edges(
            "search_google_sheets",
            self._route_after_google_sheets,
            {
                "generate": "generate_response",  # If Google Sheets has results
                "web_search": "search_web"  # If Google Sheets empty
            }
        )

        # 3. After web search, always generate response
        workflow.add_edge("search_web", "generate_response")

        # 4. After response generation, check if translation needed
        workflow.add_conditional_edges(
            "generate_response",
            self._should_translate,
            {
                "translate": "translate_response",
                "end": END
            }
        )

        workflow.add_edge("translate_response", END)

        return workflow.compile()
    
    async def process_message(self, message: str, business_id: int, sender_phone: str) -> Dict[str, Any]:
        """Process incoming WhatsApp message and generate AI response"""
        start_time = time.time()
        
        try:
            print("Processing message---------------:", message)
            # Detect language
            detected_language = self.sinhala_nlp.detect_language(message)
            print(f"Detected language-------------: {detected_language}")
            
            # Initialize state as dictionary (not class instance)
            state: AIAgentState = {
                "messages": [HumanMessage(content=message)],
                "business_context": await self._get_business_context(business_id),
                "search_results": [],
                "google_sheets_results": [],
                "web_search_results": [],
                "final_response": "",
                "language": detected_language,
                "confidence": 0,
                "analysis": ""
            }

            print(f"Detected language: {detected_language}")
            print(f"Initial state: {json.dumps({k: v if k != 'messages' else [{'type': 'HumanMessage', 'content': m.content} for m in v] for k, v in state.items()}, indent=2)}")
            
            # Run the agent workflow
            result = await self.graph.ainvoke(state)
            print(f'------final results--------:{result}')
            
            processing_time = int((time.time() - start_time) * 1000)
            
            response_data = {
                'response': result["final_response"],
                'language_detected': detected_language,
                'confidence': result["confidence"],
                'processing_time_ms': processing_time
            }
            
            # Log to LangSmith if available
            if self.langsmith_client:
                self._log_to_langsmith(message, response_data, business_id, sender_phone)
            
            return response_data
            
        except Exception as e:
            logger.error("Error processing message", error=str(e), business_id=business_id)
            processing_time = int((time.time() - start_time) * 1000)
            return {
                'response': self._get_error_response(detected_language if 'detected_language' in locals() else 'en'),
                'language_detected': detected_language if 'detected_language' in locals() else 'en',
                'confidence': 0,
                'processing_time_ms': processing_time
            } 
    # FIXED: All node functions now return dictionaries instead of state objects
    async def _analyze_query(self, state: AIAgentState) -> AIAgentState:
        """Analyze the user query to understand intent"""
        user_message = state["messages"][-1].content
        
        analysis_prompt = f"""
        Analyze this user query in {state["language"]} language:
        "{user_message}"
        
        Business Context: {state["business_context"].get('name', 'Unknown Business')}
        
        Determine:
        1. What information the user is seeking
        2. Whether this requires business-specific data
        3. Whether external search might be needed
        4. The appropriate response tone for this business
        
        Response should be in {state["language"]}.
        """
        
        try:
            response = self.github_client.complete(
                messages=[
                    AzureSystemMessage(analysis_prompt)
                ],
                temperature=0.7,
                top_p=1.0,
                model=self.model
            )
            analysis = response.choices[0].message.content
            logger.info("Query analyzed", analysis=analysis[:100])
        except Exception as e:
            logger.error("Error analyzing query", error=str(e))
            analysis = "General inquiry"
        
        # Return updated state dictionary
        return {
            **state,
            "analysis": analysis
        }
       
    async def _search_internal_data(self, state: AIAgentState) -> AIAgentState:
        """Search through business documents and data"""
        user_query = state["messages"][-1].content
        business_id = state["business_context"].get('id')
        
        try:
            # Search vector database for relevant business documents
            search_results = await self.vector_service.search(
                query=user_query,
                business_id=business_id,
                top_k=5
            )
            
            logger.info("Internal search completed", results_count=len(search_results))
            
        except Exception as e:
            logger.error("Error searching internal data", error=str(e))
            search_results = []
        
        # Return updated state dictionary
        return {
            **state,
            "search_results": search_results
        }
    
    async def _search_google_sheets_data(self, state: AIAgentState) -> AIAgentState:
        """Search Google Sheets for business data"""
        user_query = state["messages"][-1].content
        business_id = state["business_context"].get('id')

        try:
            # Get active Google Sheets connections for this business
            from ..models.google_sheet import GoogleSheetConnection
            from ..config.database import db_session

            active_sheets = db_session.query(GoogleSheetConnection).filter(
                GoogleSheetConnection.business_id == business_id,
                GoogleSheetConnection.is_active == True
            ).all()

            google_sheets_results = []

            # Search through all active sheets
            for sheet_connection in active_sheets:
                try:
                    result = await self.google_sheets_service.query_sheet(
                        business_id=business_id,
                        sheet_connection_id=sheet_connection.id,
                        query=user_query,
                        max_results=5
                    )

                    if result.get('success') and result.get('rows'):
                        google_sheets_results.extend([
                            {
                                'sheet_name': sheet_connection.name,
                                'data': row,
                                'source': 'google_sheets'
                            }
                            for row in result['rows']
                        ])

                except Exception as e:
                    logger.error(f"Error searching sheet {sheet_connection.id}", error=str(e))
                    continue

            logger.info("Google Sheets search completed", results_count=len(google_sheets_results))

        except Exception as e:
            logger.error("Error searching Google Sheets", error=str(e))
            google_sheets_results = []

        # Return updated state dictionary
        return {
            **state,
            "google_sheets_results": google_sheets_results
        }

    async def _search_web_data(self, state: AIAgentState) -> AIAgentState:
        """Search web for additional information"""
        user_query = state["messages"][-1].content

        try:
            web_results = await self.web_search_service.search(user_query)
            logger.info("Web search completed", results_count=len(web_results))

        except Exception as e:
            logger.error("Error searching web", error=str(e))
            web_results = []

        # Return updated state dictionary
        return {
            **state,
            "web_search_results": web_results
        }
    
    async def _generate_response(self, state: AIAgentState) -> AIAgentState:

        if not self.github_client:
                raise Exception("GitHub AI client not available")

        """Generate final response using LLM"""
        user_query = state["messages"][-1].content
        business_context = state["business_context"]
        internal_results = state["search_results"]
        google_sheets_results = state.get("google_sheets_results", [])
        web_results = state.get("web_search_results", [])

        # Prepare context
        context_parts = []

        if internal_results:
            context_parts.append("Business Documents Information:")
            for result in internal_results[:3]:  # Top 3 results
                context_parts.append(f"- {result.get('content', '')[:200]}...")

        if google_sheets_results:
            context_parts.append("\nProduct/Inventory Information from Google Sheets:")
            for result in google_sheets_results[:5]:  # Top 5 results
                sheet_name = result.get('sheet_name', 'Unknown Sheet')
                data = result.get('data', {})
                # Format the data nicely
                data_str = ", ".join([f"{k}: {v}" for k, v in data.items() if v is not None])
                context_parts.append(f"- [{sheet_name}] {data_str}")

        if web_results:
            context_parts.append("\nAdditional Web Information:")
            for result in web_results[:2]:  # Top 2 results
                context_parts.append(f"- {result.get('snippet', '')[:200]}...")

        context = "\n".join(context_parts)
        
        # Generate response
        response_prompt = f"""
        You are a helpful AI assistant for {business_context.get('name', 'this business')}.
        
        Business Description: {business_context.get('description', 'A Sri Lankan business')}
        AI Persona: {business_context.get('ai_persona', 'You are a helpful business assistant.')}
        
        User Query: "{user_query}"
        
        Available Context:
        {context}
        
        Instructions:
        1. Respond in {state["language"]} language (Sinhala if si, English if en)
        2. Be helpful, friendly, and professional
        3. Use the business context and available information
        4. If you don't have specific information, politely say so
        5. Keep responses concise but informative
        6. Include relevant business information when appropriate
        
        Generate a helpful response:
        """
        try:
            response = self.github_client.complete(
                messages=[
                    AzureSystemMessage(response_prompt),
                    AzureUserMessage(user_query)
                ],
                temperature=0.7,
                top_p=1.0,
                model=self.model
            )
            final_response = response.choices[0].message.content
            confidence = 85 if (internal_results or google_sheets_results or web_results) else 60
            
        except Exception as e:
            logger.error("Error generating response", error=str(e))
            final_response = self._get_error_response(state["language"])
            confidence = 0
        
        # Return updated state dictionary
        return {
            **state,
            "final_response": final_response,
            "confidence": confidence
        }
    
    async def _translate_response(self, state: AIAgentState) -> AIAgentState:
        """Translate response if needed"""
        final_response = state["final_response"]
        
        if state["language"] == 'si' and not self.sinhala_nlp.is_sinhala_text(final_response):
            try:
                translated = await self.sinhala_nlp.translate_to_sinhala(final_response)
                final_response = translated
            except Exception as e:
                logger.error("Error translating to Sinhala", error=str(e))
        
        # Return updated state dictionary
        return {
            **state,
            "final_response": final_response
        }
    
    def _route_after_vector_search(self, state: AIAgentState) -> str:
        """
        Routing logic after vector DB search.
        If vector DB has useful results → go to generate_response
        If vector DB is empty or weak → go to Google Sheets
        """
        internal_results = state["search_results"]

        # If we have good internal results (>= 2 results), generate response
        if internal_results and len(internal_results) >= 2:
            logger.info("Vector DB has useful results, proceeding to generate response")
            return "generate"

        # If internal results are weak or empty, try Google Sheets
        logger.info("Vector DB results weak/empty, proceeding to Google Sheets search")
        return "google_sheets"

    def _route_after_google_sheets(self, state: AIAgentState) -> str:
        """
        Routing logic after Google Sheets search.
        If Google Sheets has useful results → go to generate_response
        If Google Sheets is empty → go to web search
        """
        google_sheets_results = state["google_sheets_results"]

        # If we have Google Sheets results, generate response
        if google_sheets_results and len(google_sheets_results) > 0:
            logger.info("Google Sheets has useful results, proceeding to generate response")
            return "generate"

        # If Google Sheets is also empty, try web search as fallback
        logger.info("Google Sheets results empty, proceeding to web search")
        return "web_search"
    
    def _should_translate(self, state: AIAgentState) -> str:
        """Determine if translation is needed"""
        if state["language"] == 'si' and not self.sinhala_nlp.is_sinhala_text(state["final_response"]):
            return "translate"
        return "end"
    
    # Keep other methods the same...
    async def _get_business_context(self, business_id: int) -> Dict[str, Any]:
        """Get business context from database"""
        try:
            from ..models.business import Business
            from ..config.database import db_session
            
            business = db_session.query(Business).filter(
                Business.id == business_id,
                Business.is_active == True
            ).first()
            
            if business:
                return {
                    'id': business.id,
                    'name': business.name,
                    'description': business.description,
                    'ai_persona': business.ai_persona,
                    'supported_languages': business.supported_languages,
                    'default_language': business.default_language
                }
        except Exception as e:
            logger.error("Error getting business context", error=str(e))
        
        # Fallback context
        return {
            'id': business_id,
            'name': 'Sample Business',
            'description': 'A Sri Lankan business',
            'ai_persona': 'You are a helpful business assistant.'
        }
    
    def _get_error_response(self, language: str) -> str:
        """Get error response in appropriate language"""
        if language == 'si':
            return "කණගාටුයි, දැන් මට ඔබගේ ප්‍රශ්නයට පිළිතුරු දීමට අපහසුයි. කරුණාකර පසුව නැවත උත්සාහ කරන්න."
        else:
            return "Sorry, I'm having trouble processing your request right now. Please try again later."
    
    def _log_to_langsmith(self, message: str, response: Dict, business_id: int, sender_phone: str):
        """Log interaction to LangSmith for monitoring"""
        if not self.langsmith_client:
            return
        try:
            self.langsmith_client.create_run(
                name="whatsapp_message_processing",
                run_type="chain",
                # run_type=RunType.CHAIN,  # Add this required parameter
                inputs={"message": message, "business_id": business_id},
                outputs=response,
                metadata={
                    "sender_phone": sender_phone,
                    "processing_time_ms": response.get('processing_time_ms'),
                    "confidence": response.get('confidence')
                }
            )
        except Exception as e:
            logger.error("Error logging to LangSmith", error=str(e))


# Tool functions for direct use (without ToolExecutor)
async def search_business_documents(query: str, business_id: int) -> str:
    """Search through business documents"""
    try:
        vector_service = VectorService()
        results = await vector_service.search(
            query=query,
            business_id=business_id,
            top_k=3
        )
        
        if not results:
            return "No relevant information found in business documents."
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_results.append(f"{i}. {result.get('content', '')[:200]}...")
        
        return "Relevant business information:\n" + "\n".join(formatted_results)
        
    except Exception as e:
        logger.error("Error in business document search", error=str(e))
        return "Error accessing business documents. Please try again."

async def web_search_tool(query: str) -> str:
    """Search the web for information"""
    try:
        web_search_service = WebSearchService()
        results = await web_search_service.search(query, num_results=3)
        
        if not results:
            return "No relevant information found on the web."
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_results.append(f"{i}. {result.get('title', 'Unknown')}: {result.get('snippet', '')[:150]}...")
        
        return "Web search results:\n" + "\n".join(formatted_results)
        
    except Exception as e:
        logger.error("Error in web search", error=str(e))
        return "Error searching the web. Please try again later."

async def translate_to_sinhala_tool(text: str) -> str:
    """Translate text to Sinhala"""
    try:
        sinhala_nlp = SinhalaNLP()
        translated = await sinhala_nlp.translate_to_sinhala(text)
        return translated
    except Exception as e:
        logger.error("Error in Sinhala translation", error=str(e))
        return text  # Return original text if translation fails
    