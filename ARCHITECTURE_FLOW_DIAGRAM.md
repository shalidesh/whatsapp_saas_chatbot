# WhatsApp AI SaaS - Complete Architecture Flow Diagram

## 1. Complete System Architecture

```mermaid
graph TB
    subgraph "Frontend Layer - Next.js (Port 3000)"
        A[User Browser] --> B[Next.js App Router]
        B --> C[Landing Page]
        B --> D[Auth Pages]
        B --> E[Dashboard Layout]

        E --> E1[Overview Page]
        E --> E2[Messages Page]
        E --> E3[Documents Page]
        E --> E4[AI Agent Page]
        E --> E5[Settings Page]

        F[Zustand Store] --> F1[Auth State]
        F --> F2[Business State]
        F --> F3[User State]

        G[API Client Axios] --> G1[Request Interceptor]
        G1 --> G2[Add JWT Token]
        G --> G3[Response Interceptor]
        G3 --> G4[Error Handling]

        E1 & E2 & E3 & E4 & E5 --> G
    end

    subgraph "API Gateway & Middleware Layer"
        H[FastAPI App - Port 5000]
        H --> I1[CORS Middleware]
        I1 --> I2[Logging Middleware]
        I2 --> I3[Metrics Middleware]
        I3 --> I4[Tenant Logging]
        I4 --> I5[JWT Auth Bearer]
        I5 --> I6[Exception Handlers]
    end

    subgraph "Backend Routes Layer"
        J1[Auth Routes /api/auth]
        J2[Dashboard Routes /api/dashboard]
        J3[WhatsApp Routes /api/whatsapp]
        J4[AI Agent Routes /api/ai]

        J1 --> J1A[POST /register]
        J1 --> J1B[POST /login]
        J1 --> J1C[POST /verify-token]

        J2 --> J2A[GET /overview]
        J2 --> J2B[GET /messages]
        J2 --> J2C[GET /analytics]
        J2 --> J2D[GET /documents]
        J2 --> J2E[POST /documents/upload]
        J2 --> J2F[GET /business/settings]
        J2 --> J2G[PUT /business/settings]
        J2 --> J2H[Google Sheets Endpoints]

        J3 --> J3A[GET /webhook - Verify]
        J3 --> J3B[POST /webhook - Receive]
        J3 --> J3C[POST /send-message]
        J3 --> J3D[GET /health]

        J4 --> J4A[POST /test-message]
        J4 --> J4B[GET /agent-status]
        J4 --> J4C[POST /reload-knowledge]
    end

    subgraph "Service Layer"
        K1[WhatsApp Service]
        K2[AI Service]
        K3[Vector Service]
        K4[Document Service]
        K5[Google Sheets Service]
        K6[Web Search Service]
        K7[Sinhala NLP Service]
    end

    subgraph "Database Layer - PostgreSQL"
        L1[(Users Table)]
        L2[(Businesses Table)]
        L3[(Messages Table)]
        L4[(Documents Table)]
        L5[(Google Sheets Table)]

        L1 -->|1:Many| L2
        L2 -->|1:Many| L3
        L2 -->|1:Many| L4
        L2 -->|1:Many| L5
    end

    subgraph "Async Task Queue - Celery"
        M1[RabbitMQ Broker<br/>Port 5672]
        M2[Redis Backend<br/>Port 6379]
        M3[Celery Worker]
        M4[Flower Monitor<br/>Port 5555]

        M1 --> M3
        M3 --> M2
        M1 --> M4
    end

    subgraph "Celery Tasks"
        N1[process_whatsapp_message<br/>High Priority Queue]
        N2[process_document_upload<br/>Low Priority Queue]
    end

    subgraph "Vector Database Layer"
        O1[FAISS Vector Store<br/>./data/faiss]
        O2[ChromaDB Optional<br/>./data/chromadb]
    end

    subgraph "External Services"
        P1[WhatsApp Business API]
        P2[GitHub/OpenAI GPT-4]
        P3[Hugging Face API<br/>Embeddings]
        P4[AWS S3<br/>Document Storage]
        P5[Web Search API]
        P6[LangSmith Tracing]
    end

    subgraph "AI Agent - LangGraph"
        Q1[Analyze Query Node]
        Q2[Search Internal Node]
        Q3[Search Web Node]
        Q4[Generate Response Node]
        Q5[Translate Response Node]

        Q1 --> Q2
        Q2 --> Q3
        Q3 --> Q4
        Q4 --> Q5
    end

    %% Frontend to Backend
    G -->|HTTP/REST| H

    %% Middleware to Routes
    I6 --> J1 & J2 & J3 & J4

    %% Routes to Services
    J1A & J1B & J1C --> K1
    J2A & J2B & J2C & J2D & J2E & J2F & J2G --> K1 & K4
    J2H --> K5
    J3A & J3B & J3C --> K1
    J4A & J4B & J4C --> K2

    %% Services to Database
    K1 & K2 & K4 & K5 --> L1 & L2 & L3 & L4 & L5

    %% Services to Vector DB
    K2 & K3 & K4 --> O1 & O2

    %% Services to Celery
    K1 --> M1
    K4 --> M1

    %% Celery Worker to Tasks
    M3 --> N1 & N2

    %% Tasks to Services
    N1 --> K2
    N2 --> K4

    %% AI Service to Agent
    K2 --> Q1

    %% Services to External APIs
    K1 --> P1
    K2 --> P2 & P6
    K3 & K4 --> P3
    K4 --> P4
    K6 --> P5
    Q3 --> P5

    %% External to Backend
    P1 -->|Webhook| J3B
```

