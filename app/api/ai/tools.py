from typing import List, Dict, Any, Optional, Type
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import Field
import structlog

from ...services.vector_service import VectorService
from ...services.web_search_service import WebSearchService
from ...services.google_sheets_service import GoogleSheetsService
from ...utils.sinhala_nlp import SinhalaNLP
from ...models.google_sheet import GoogleSheetConnection
from ...config.database import db_session

logger = structlog.get_logger(__name__)


"""
Add these lines at the top of tools.py to make it more async-friendly:
"""

# Add this async wrapper function to tools.py:
async def execute_tool_async(tool_name: str, query: str, business_id: int = None, business_context: dict = None) -> str:
    """Async wrapper for executing tools"""
    try:
        if tool_name == "search_business_documents":
            return await search_business_documents_simple(query, business_id)
        elif tool_name == "web_search":
            return await web_search_simple(query)
        elif tool_name == "translate_to_sinhala":
            return await translate_to_sinhala_simple(query)
        elif tool_name == "get_business_info":
            return get_business_info_simple(business_context or {})
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    except Exception as e:
        logger.error("Error executing tool", tool_name=tool_name, error=str(e))
        return f"Error executing {tool_name}: {str(e)}"

# Add this function to tools.py for FastAPI compatibility:
def create_tool_registry() -> dict:
    """Create a registry of available tools for FastAPI"""
    return {
        "search_business_documents": {
            "name": "Search Business Documents",
            "description": "Search uploaded business documents and data",
            "requires_business_id": True,
            "async": True
        },
        "web_search": {
            "name": "Web Search",
            "description": "Search the web for current information",
            "requires_business_id": False,
            "async": True
        },
        "translate_to_sinhala": {
            "name": "Sinhala Translation",
            "description": "Translate English text to Sinhala",
            "requires_business_id": False,
            "async": True
        },
        "get_business_info": {
            "name": "Business Information",
            "description": "Get basic business information",
            "requires_business_id": False,
            "async": False
        }
    }


class BusinessDocumentSearchTool(BaseTool):
    """Tool for searching business documents using vector similarity"""
    
    name: str = Field(default="search_business_documents")
    description: str = Field(default="""
    Search through uploaded business documents and data.
    Use this when the user asks about:
    - Product information
    - Service details
    - Company policies
    - Pricing information
    - Business hours or contact details
    
    Input should be the user's query in natural language.
    """)
    business_id: int = Field(description="Business ID for document search")
    
    def __init__(self, business_id: int, **kwargs):
        super().__init__(business_id=business_id, **kwargs)
        self.vector_service = VectorService()
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Search business documents for relevant information"""
        try:
            # Search vector database
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(
                    self.vector_service.search(
                        query=query,
                        business_id=self.business_id,
                        top_k=3
                    )
                )
            finally:
                loop.close()
            
            if not results:
                return "No relevant information found in business documents."
            
            # Format results
            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted_results.append(
                    f"{i}. {result.get('content', '')[:200]}..."
                )
            
            return "Relevant business information:\n" + "\n".join(formatted_results)
            
        except Exception as e:
            logger.error("Error in business document search", error=str(e))
            return "Error accessing business documents. Please try again."

class WebSearchTool(BaseTool):
    """Tool for searching the web when business documents don't have the answer"""
    
    name: str = Field(default="web_search")
    description: str = Field(default="""
    Search the web for current information when business documents don't contain the answer.
    Use this for:
    - Current events or news
    - General information not specific to the business
    - Real-time data like weather, prices, or rates
    - Information that changes frequently
    
    Input should be a clear search query.
    """)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.web_search_service = WebSearchService()
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Search the web for information"""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(
                    self.web_search_service.search(query, num_results=3)
                )
            finally:
                loop.close()
            
            if not results:
                return "No relevant information found on the web."
            
            # Format results
            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted_results.append(
                    f"{i}. {result.get('title', 'Unknown')}: {result.get('snippet', '')[:150]}..."
                )
            
            return "Web search results:\n" + "\n".join(formatted_results)
            
        except Exception as e:
            logger.error("Error in web search", error=str(e))
            return "Error searching the web. Please try again later."

class SinhalaTranslationTool(BaseTool):
    """Tool for translating text to Sinhala"""
    
    name: str = Field(default="translate_to_sinhala")
    description: str = Field(default="""
    Translate English text to Sinhala.
    Use this when:
    - The user's message was in Sinhala but the response is in English
    - You need to provide a Sinhala response
    - The business prefers Sinhala communication
    
    Input should be English text to translate.
    """)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sinhala_nlp = SinhalaNLP()
    
    def _run(
        self,
        text: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Translate text to Sinhala"""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                translated = loop.run_until_complete(
                    self.sinhala_nlp.translate_to_sinhala(text)
                )
            finally:
                loop.close()
            return translated
            
        except Exception as e:
            logger.error("Error in Sinhala translation", error=str(e))
            return text  # Return original text if translation fails

