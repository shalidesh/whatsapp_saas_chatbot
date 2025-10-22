# Google Sheets Integration - Quick Start Guide

## 5-Minute Setup

### Step 1: Prepare Your Google Sheet

1. Open your Google Sheet with data (e.g., product inventory)
2. Click **Share** button (top-right corner)
3. Click **"Change to anyone with the link"**
4. Set permission to **"Viewer"**
5. Click **"Copy link"**

Your sheet URL should look like:
```
https://docs.google.com/spreadsheets/d/1ABC123XYZ.../edit
```

### Step 2: Install Dependencies

```bash
pip install httpx cachetools
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

### Step 3: Start Your Application

```bash
python run.py
```

The database table `google_sheet_connections` will be created automatically.

### Step 4: Connect Your Sheet via API

```bash
curl -X POST "http://localhost:8000/api/dashboard/google-sheets/connect" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": 1,
    "name": "Product Inventory",
    "sheet_url": "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit",
    "cache_ttl_minutes": 10
  }'
```

### Step 5: Test via WhatsApp

Send a message to your WhatsApp business number:

```
"What's the price of Dell Laptop?"
```

The AI will automatically:
1. Recognize this as a product query
2. Check connected Google Sheets
3. Search for "Dell Laptop"
4. Return current price and stock info

## Example Sheet Structure

Create a Google Sheet with this structure:

| Product      | Price | Stock | Category    |
|-------------|-------|-------|-------------|
| Dell Laptop | $999  | 15    | Electronics |
| iPhone 15   | $899  | 8     | Electronics |
| Office Chair| $199  | 25    | Furniture   |

## How It Works

```
User Query → AI Agent → Google Sheets Tool → Live Sheet Data → AI Response
```

**Key Points**:
- ✅ Data is fetched in real-time
- ✅ No vector database storage
- ✅ Always up-to-date results
- ✅ 10-minute cache by default
- ✅ Works with multiple sheets

## API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/google-sheets/test-connection` | POST | Test sheet access |
| `/google-sheets/connect` | POST | Connect a sheet |
| `/google-sheets` | GET | List connected sheets |
| `/google-sheets/query` | POST | Query sheet data |
| `/google-sheets/{id}/preview` | GET | Preview sheet |
| `/google-sheets/{id}/refresh-cache` | POST | Refresh cache |
| `/google-sheets/{id}` | DELETE | Disconnect sheet |

## Configuration Options

```json
{
  "cache_ttl_minutes": 10  // How long to cache data
}
```

**Recommended TTL**:
- **Real-time inventory**: 1-5 minutes
- **Pricing (changes hourly)**: 10-30 minutes
- **Static data (rarely changes)**: 60-1440 minutes

## Troubleshooting

### Error: "Sheet not accessible"
**Fix**: Make sure sheet is shared as "Anyone with the link can view"

### Error: "No data found"
**Fix**: Ensure sheet has data in the first tab (Sheet1)

### Slow performance
**Fix**: Increase `cache_ttl_minutes` or reduce sheet size

## Next Steps

- Read full documentation: `docs/GOOGLE_SHEETS_INTEGRATION.md`
- Connect multiple sheets for different data types
- Adjust cache TTL based on your needs
- Monitor query performance

## Support

For detailed information, see the complete documentation:
- **Full Guide**: `docs/GOOGLE_SHEETS_INTEGRATION.md`
- **Migration Script**: `migrations/001_add_google_sheets_table.sql`
- **Service Code**: `app/services/google_sheets_service.py`
- **AI Tool**: `app/api/ai/tools.py` (GoogleSheetsQueryTool)
