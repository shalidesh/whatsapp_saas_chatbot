# Google Sheets Live Integration

## Overview

This feature enables real-time integration with Google Sheets, allowing your AI agent to query live, always-up-to-date spreadsheet data **without** storing it in a vector database. This is perfect for:

- Product inventory that changes frequently
- Pricing information
- Customer contact lists
- Order tracking
- Any data that needs to be always current

## Key Features

- **Real-Time Data**: Fetches fresh data from Google Sheets on every query
- **Smart Caching**: Configurable cache (default 10 minutes) to balance freshness and performance
- **No Vector Database**: Data is queried directly, not embedded, ensuring always-up-to-date results
- **Natural Language Queries**: Users can ask questions in plain language
- **Multiple Sheets**: Connect multiple Google Sheets per business
- **AI-Powered Search**: Intelligent matching across all columns

## Architecture

```
User WhatsApp Query
    ↓
AI Agent (detects need for sheet data)
    ↓
GoogleSheetsQueryTool
    ↓
GoogleSheetsService
    ↓
Check Cache (TTL-based)
    ↓ (if expired)
Google Sheets CSV Export API
    ↓
Parse as DataFrame
    ↓
Search/Filter Data
    ↓
Return Fresh Results
```

## Setup Instructions

### 1. Make Your Google Sheet Publicly Accessible

**IMPORTANT**: Currently, this integration uses Google Sheets CSV export, which requires the sheet to be publicly accessible.

1. Open your Google Sheet
2. Click "Share" (top right)
3. Click "Change to anyone with the link"
4. Set permission to "Viewer"
5. Click "Copy link"

**Note**: For private sheets with OAuth2 authentication, you'll need to implement the full Google Sheets API integration (see Future Enhancements below).

### 2. Install Dependencies

The following dependencies have been added to `requirements.txt`:

```bash
httpx          # Async HTTP client for fetching sheets
cachetools     # Caching library for performance
pandas         # DataFrame operations (already installed)
```

Install them:

```bash
pip install -r requirements.txt
```

### 3. Database Migration

