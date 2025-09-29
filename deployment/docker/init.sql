-- Create database
CREATE DATABASE whatsapp_saas;

-- Connect to database
\c whatsapp_saas;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);

-- Businesses table
CREATE TABLE businesses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    website_url VARCHAR(500),
    whatsapp_phone_number VARCHAR(20),
    business_category VARCHAR(100),
    ai_persona TEXT DEFAULT 'You are a helpful business assistant.',
    supported_languages JSONB DEFAULT '["si", "en"]',
    default_language VARCHAR(10) DEFAULT 'si',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_businesses_user_id ON businesses(user_id);
CREATE INDEX idx_businesses_phone ON businesses(whatsapp_phone_number);
CREATE INDEX idx_businesses_active ON businesses(is_active);

-- Message direction and status enums
CREATE TYPE message_direction AS ENUM ('inbound', 'outbound');
CREATE TYPE message_status AS ENUM ('received', 'processing', 'responded', 'failed');

-- Messages table (update metadata column name)
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    whatsapp_message_id VARCHAR(255) UNIQUE,
    direction message_direction NOT NULL,
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text',
    language_detected VARCHAR(10),
    sender_phone VARCHAR(20),
    recipient_phone VARCHAR(20),
    sender_name VARCHAR(255),
    status message_status DEFAULT 'received',
    ai_response TEXT,
    processing_time_ms INTEGER,
    confidence_score INTEGER,
    message_metadata JSONB DEFAULT '{}',  -- Renamed from metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX idx_messages_business_id ON messages(business_id);
CREATE INDEX idx_messages_whatsapp_id ON messages(whatsapp_message_id);
CREATE INDEX idx_messages_direction ON messages(direction);
CREATE INDEX idx_messages_status ON messages(status);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_messages_sender_phone ON messages(sender_phone);


-- Documents table (update metadata column name)
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    document_type document_type NOT NULL,
    file_path VARCHAR(500),
    url VARCHAR(500),
    file_size INTEGER,
    status document_status DEFAULT 'uploaded',
    processing_error TEXT,
    extracted_text TEXT,
    chunk_count INTEGER DEFAULT 0,
    embedding_model VARCHAR(100) DEFAULT 'text-embedding-ada-002',
    document_metadata JSONB DEFAULT '{}',  -- Renamed from metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Document type and status enums
CREATE TYPE document_type AS ENUM ('pdf', 'spreadsheet', 'website');
CREATE TYPE document_status AS ENUM ('uploaded', 'processing', 'processed', 'failed');


CREATE INDEX idx_documents_business_id ON documents(business_id);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_active ON documents(is_active);

-- Analytics views
CREATE OR REPLACE VIEW daily_message_stats AS
SELECT
    business_id,
    DATE(created_at) as date,
    COUNT(*) as total_messages,
    COUNT(CASE WHEN direction = 'inbound' THEN 1 END) as inbound_messages,
    COUNT(CASE WHEN direction = 'outbound' THEN 1 END) as outbound_messages,
    COUNT(CASE WHEN direction = 'inbound' AND status = 'responded' THEN 1 END) as responded_messages,
    AVG(CASE WHEN direction = 'inbound' AND status = 'responded' THEN processing_time_ms END) as avg_response_time_ms
    FROM messages
    GROUP BY business_id, DATE(created_at);


-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $
    BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
    END;
    $ language 'plpgsql';
    -- Triggers for updated_at
    CREATE TRIGGER update_businesses_updated_at BEFORE UPDATE ON businesses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
-- Create initial admin user (password: admin123)
INSERT INTO users (email, password_hash, first_name, last_name) VALUES
('admin@whatsappsaas.com', 'pbkdf2:sha256:600000$1234567890$abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890', 'Admin', 'User');