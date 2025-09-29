import httpx
from typing import List, Dict, Any
import structlog


from ..config.settings import config

logger = structlog.get_logger(__name__)

class WebSearchService:
    def __init__(self):
        self.serp_api_key = config.SERP_API_KEY
        self.search_url = "https://serpapi.com/search"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Search web using SerpAPI"""
        try:
            params = {
                "q": query,
                "api_key": self.serp_api_key,
                "engine": "google",
                "num": num_results,
                "hl": "en",
                "gl": "lk"  # Sri Lanka location
            }
            
            # Make async request
            # loop = asyncio.get_event_loop()

            # response = await loop.run_in_executor(
            #     None, 
            #     lambda: requests.get(self.search_url, params=params)
            # )

            response = await self.client.get(self.search_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                results = self._parse_search_results(data)
                logger.info("Web search completed", 
                           query=query, results_count=len(results))
                return results
            else:
                logger.error("Web search failed", 
                           status_code=response.status_code)
                return []
                
        except Exception as e:
            logger.error("Error in web search", error=str(e), query=query)
            return []
    
    def _parse_search_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse SerpAPI response"""
        results = []
        
        # Parse organic results
        organic_results = data.get('organic_results', [])
        for result in organic_results:
            results.append({
                'title': result.get('title', ''),
                'link': result.get('link', ''),
                'snippet': result.get('snippet', ''),
                'source': 'organic'
            })
        
        # Parse answer box if available
        answer_box = data.get('answer_box')
        if answer_box:
            results.insert(0, {
                'title': answer_box.get('title', 'Answer'),
                'link': answer_box.get('link', ''),
                'snippet': answer_box.get('answer', answer_box.get('snippet', '')),
                'source': 'answer_box'
            })
        
        # Parse knowledge graph if available
        knowledge_graph = data.get('knowledge_graph')
        if knowledge_graph:
            results.insert(0, {
                'title': knowledge_graph.get('title', 'Knowledge'),
                'link': knowledge_graph.get('website', ''),
                'snippet': knowledge_graph.get('description', ''),
                'source': 'knowledge_graph'
            })
        
        return results[:5]  # Return top 5 results