class BusinessInfoTool(BaseTool):
    """Tool for getting basic business information"""

    name: str = Field(default="get_business_info")
    description: str = Field(default="""
    Get basic information about the business like name, description, contact details.
    Use this when users ask about:
    - Business hours
    - Contact information
    - Location
    - General business description

    No input required.
    """)
    business_context: Dict[str, Any] = Field(description="Business context information")

    def __init__(self, business_context: Dict[str, Any], **kwargs):
        super().__init__(business_context=business_context, **kwargs)

    def _run(
        self,
        query: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Get business information"""
        try:
            info_parts = []

            if self.business_context.get('name'):
                info_parts.append(f"Business Name: {self.business_context['name']}")

            if self.business_context.get('description'):
                info_parts.append(f"Description: {self.business_context['description']}")

            if self.business_context.get('website_url'):
                info_parts.append(f"Website: {self.business_context['website_url']}")

            if self.business_context.get('whatsapp_phone_number'):
                info_parts.append(f"WhatsApp: {self.business_context['whatsapp_phone_number']}")

            if self.business_context.get('business_category'):
                info_parts.append(f"Category: {self.business_context['business_category']}")

            if info_parts:
                return "Business Information:\n" + "\n".join(info_parts)
            else:
                return "Business information is not available."

        except Exception as e:
            logger.error("Error getting business info", error=str(e))
            return "Error retrieving business information."

class GoogleSheetsQueryTool(BaseTool):
    """Tool for querying connected Google Sheets in real-time"""

    name: str = Field(default="query_google_sheets")
    description: str = Field(default="""
    Search and query live Google Sheets data. Use this when users ask about:
    - Product inventory or stock levels
    - Pricing information that updates frequently
    - Customer data or contact lists
    - Real-time data from spreadsheets
    - Any information stored in connected Google Sheets

    This tool fetches fresh data from Google Sheets, so it always returns up-to-date information.
    Input should be the user's query in natural language.
    """)
    business_id: int = Field(description="Business ID for Google Sheets access")

    def __init__(self, business_id: int, **kwargs):
        super().__init__(business_id=business_id, **kwargs)
        self.sheets_service = GoogleSheetsService()

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Query Google Sheets for relevant information"""
        try:
            # Get all active sheet connections for this business
            connections = db_session.query(GoogleSheetConnection).filter(
                GoogleSheetConnection.business_id == self.business_id,
                GoogleSheetConnection.is_active == True
            ).all()

            if not connections:
                return "No Google Sheets are connected to this business. Please connect a Google Sheet first."

            # Query each connected sheet
            all_results = []
            for connection in connections:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        self.sheets_service.query_sheet(
                            business_id=self.business_id,
                            sheet_connection_id=connection.id,
                            query=query,
                            max_results=3
                        )
                    )
                finally:
                    loop.close()

                if result.get('success') and result.get('rows'):
                    all_results.append({
                        'sheet_name': connection.name,
                        'rows': result['rows']
                    })

            if not all_results:
                return "No relevant information found in connected Google Sheets."

            # Format results
            formatted_results = []
            for sheet_result in all_results:
                sheet_name = sheet_result['sheet_name']
                formatted_results.append(f"\nFrom '{sheet_name}':")
                for i, row in enumerate(sheet_result['rows'], 1):
                    row_text = ', '.join(f"{k}: {v}" for k, v in row.items() if v is not None)
                    formatted_results.append(f"{i}. {row_text}")

            return "Google Sheets data (live, up-to-date):\n" + "\n".join(formatted_results)

        except Exception as e:
            logger.error("Error querying Google Sheets", error=str(e))
            return "Error accessing Google Sheets. Please try again."

# Simplified tool functions (alternative approach)
async def search_business_documents_simple(query: str, business_id: int) -> str:
    """Simple function to search business documents"""
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