## 2. Detailed Message Flow - Inbound WhatsApp Message

```mermaid
sequenceDiagram
    participant WA as WhatsApp User
    participant WAB as WhatsApp Business API
    participant WH as FastAPI Webhook<br/>/api/whatsapp/webhook
    participant MW as Middleware Stack
    participant WS as WhatsApp Service
    participant DB as PostgreSQL
    participant RMQ as RabbitMQ
    participant CW as Celery Worker
    participant AI as AI Service
    participant LG as LangGraph Agent
    participant VS as Vector Service
    participant FAISS as FAISS DB
    participant GPT as GitHub/OpenAI
    participant HF as Hugging Face

    WA->>WAB: Send Message
    WAB->>WH: POST /webhook<br/>{message payload}
    WH->>MW: Request
    MW->>MW: CORS Check
    MW->>MW: Logging
    MW->>MW: Metrics
    WH->>WS: parse_webhook_message()
    WS->>DB: INSERT Message<br/>status=RECEIVED
    DB-->>WS: Message ID
    WS->>RMQ: process_whatsapp_message.delay(message_id)
    WS-->>WH: Task Queued
    WH-->>WAB: 200 OK

    Note over RMQ,CW: Async Processing Starts

    RMQ->>CW: Task Dispatch<br/>High Priority Queue
    CW->>DB: UPDATE status=PROCESSING
    CW->>AI: process_message(message_id)
    AI->>DB: FETCH Business Context
    AI->>LG: Initialize LangGraph Workflow

    LG->>LG: Node: analyze_query()
    Note over LG: Detect language, intent

    LG->>VS: Node: search_internal()
    VS->>FAISS: Similarity Search<br/>Top 5 chunks
    FAISS-->>VS: Relevant Documents
    VS-->>LG: Search Results

    LG->>AI: Node: search_web() if needed
    AI->>HF: Web Search Query
    HF-->>AI: Web Results
    AI-->>LG: Web Results

    LG->>GPT: Node: generate_response()
    Note over GPT: Context: Business + Docs + Web
    GPT-->>LG: AI Response

    LG->>LG: Node: translate_response() if needed
    LG-->>AI: Final Response + Confidence

    AI->>WS: send_whatsapp_message()
    WS->>WAB: POST /messages<br/>{to, text}
    WAB-->>WS: Message Sent
    WS->>DB: INSERT Message<br/>direction=OUTBOUND

    AI->>DB: UPDATE inbound message<br/>status=RESPONDED<br/>ai_response, processing_time_ms
    DB-->>AI: Success
    AI-->>CW: Task Complete
    CW->>RMQ: Store Result in Redis

    WAB->>WA: Deliver Response
```

