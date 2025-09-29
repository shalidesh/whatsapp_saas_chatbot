"""Application constants and enums"""

# Message types
MESSAGE_TYPES = {
    'TEXT': 'text',
    'IMAGE': 'image',
    'DOCUMENT': 'document',
    'AUDIO': 'audio',
    'VIDEO': 'video',
    'LOCATION': 'location',
    'CONTACT': 'contact'
}

# Language codes
SUPPORTED_LANGUAGES = {
    'SINHALA': 'si',
    'ENGLISH': 'en',
    'TAMIL': 'ta'
}

# Vector database types
VECTOR_DB_TYPES = {
    'FAISS': 'faiss',
    'CHROMADB': 'chromadb'
}

# File size limits (in bytes)
MAX_FILE_SIZE = {
    'PDF': 10 * 1024 * 1024,  # 10MB
    'IMAGE': 5 * 1024 * 1024,  # 5MB
    'DOCUMENT': 20 * 1024 * 1024,  # 20MB
}

# Processing timeouts (in seconds)
PROCESSING_TIMEOUTS = {
    'AI_RESPONSE': 30,
    'DOCUMENT_PROCESSING': 300,
    'WEB_SEARCH': 10
}

# Rate limits
RATE_LIMITS = {
    'MESSAGES_PER_MINUTE': 60,
    'API_CALLS_PER_HOUR': 1000,
    'DOCUMENT_UPLOADS_PER_DAY': 100
}

# Status codes
HTTP_STATUS = {
    'OK': 200,
    'CREATED': 201,
    'BAD_REQUEST': 400,
    'UNAUTHORIZED': 401,
    'FORBIDDEN': 403,
    'NOT_FOUND': 404,
    'INTERNAL_ERROR': 500
}