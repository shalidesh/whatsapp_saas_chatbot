import re
import pandas as pd
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import structlog
from cachetools import TTLCache
import json

from ..models.google_sheet import GoogleSheetConnection
from ..config.database import db_session
from ..config.settings import config

logger = structlog.get_logger(__name__)


class GoogleSheetsService:
    """Service for fetching and querying Google Sheets data in real-time"""

    def __init__(self):
        # In-memory cache: key = sheet_id, value = (data, timestamp)
        # TTL is handled per-sheet based on their cache_ttl_minutes setting
        self.cache: Dict[str, Dict[str, Any]] = {}

    def extract_sheet_id(self, url: str) -> Optional[str]:
        """Extract Google Sheet ID from various URL formats"""
        try:
            # Pattern for: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit...
            pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
            match = re.search(pattern, url)
            if match:
                return match.group(1)

            # If URL is just the ID
            if re.match(r'^[a-zA-Z0-9-_]+$', url):
                return url

            return None
        except Exception as e:
            logger.error("Error extracting sheet ID", error=str(e))
            return None

    async def fetch_sheet_data(
        self,
        sheet_id: str,
        range_name: str = "Sheet1",
        use_cache: bool = True,
        cache_ttl_minutes: int = 10
    ) -> Optional[pd.DataFrame]:
        """
        Fetch data from Google Sheets using public CSV export.
        Note: This only works for publicly accessible sheets.
        For private sheets, you'll need to implement OAuth2 flow.
        """
        try:
            # Check cache first
            if use_cache and sheet_id in self.cache:
                cached_data = self.cache[sheet_id]
                cache_time = cached_data.get('timestamp')
                ttl = timedelta(minutes=cached_data.get('ttl_minutes', cache_ttl_minutes))

                if cache_time and datetime.utcnow() - cache_time < ttl:
                    logger.info(f"Using cached data for sheet {sheet_id}")
                    return cached_data.get('data')

            # Construct CSV export URL
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"

            logger.info(f"Fetching Google Sheet data from {csv_url}")

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(csv_url)
                response.raise_for_status()

            # Parse CSV into DataFrame
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))

            # Cache the data
            self.cache[sheet_id] = {
                'data': df,
                'timestamp': datetime.utcnow(),
                'ttl_minutes': cache_ttl_minutes
            }

            logger.info(
                f"Successfully fetched sheet data",
                sheet_id=sheet_id,
                rows=len(df),
                columns=len(df.columns)
            )

            return df

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404 or e.response.status_code == 403:
                logger.error(
                    "Sheet not accessible - ensure it's publicly shared",
                    sheet_id=sheet_id,
                    status_code=e.response.status_code
                )
                raise ValueError(
                    "Google Sheet is not publicly accessible. "
                    "Please make sure the sheet is shared with 'Anyone with the link can view'"
                )
            else:
                logger.error("HTTP error fetching sheet", error=str(e))
                raise
        except Exception as e:
            logger.error("Error fetching sheet data", sheet_id=sheet_id, error=str(e))
            raise

    async def query_sheet(
        self,
        business_id: int,
        sheet_connection_id: int,
        query: str,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Query Google Sheet data using natural language.
        Returns relevant rows based on the query.
        """
        try:
            # Get sheet connection
            connection = db_session.query(GoogleSheetConnection).filter(
                GoogleSheetConnection.id == sheet_connection_id,
                GoogleSheetConnection.business_id == business_id,
                GoogleSheetConnection.is_active == True
            ).first()

            if not connection:
                raise ValueError("Sheet connection not found")

            # Fetch sheet data
            df = await self.fetch_sheet_data(
                sheet_id=connection.sheet_id,
                use_cache=True,
                cache_ttl_minutes=connection.cache_ttl_minutes
            )

            if df is None or df.empty:
                return {
                    'success': False,
                    'message': 'No data found in sheet',
                    'rows': []
                }

            # Update connection metadata
            connection.last_synced_at = datetime.utcnow()
            connection.row_count = len(df)
            connection.column_count = len(df.columns)
            db_session.commit()

            # Perform query - simple text matching across all columns
            # For more advanced queries, you could integrate LLM here
            matching_rows = self._search_dataframe(df, query, max_results)

            return {
                'success': True,
                'message': f'Found {len(matching_rows)} matching rows',
                'rows': matching_rows,
                'total_rows': len(df),
                'columns': list(df.columns),
                'last_synced': connection.last_synced_at.isoformat()
            }

        except Exception as e:
            logger.error("Error querying sheet", error=str(e))
            # Update error in connection
            if 'connection' in locals():
                connection.last_sync_error = str(e)
                db_session.commit()

            return {
                'success': False,
                'message': f'Error querying sheet: {str(e)}',
                'rows': []
            }

    def _search_dataframe(
        self,
        df: pd.DataFrame,
        query: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search DataFrame for rows matching the query.
        Uses keyword-based matching - searches for any of the keywords in the query.
        Supports both exact phrase matching and individual keyword matching.
        """
        try:
            query_lower = query.lower().strip()
            matching_indices = []

            # Split query into keywords (handle multiple words)
            keywords = query_lower.split()

            # Search across all columns
            for idx, row in df.iterrows():
                row_text = ' '.join(str(val).lower() for val in row.values if pd.notna(val))

                # Check if the exact query phrase exists
                if query_lower in row_text:
                    matching_indices.append(idx)
                # Otherwise check if any keyword matches
                elif any(keyword in row_text for keyword in keywords):
                    matching_indices.append(idx)

                if len(matching_indices) >= max_results:
                    break

            # Convert matching rows to dictionaries
            matching_rows = []
            for idx in matching_indices:
                row_dict = df.iloc[idx].to_dict()
                # Convert any NaN to None for JSON serialization
                row_dict = {k: (None if pd.isna(v) else v) for k, v in row_dict.items()}
                matching_rows.append(row_dict)

            return matching_rows

        except Exception as e:
            logger.error("Error searching dataframe", error=str(e))
            return []

    async def test_connection(self, sheet_url: str) -> Dict[str, Any]:
        """Test if a Google Sheet is accessible"""
        try:
            sheet_id = self.extract_sheet_id(sheet_url)
            if not sheet_id:
                return {
                    'success': False,
                    'message': 'Invalid Google Sheets URL'
                }

            df = await self.fetch_sheet_data(sheet_id, use_cache=False)

            if df is not None:
                return {
                    'success': True,
                    'message': 'Connection successful',
                    'sheet_id': sheet_id,
                    'row_count': len(df),
                    'column_count': len(df.columns),
                    'columns': list(df.columns),
                    'preview': df.head(3).to_dict(orient='records')
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to fetch sheet data'
                }

        except Exception as e:
            logger.error("Error testing connection", error=str(e))
            return {
                'success': False,
                'message': str(e)
            }

    def clear_cache(self, sheet_id: Optional[str] = None):
        """Clear cache for a specific sheet or all sheets"""
        if sheet_id:
            if sheet_id in self.cache:
                del self.cache[sheet_id]
                logger.info(f"Cleared cache for sheet {sheet_id}")
        else:
            self.cache.clear()
            logger.info("Cleared all sheet caches")

    async def get_sheet_preview(
        self,
        business_id: int,
        sheet_connection_id: int,
        num_rows: int = 5
    ) -> Dict[str, Any]:
        """Get a preview of sheet data"""
        try:
            connection = db_session.query(GoogleSheetConnection).filter(
                GoogleSheetConnection.id == sheet_connection_id,
                GoogleSheetConnection.business_id == business_id,
                GoogleSheetConnection.is_active == True
            ).first()

            if not connection:
                raise ValueError("Sheet connection not found")

            df = await self.fetch_sheet_data(
                sheet_id=connection.sheet_id,
                use_cache=True,
                cache_ttl_minutes=connection.cache_ttl_minutes
            )

            if df is None or df.empty:
                return {
                    'success': False,
                    'message': 'No data found in sheet'
                }

            preview_data = df.head(num_rows).to_dict(orient='records')
            # Clean NaN values
            preview_data = [
                {k: (None if pd.isna(v) else v) for k, v in row.items()}
                for row in preview_data
            ]

            return {
                'success': True,
                'columns': list(df.columns),
                'preview': preview_data,
                'total_rows': len(df),
                'total_columns': len(df.columns)
            }

        except Exception as e:
            logger.error("Error getting sheet preview", error=str(e))
            return {
                'success': False,
                'message': str(e)
            }