async def web_search_simple(query: str) -> str:
    """Simple function to search the web"""
    try:
        web_search_service = WebSearchService()
        results = await web_search_service.search(query, num_results=3)
        
        if not results:
            return "No relevant information found on the web."
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_results.append(
                f"{i}. {result.get('title', 'Unknown')}: {result.get('snippet', '')[:150]}..."
            )
        
        return "Web search results:\n" + "\n".join(formatted_results)
        
    except Exception as e:
        logger.error("Error in web search", error=str(e))
        return "Error searching the web. Please try again later."

async def translate_to_sinhala_simple(text: str) -> str:
    """Simple function to translate to Sinhala"""
    try:
        sinhala_nlp = SinhalaNLP()
        translated = await sinhala_nlp.translate_to_sinhala(text)
        return translated
    except Exception as e:
        logger.error("Error in Sinhala translation", error=str(e))
        return text

def get_business_info_simple(business_context: Dict[str, Any]) -> str:
    """Simple function to get business info"""
    try:
        info_parts = []

        if business_context.get('name'):
            info_parts.append(f"Business Name: {business_context['name']}")

        if business_context.get('description'):
            info_parts.append(f"Description: {business_context['description']}")

        if business_context.get('website_url'):
            info_parts.append(f"Website: {business_context['website_url']}")

        if business_context.get('whatsapp_phone_number'):
            info_parts.append(f"WhatsApp: {business_context['whatsapp_phone_number']}")

        if business_context.get('business_category'):
            info_parts.append(f"Category: {business_context['business_category']}")

        if info_parts:
            return "Business Information:\n" + "\n".join(info_parts)
        else:
            return "Business information is not available."

    except Exception as e:
        logger.error("Error getting business info", error=str(e))
        return "Error retrieving business information."

async def query_google_sheets_simple(query: str, business_id: int) -> str:
    """Simple function to query Google Sheets"""
    try:
        sheets_service = GoogleSheetsService()

        # Get all active sheet connections
        connections = db_session.query(GoogleSheetConnection).filter(
            GoogleSheetConnection.business_id == business_id,
            GoogleSheetConnection.is_active == True
        ).all()

        if not connections:
            return "No Google Sheets are connected to this business."

        # Query each sheet
        all_results = []
        for connection in connections:
            result = await sheets_service.query_sheet(
                business_id=business_id,
                sheet_connection_id=connection.id,
                query=query,
                max_results=3
            )

            if result.get('success') and result.get('rows'):
                all_results.append({
                    'sheet_name': connection.name,
                    'rows': result['rows']
                })

        if not all_results:
            return "No relevant information found in connected Google Sheets."

        # Format results
        formatted_results = []
        for sheet_result in all_results:
            sheet_name = sheet_result['sheet_name']
            formatted_results.append(f"\nFrom '{sheet_name}':")
            for i, row in enumerate(sheet_result['rows'], 1):
                row_text = ', '.join(f"{k}: {v}" for k, v in row.items() if v is not None)
                formatted_results.append(f"{i}. {row_text}")

        return "Google Sheets data (live):\n" + "\n".join(formatted_results)

    except Exception as e:
        logger.error("Error querying Google Sheets", error=str(e))
        return "Error accessing Google Sheets. Please try again."

def get_ai_tools(business_id: int, business_context: Dict[str, Any]) -> List[BaseTool]:
    """Get list of available AI tools for a business"""

    try:
        tools = [
            BusinessDocumentSearchTool(business_id=business_id),
            GoogleSheetsQueryTool(business_id=business_id),
            WebSearchTool(),
            SinhalaTranslationTool(),
            BusinessInfoTool(business_context=business_context)
        ]
        return tools
    except Exception as e:
        logger.error("Error creating AI tools", error=str(e))
        # Return empty list if tool creation fails
        return []

def get_tool_descriptions() -> Dict[str, str]:
    """Get descriptions of all available tools"""

    return {
        "search_business_documents": "Search uploaded business documents and data",
        "query_google_sheets": "Query live Google Sheets data (always up-to-date)",
        "web_search": "Search the web for current information",
        "translate_to_sinhala": "Translate English text to Sinhala",
        "get_business_info": "Get basic business information"
    }

# Export simple functions for direct use
__all__ = [
    'get_ai_tools',
    'get_tool_descriptions',
    'search_business_documents_simple',
    'query_google_sheets_simple',
    'web_search_simple',
    'translate_to_sinhala_simple',
    'get_business_info_simple'
]