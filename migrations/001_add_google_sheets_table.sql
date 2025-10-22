-- Migration: Add Google Sheets Connection Table
-- Created: 2025-10-21
-- Description: Add support for live Google Sheets integration

CREATE TABLE IF NOT EXISTS google_sheet_connections (
    id SERIAL PRIMARY KEY,
    business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,

    -- Sheet Info
    name VARCHAR(255) NOT NULL,
    sheet_url VARCHAR(500) NOT NULL,
    sheet_id VARCHAR(255) NOT NULL,

    -- Configuration
    cache_ttl_minutes INTEGER DEFAULT 10,
    query_columns JSON DEFAULT '[]'::json,

    -- Metadata
    last_synced_at TIMESTAMP,
    last_sync_error TEXT,
    row_count INTEGER DEFAULT 0,
    column_count INTEGER DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    CONSTRAINT unique_business_sheet UNIQUE (business_id, sheet_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_google_sheets_business_id ON google_sheet_connections(business_id);
CREATE INDEX IF NOT EXISTS idx_google_sheets_is_active ON google_sheet_connections(is_active);
CREATE INDEX IF NOT EXISTS idx_google_sheets_sheet_id ON google_sheet_connections(sheet_id);

-- Add comment
COMMENT ON TABLE google_sheet_connections IS 'Stores connections to Google Sheets for live data integration';