## 3. Document Upload and Processing Flow

```mermaid
sequenceDiagram
    participant U as User (Frontend)
    participant API as API Client
    participant DR as Dashboard Route<br/>/documents/upload
    participant DS as Document Service
    participant S3 as AWS S3
    participant DB as PostgreSQL
    participant RMQ as RabbitMQ
    participant CW as Celery Worker
    participant HF as Hugging Face API
    participant FAISS as FAISS Vector Store

    U->>API: Upload File (FormData)
    API->>API: Add JWT Token
    API->>DR: POST /api/dashboard/documents/upload
    DR->>DR: Validate JWT
    DR->>DR: Check file type

    DR->>DS: upload_document(file, business_id)
    DS->>S3: upload_fileobj()<br/>Key: businesses/{id}/documents/{name}
    S3-->>DS: Upload Success

    DS->>DB: INSERT Document<br/>status=UPLOADED
    DB-->>DS: Document ID

    DS->>RMQ: process_document_upload.delay(doc_id)<br/>Low Priority Queue
    DS-->>DR: {document_id, status}
    DR-->>API: 201 Created
    API->>U: Show Upload Success Toast

    Note over RMQ,CW: Async Processing

    RMQ->>CW: Task Dispatch
    CW->>DB: UPDATE status=PROCESSING
    CW->>DB: FETCH Document
    CW->>S3: Download File
    S3-->>CW: File Data

    alt PDF Document
        CW->>CW: PyPDF2.extract_text()
    else Spreadsheet
        CW->>CW: pandas.read_excel()
    else Website
        CW->>CW: BeautifulSoup.scrape()
    end

    CW->>CW: RecursiveCharacterTextSplitter<br/>chunk_size=1000, overlap=200
    Note over CW: Split into chunks

    loop For each chunk
        CW->>HF: POST /models/{embedding_model}<br/>{inputs: chunk_text}
        HF-->>CW: Embedding Vector (384-dim)
        CW->>FAISS: add_texts([chunk], [embedding])
        FAISS-->>CW: Stored
    end

    CW->>FAISS: save_local(persist_path)
    FAISS-->>CW: Persisted

    CW->>DB: UPDATE Document<br/>status=PROCESSED<br/>chunk_count={n}
    DB-->>CW: Success

    CW-->>RMQ: Task Complete

    Note over U: Frontend polls or refreshes<br/>to see PROCESSED status
```

## 4. Authentication Flow

