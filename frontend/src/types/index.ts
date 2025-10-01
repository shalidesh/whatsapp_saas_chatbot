export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Business {
  id: number;
  user_id: number;
  name: string;
  description: string;
  website_url?: string;
  whatsapp_phone_number: string;
  business_category?: string;
  ai_persona: string;
  supported_languages: string[];
  default_language: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  business_id: number;
  whatsapp_message_id: string;
  direction: 'inbound' | 'outbound';
  content: string;
  content_type: string;
  sender_phone: string;
  recipient_phone: string;
  sender_name?: string;
  status: 'received' | 'processing' | 'responded' | 'failed';
  language_detected?: string;
  processing_time_ms?: number;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: number;
  business_id: number;
  file_path?: string;
  url?: string;
  document_type: string;
  status: 'pending' | 'processing' | 'processed' | 'failed';
  title?: string;
  chunk_count?: number;
  error_message?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DashboardStatistics {
  total_messages: number;
  inbound_messages: number;
  responded_messages: number;
  response_rate: number;
  avg_response_time_ms: number;
  total_documents: number;
  processed_documents: number;
}

export interface AnalyticsData {
  daily_stats: {
    date: string;
    total: number;
    inbound: number;
    outbound: number;
  }[];
  language_distribution: {
    language: string;
    count: number;
  }[];
  response_time_distribution: {
    bucket: string;
    count: number;
  }[];
  common_queries: {
    query: string;
    frequency: number;
  }[];
}

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  pages: number;
}

export interface AuthResponse {
  message: string;
  token: string;
  user: User;
  business?: Business;
  businesses?: Business[];
}