The `google_sheet_connections` table will be automatically created when the application starts (via SQLAlchemy's `Base.metadata.create_all()`).

Alternatively, you can run the SQL migration manually:

```bash
psql -d your_database -f migrations/001_add_google_sheets_table.sql
```

### 4. Start the Application

```bash
python run.py
```

The GoogleSheetsQueryTool is automatically registered with the AI agent.

## API Endpoints

### 1. Test Connection

Test if a Google Sheet is accessible before connecting.

**Endpoint**: `POST /api/dashboard/google-sheets/test-connection`

**Request**:
```bash
curl -X POST "http://localhost:8000/api/dashboard/google-sheets/test-connection" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "sheet_url=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
```

**Response**:
```json
{
  "success": true,
  "message": "Connection successful",
  "sheet_id": "1ABC...",
  "row_count": 150,
  "column_count": 5,
  "columns": ["Product", "Price", "Stock", "Category"],
  "preview": [...]
}
```

### 2. Connect Google Sheet

Connect a Google Sheet to your business.

**Endpoint**: `POST /api/dashboard/google-sheets/connect`

**Request**:
```json
{
  "business_id": 1,
  "name": "Product Inventory",
  "sheet_url": "https://docs.google.com/spreadsheets/d/1ABC.../edit",
  "cache_ttl_minutes": 10
}
```

**Response**:
```json
{
  "message": "Google Sheet connected successfully",
  "connection": {
    "id": 1,
    "business_id": 1,
    "name": "Product Inventory",
    "sheet_id": "1ABC...",
    "row_count": 150,
    "column_count": 5,
    "is_active": true,
    "created_at": "2025-10-21T10:00:00"
  }
}
```

### 3. List Connected Sheets

Get all Google Sheets connected to a business.

**Endpoint**: `GET /api/dashboard/google-sheets?business_id=1`

**Response**:
```json
{
  "connections": [
    {
      "id": 1,
      "name": "Product Inventory",
      "sheet_url": "https://...",
      "row_count": 150,
      "last_synced_at": "2025-10-21T10:30:00",
      "is_active": true
    }
  ]
}
```

### 4. Query Sheet

Query a connected Google Sheet (mainly for testing; the AI agent uses this automatically).

**Endpoint**: `POST /api/dashboard/google-sheets/query`

**Request**:
```json
{
  "business_id": 1,
  "sheet_connection_id": 1,
  "query": "laptop price",
  "max_results": 5
}
```

**Response**:
```json
{
  "success": true,
  "message": "Found 3 matching rows",
  "rows": [
    {
      "Product": "Dell Laptop",
      "Price": "$999",
      "Stock": "15",
      "Category": "Electronics"
    },
    ...
  ],
  "total_rows": 150,
  "columns": ["Product", "Price", "Stock", "Category"]
}
```

### 5. Preview Sheet Data

Get a preview of sheet data.

**Endpoint**: `GET /api/dashboard/google-sheets/{connection_id}/preview?business_id=1&num_rows=5`

### 6. Refresh Cache

Force refresh the cache for a sheet.

**Endpoint**: `POST /api/dashboard/google-sheets/{connection_id}/refresh-cache?business_id=1`

### 7. Disconnect Sheet

Disconnect a Google Sheet.

**Endpoint**: `DELETE /api/dashboard/google-sheets/{connection_id}?business_id=1`

## Usage Example

### Via WhatsApp Chat

Once a Google Sheet is connected, users can query it naturally via WhatsApp:

**User**: "What's the price of Dell Laptop?"

**AI Agent**:
1. Detects the query is about products/pricing
2. Calls `GoogleSheetsQueryTool`
3. Fetches fresh data from Google Sheets
4. Searches for "Dell Laptop" across all columns
5. Returns: "The Dell Laptop is priced at $999 with 15 units in stock."

**User**: "Do you have iPhone in stock?"

**AI Agent**: Queries the sheet and responds with current stock levels.

## Configuration Options

### Cache TTL (Time-To-Live)

Configure how long data is cached (in minutes):

- **Default**: 10 minutes
- **Min**: 1 minute (near real-time, more API calls)
- **Max**: 1440 minutes (24 hours, less API calls)

Set when connecting a sheet:
```json
{
  "cache_ttl_minutes": 5  // Refresh every 5 minutes
}
```

### Query Columns (Future Feature)

Specify which columns to prioritize for queries:
```json
{
  "query_columns": ["Product", "Description"]
}
```

## Performance Considerations

### API Quotas

Google Sheets CSV export doesn't have strict quotas, but:
- Use appropriate cache TTL
- Don't set cache TTL too low (<1 minute)
- Monitor usage if you have high traffic

### Cache Strategy

The caching strategy:
1. First query: Fetch from Google Sheets, cache result
2. Subsequent queries: Use cached data until TTL expires
3. After TTL: Fetch fresh data, update cache

### Response Times

- **With cache hit**: ~50-200ms
- **With cache miss**: ~1-3 seconds (includes Google Sheets fetch)

## Differences vs Vector Database Approach

| Aspect | Google Sheets (This) | Vector Database |
|--------|---------------------|-----------------|
| **Data Freshness** | Always current | Static snapshot |
| **Update Method** | Automatic | Manual re-upload |
| **Query Speed** | Moderate (cached) | Very fast |
| **Semantic Search** | Limited | Excellent |
| **Best For** | Frequently changing data | Static documents |
| **Storage** | None (live fetch) | Embedded vectors |

## Troubleshooting

### "Sheet not accessible" Error

**Cause**: Sheet is not publicly shared

**Solution**:
1. Open Google Sheet
2. Click Share → "Anyone with the link can view"
3. Try connecting again

### "No data found in sheet"

**Causes**:
- Sheet is empty
- Sheet has non-standard format
- Wrong sheet ID

**Solution**:
- Ensure sheet has data in first tab (Sheet1)
- Check sheet URL is correct

### Slow Query Performance

**Causes**:
- Cache expired
- Large spreadsheet
- Many connected sheets

**Solutions**:
- Increase cache TTL
- Limit spreadsheet size (<1000 rows recommended)
- Use specific queries instead of broad searches

## Future Enhancements

### 1. OAuth2 Authentication (Private Sheets)

Implement full Google Sheets API v4 with OAuth2:

```python
# Future implementation
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

service = build('sheets', 'v4', credentials=creds)
```

**Benefits**:
- Access private sheets
- Better API quotas
- More features (write access, formatting, etc.)

### 2. LLM-Enhanced Querying

Use OpenAI to translate natural language to structured queries:

```python
# Future: Convert "cheap laptops" to filter
query = "cheap laptops"
# → filter: Price < 500 AND Category = "Laptops"
```

### 3. Multiple Sheet Tabs

Support querying specific tabs in a sheet:

```python
fetch_sheet_data(sheet_id, range_name="Inventory")
```

### 4. Write Operations

Allow AI to update sheets:

```python
# Future: Update stock levels
update_sheet_cell(sheet_id, "B2", new_value="10")
```

### 5. Webhook Integration

Use Google Apps Script webhooks to invalidate cache on sheet changes:

```javascript
// Google Apps Script
function onEdit(e) {
  UrlFetchApp.fetch('https://your-api.com/webhook/sheet-updated', {
    method: 'POST',
    payload: JSON.stringify({ sheet_id: 'ABC...' })
  });
}
```

## Security Considerations

### Public Sheets

- ⚠️ Don't store sensitive data in public sheets
- ✅ Use for public information only (products, pricing, FAQs)

### Private Sheets (Future)

When implementing OAuth2:
- Store refresh tokens encrypted
- Use least-privilege access (read-only)
- Implement token rotation

### Data Validation

- Validate sheet structure before querying
- Sanitize user queries to prevent injection
- Rate limit API calls

## Testing

### Unit Tests

```python
# test_google_sheets_service.py
import pytest
from app.services.google_sheets_service import GoogleSheetsService

@pytest.mark.asyncio
async def test_fetch_sheet_data():
    service = GoogleSheetsService()
    df = await service.fetch_sheet_data(
        sheet_id="TEST_SHEET_ID",
        use_cache=False
    )
    assert df is not None
    assert len(df) > 0
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_query_sheet():
    result = await google_sheets_service.query_sheet(
        business_id=1,
        sheet_connection_id=1,
        query="laptop",
        max_results=5
    )
    assert result['success'] == True
    assert len(result['rows']) > 0
```

## Example Spreadsheet Structure

For best results, structure your Google Sheet like this:

| Product | Price | Stock | Category | Description |
|---------|-------|-------|----------|-------------|
| Dell Laptop | $999 | 15 | Electronics | 15-inch, 16GB RAM |
| iPhone 15 | $899 | 8 | Electronics | Latest model |
| Office Chair | $199 | 25 | Furniture | Ergonomic design |

**Tips**:
- First row should contain column headers
- Keep data clean and consistent
- Avoid merged cells
- Use clear column names
- Keep under 1000 rows for best performance

## Support

For issues or questions:
1. Check this documentation
2. Review error logs in application
3. Test connection with `/test-connection` endpoint
4. Check Google Sheet permissions

---

**Version**: 1.0
**Last Updated**: 2025-10-21
**Author**: WhatsApp AI SaaS Team