```mermaid
sequenceDiagram
    participant U as User Browser
    participant FE as Frontend (Next.js)
    participant ZU as Zustand Store
    participant API as API Client
    participant AR as Auth Route
    participant DB as PostgreSQL
    participant JWT as JWT Service

    U->>FE: Navigate to /register
    FE->>U: Show Registration Form
    U->>FE: Submit Form (email, password, business info)
    FE->>ZU: register(data)
    ZU->>API: register(data)
    API->>AR: POST /api/auth/register

    AR->>AR: Validate Pydantic Schema
    AR->>DB: CHECK if email exists
    alt Email exists
        DB-->>AR: User found
        AR-->>API: 400 Email Already Exists
        API->>U: Show Error Toast
    else Email available
        AR->>AR: hash_password(password)
        AR->>DB: INSERT User
        DB-->>AR: User ID
        AR->>DB: INSERT Business
        DB-->>AR: Business ID
        AR->>JWT: create_access_token(user_id)
        JWT-->>AR: JWT Token
        AR-->>API: 201 {user, businesses, token}
        API->>API: setToken(token)<br/>localStorage
        API->>ZU: Set auth state
        ZU->>FE: Navigate to /dashboard
        FE->>U: Show Dashboard
    end

    Note over U,DB: Login Flow

    U->>FE: Navigate to /login
    FE->>U: Show Login Form
    U->>FE: Submit (email, password)
    FE->>ZU: login(email, password)
    ZU->>API: login({email, password})
    API->>AR: POST /api/auth/login

    AR->>DB: SELECT User WHERE email
    alt User not found
        DB-->>AR: None
        AR-->>API: 401 Invalid Credentials
        API->>U: Show Error Toast
    else User found
        DB-->>AR: User record
        AR->>AR: check_password(password, hash)
        alt Password invalid
            AR-->>API: 401 Invalid Credentials
        else Password valid
            AR->>JWT: create_access_token(user_id)
            JWT-->>AR: JWT Token
            AR->>DB: SELECT Businesses WHERE user_id
            DB-->>AR: Business list
            AR-->>API: 200 {user, businesses, token}
            API->>API: setToken(token)<br/>localStorage
            API->>ZU: Update state
            ZU->>FE: Navigate to /dashboard
        end
    end

    Note over U,DB: Protected Route Access

    U->>FE: Navigate to /dashboard/messages
    FE->>API: getMessages(business_id)
    API->>API: Request Interceptor<br/>Add Header:<br/>Authorization: Bearer {token}
    API->>AR: GET /api/dashboard/messages
    AR->>AR: HTTPBearer dependency<br/>Extract token
    AR->>JWT: verify_token(token)
    alt Token invalid/expired
        JWT-->>AR: Exception
        AR-->>API: 401 Unauthorized
        API->>ZU: Clear auth state
        ZU->>FE: Redirect to /login
    else Token valid
        JWT-->>AR: {user_id}
        AR->>DB: SELECT User WHERE id
        DB-->>AR: User object
        AR->>AR: get_current_user() dependency<br/>Inject user
        AR->>DB: SELECT Messages WHERE business_id
        DB-->>AR: Messages list
        AR-->>API: 200 {messages}
        API->>FE: Update state
        FE->>U: Render messages
    end
```

## 5. Database Schema Relationships

```mermaid
erDiagram
    USERS ||--o{ BUSINESSES : owns
    BUSINESSES ||--o{ MESSAGES : receives
    BUSINESSES ||--o{ DOCUMENTS : stores
    BUSINESSES ||--o{ GOOGLE_SHEET_CONNECTIONS : connects

    USERS {
        uuid id PK
        string email UK "Unique index"
        string password_hash
        string first_name
        string last_name
        string phone
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    BUSINESSES {
        uuid id PK
        uuid user_id FK
        string name
        text description
        string website_url
        string whatsapp_phone_number
        string business_category
        text ai_persona
        json supported_languages "Array"
        string default_language
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    MESSAGES {
        uuid id PK
        uuid business_id FK
        string whatsapp_message_id UK
        enum direction "INBOUND/OUTBOUND"
        text content
        string content_type
        string sender_phone
        string recipient_phone
        string sender_name
        enum status "RECEIVED/PROCESSING/RESPONDED/FAILED"
        string language_detected
        text ai_response
        integer processing_time_ms
        integer confidence_score "0-100"
        json message_metadata
        timestamp created_at
    }

    DOCUMENTS {
        uuid id PK
        uuid business_id FK
        string name
        string file_path "S3 path"
        string url
        enum document_type "PDF/SPREADSHEET/WEBSITE"
        enum status "UPLOADED/PROCESSING/PROCESSED/FAILED"
        text processing_error
        text extracted_text
        integer chunk_count
        string embedding_model
        json document_metadata
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    GOOGLE_SHEET_CONNECTIONS {
        uuid id PK
        uuid business_id FK
        string name
        string sheet_url
        string sheet_id
        integer cache_ttl_minutes
        json query_columns "Array"
        timestamp last_synced_at
        text last_sync_error
        integer row_count
        integer column_count
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }
```

## 6. AI Agent LangGraph Workflow

```mermaid
graph TD
    Start([Incoming Message]) --> Init[Initialize State]
    Init --> Analyze[Node: analyze_query]

    Analyze --> ExtractLang[Extract Language]
    ExtractLang --> DetectIntent[Detect Intent]
    DetectIntent --> ClassifyQuery[Classify Query Type]

    ClassifyQuery --> Internal[Node: search_internal]
    Internal --> GetBizContext[Get Business Context]
    GetBizContext --> VectorSearch[FAISS Similarity Search]
    VectorSearch --> RankResults[Rank by Relevance Score]

    RankResults --> Decision1{Results<br/>Sufficient?}
    Decision1 -->|Yes| Generate[Node: generate_response]
    Decision1 -->|No| Web[Node: search_web]

    Web --> WebQuery[Formulate Search Query]
    WebQuery --> SERP[SERP API Call]
    SERP --> ProcessWeb[Process Web Results]
    ProcessWeb --> Generate

    Generate --> BuildPrompt[Build Context Prompt]
    BuildPrompt --> LLMCall[GitHub/OpenAI API Call]
    LLMCall --> ValidateResp[Validate Response]

    ValidateResp --> Decision2{Translation<br/>Needed?}
    Decision2 -->|Yes| Translate[Node: translate_response]
    Decision2 -->|No| Final

    Translate --> DetectTarget[Detect Target Language]
    DetectTarget --> TranslateText[Translate via LLM]
    TranslateText --> Final

    Final[Finalize Response] --> Confidence[Calculate Confidence Score]
    Confidence --> End([Return Response + Metadata])

    style Start fill:#90EE90
    style End fill:#FFB6C1
    style Generate fill:#87CEEB
    style Internal fill:#DDA0DD
    style Web fill:#F0E68C
    style Translate fill:#FFA07A
```

## 7. Celery Task Queue Architecture

```mermaid
graph TB
    subgraph "FastAPI Application"
        A1[WhatsApp Webhook Handler]
        A2[Document Upload Handler]
    end

    subgraph "Message Broker - RabbitMQ Port 5672"
        B1[High Priority Queue]
        B2[Low Priority Queue]
        B3[Dead Letter Queue]
    end

    subgraph "Celery Workers"
        C1[Worker 1<br/>Solo Pool]
        C2[Worker 2<br/>Solo Pool]
        C3[Worker 3<br/>Solo Pool]
    end

    subgraph "Task Definitions"
        D1[process_whatsapp_message<br/>Max Retry: 3<br/>Time Limit: 30min]
        D2[process_document_upload<br/>Max Retry: 3<br/>Time Limit: 30min]
    end

    subgraph "Result Backend - Redis Port 6379"
        E1[Task Results DB 1]
        E2[Task Status Cache]
    end

    subgraph "Monitoring - Flower Port 5555"
        F1[Web Dashboard]
        F2[Task Inspector]
        F3[Worker Stats]
    end

    A1 -->|.delay| B1
    A2 -->|.delay| B2

    B1 --> C1 & C2 & C3
    B2 --> C1 & C2 & C3

    C1 & C2 & C3 --> D1
    C1 & C2 & C3 --> D2

    D1 & D2 -->|Store Result| E1
    D1 & D2 -->|Update Status| E2

    C1 & C2 & C3 -.->|Failed 3 times| B3

    B1 & B2 --> F1
    C1 & C2 & C3 --> F2
    E1 & E2 --> F3

    style B1 fill:#FFB6C1
    style B2 fill:#87CEEB
    style B3 fill:#FF6B6B
    style F1 fill:#90EE90
```

## 8. Complete Technology Stack

```mermaid
graph LR
    subgraph "Frontend Stack"
        FE1[Next.js 15.5.4<br/>React 19]
        FE2[TypeScript]
        FE3[Tailwind CSS]
        FE4[Axios]
        FE5[Zustand]
        FE6[React Query]
        FE7[Recharts]
    end

    subgraph "Backend Stack"
        BE1[FastAPI<br/>Python 3.11+]
        BE2[SQLAlchemy ORM]
        BE3[Pydantic]
        BE4[Uvicorn ASGI]
        BE5[Structlog]
        BE6[Prometheus]
    end

    subgraph "Database Stack"
        DB1[(PostgreSQL<br/>Main Database)]
        DB2[(Redis<br/>Cache + Results)]
        DB3[(MongoDB<br/>Optional)]
    end

    subgraph "AI Stack"
        AI1[LangChain]
        AI2[LangGraph]
        AI3[FAISS]
        AI4[ChromaDB]
        AI5[Hugging Face<br/>Embeddings]
        AI6[GitHub/OpenAI<br/>GPT-4]
    end

    subgraph "Queue Stack"
        Q1[Celery]
        Q2[RabbitMQ]
        Q3[Flower]
    end

    subgraph "Cloud Stack"
        C1[AWS S3<br/>Storage]
        C2[Docker]
        C3[Docker Compose]
    end

    subgraph "External APIs"
        E1[WhatsApp Business API]
        E2[SERP API]
        E3[LangSmith]
    end

    FE1 --> BE1
    BE1 --> BE2
    BE2 --> DB1
    BE1 --> DB2
    BE1 --> Q1
    Q1 --> Q2
    Q1 --> DB2

    BE1 --> AI1
    AI1 --> AI2
    AI2 --> AI3
    AI2 --> AI5
    AI2 --> AI6

    BE1 --> C1
    BE1 --> E1
    AI2 --> E2
    AI2 --> E3
```

## 9. Deployment Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        U1[Web Browser]
        U2[WhatsApp Users]
    end

    subgraph "Load Balancer"
        LB[Nginx/ALB]
    end

    subgraph "Frontend Tier - Next.js"
        FE1[Next.js Instance 1]
        FE2[Next.js Instance 2]
        FE3[Next.js Instance 3]
    end

    subgraph "Backend Tier - FastAPI"
        BE1[FastAPI Instance 1]
        BE2[FastAPI Instance 2]
        BE3[FastAPI Instance 3]
    end

    subgraph "Worker Tier - Celery"
        W1[Worker 1]
        W2[Worker 2]
        W3[Worker 3]
    end

    subgraph "Data Tier"
        DB1[(PostgreSQL<br/>Primary)]
        DB2[(PostgreSQL<br/>Replica)]
        RD[(Redis Cluster)]
        RMQ[RabbitMQ Cluster]
        VC[Vector DB<br/>FAISS/ChromaDB]
    end

    subgraph "Storage Tier"
        S3[AWS S3<br/>Documents]
    end

    subgraph "External Services"
        WA[WhatsApp API]
        AI[GitHub/OpenAI]
        HF[Hugging Face]
    end

    U1 --> LB
    U2 --> WA

    LB --> FE1 & FE2 & FE3
    FE1 & FE2 & FE3 --> BE1 & BE2 & BE3

    BE1 & BE2 & BE3 --> DB1
    DB1 -.Replicate.-> DB2
    BE1 & BE2 & BE3 --> RD
    BE1 & BE2 & BE3 --> RMQ

    RMQ --> W1 & W2 & W3
    W1 & W2 & W3 --> DB1
    W1 & W2 & W3 --> VC
    W1 & W2 & W3 --> RD

    BE1 & BE2 & BE3 --> S3
    W1 & W2 & W3 --> S3

    BE1 & BE2 & BE3 --> WA
    W1 & W2 & W3 --> AI
    W1 & W2 & W3 --> HF

    WA -.Webhook.-> BE1 & BE2 & BE3

    style U1 fill:#90EE90
    style U2 fill:#90EE90
    style DB1 fill:#FFB6C1
    style S3 fill:#87CEEB
```

## 10. Security Architecture

```mermaid
graph TB
    subgraph "Client Security"
        C1[HTTPS Only]
        C2[XSS Prevention<br/>React Sanitization]
        C3[CSRF Protection]
        C4[localStorage Token<br/>HTTPOnly Consideration]
    end

    subgraph "Network Security"
        N1[CORS Policy<br/>Allowed Origins]
        N2[Rate Limiting]
        N3[DDoS Protection]
        N4[SSL/TLS]
    end

    subgraph "Authentication Security"
        A1[JWT HS256]
        A2[Token Expiration<br/>3600s]
        A3[Werkzeug Password Hash<br/>PBKDF2]
        A4[HTTPBearer Middleware]
    end

    subgraph "Authorization Security"
        AU1[Business Ownership Check]
        AU2[User Active Status]
        AU3[Tenant Isolation]
        AU4[Role-Based Access]
    end

    subgraph "Data Security"
        D1[Pydantic Validation]
        D2[SQLAlchemy ORM<br/>SQL Injection Prevention]
        D3[Input Sanitization]
        D4[Output Encoding]
    end

    subgraph "External API Security"
        E1[API Key Management<br/>Environment Variables]
        E2[AWS IAM Credentials]
        E3[WhatsApp Token Rotation]
        E4[Secret Manager]
    end

    subgraph "Database Security"
        DB1[Connection Pooling]
        DB2[Encrypted Connections]
        DB3[Backup Encryption]
        DB4[Access Control]
    end

    subgraph "Monitoring Security"
        M1[Audit Logging]
        M2[Anomaly Detection]
        M3[LangSmith Tracing]
        M4[Prometheus Metrics]
    end

    C1 & C2 & C3 & C4 --> N1
    N1 & N2 & N3 & N4 --> A1
    A1 & A2 & A3 & A4 --> AU1
    AU1 & AU2 & AU3 & AU4 --> D1
    D1 & D2 & D3 & D4 --> E1
    E1 & E2 & E3 & E4 --> DB1
    DB1 & DB2 & DB3 & DB4 --> M1

    style A1 fill:#FFB6C1
    style AU1 fill:#87CEEB
    style E1 fill:#90EE90
    style M1 fill:#DDA0DD
```

---

## Key File References

### Backend Core
- Entry Point: `app/run.py:1`
- App Factory: `app/__init__.py:1`
- Settings: `app/config/settings.py:1`
- Database Config: `app/config/database.py:1`

### Models
- User Model: `app/models/user.py:1`
- Business Model: `app/models/business.py:1`
- Message Model: `app/models/message.py:1`
- Document Model: `app/models/document.py:1`

### Routes
- Auth Routes: `app/api/auth/routes.py:1`
- Dashboard Routes: `app/api/dashboard/routes.py:1`
- WhatsApp Webhook: `app/api/whatsapp/webhook.py:1`
- AI Agent Routes: `app/api/ai/agent.py:1`

### Services
- AI Service: `app/services/ai_service.py:1`
- WhatsApp Service: `app/services/whatsapp_service.py:1`
- Vector Service: `app/services/vector_service.py:1`
- Document Service: `app/services/document_service.py:1`

### Frontend Core
- API Client: `frontend/src/lib/api-client.ts:1`
- Auth Store: `frontend/src/store/auth-store.ts:1`
- Dashboard Layout: `frontend/src/components/layout/DashboardLayout.tsx:1`

---

## How to Read These Diagrams

1. **System Architecture (Diagram 1)**: Shows all layers and components with their connections
2. **Message Flow (Diagram 2)**: Detailed sequence of an inbound WhatsApp message
3. **Document Upload (Diagram 3)**: Complete document processing pipeline
4. **Authentication (Diagram 4)**: Registration, login, and protected route access
5. **Database Schema (Diagram 5)**: Entity relationships and table structures
6. **AI Agent (Diagram 6)**: LangGraph workflow nodes and decision logic
7. **Celery Queue (Diagram 7)**: Task queue architecture and priorities
8. **Tech Stack (Diagram 8)**: All technologies and their relationships
9. **Deployment (Diagram 9)**: Production deployment architecture
10. **Security (Diagram 10)**: Security layers and implementations

Each diagram can be rendered using Mermaid-compatible tools or viewers.
