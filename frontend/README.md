# WhatsApp AI SaaS - Frontend

Production-grade Next.js frontend for AI-powered WhatsApp business automation.

## 🚀 Features

- **Authentication System**: Secure login/registration with JWT tokens
- **Dashboard**: Real-time analytics and message monitoring
- **Message Management**: Browse and filter conversations
- **Document Management**: Upload and manage knowledge base content
- **AI Agent Testing**: Test and configure your AI assistant
- **Business Settings**: Customize AI persona and supported languages
- **Responsive Design**: Mobile-first design with Tailwind CSS
- **Type-Safe**: Full TypeScript support
- **State Management**: Zustand for efficient state management
- **API Integration**: Axios client with request/response interceptors

## 📁 Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js 13+ app directory
│   │   ├── dashboard/         # Dashboard pages
│   │   │   ├── page.tsx       # Overview dashboard
│   │   │   ├── messages/      # Messages management
│   │   │   ├── documents/     # Document management
│   │   │   ├── settings/      # Business settings
│   │   │   └── ai-agent/      # AI agent testing
│   │   ├── login/             # Login page
│   │   ├── register/          # Registration page
│   │   └── layout.tsx         # Root layout
│   ├── components/
│   │   ├── layout/            # Layout components
│   │   │   └── DashboardLayout.tsx
│   │   └── ui/                # UI components
│   │       ├── Button.tsx
│   │       ├── Input.tsx
│   │       └── Card.tsx
│   ├── lib/                   # Utilities and configurations
│   │   └── api-client.ts      # API client with interceptors
│   ├── store/                 # Zustand state management
│   │   └── auth-store.ts      # Authentication state
│   └── types/                 # TypeScript type definitions
│       └── index.ts
├── public/                    # Static assets
├── .env.local                 # Environment variables
├── next.config.ts             # Next.js configuration
├── tailwind.config.ts         # Tailwind CSS configuration
├── tsconfig.json              # TypeScript configuration
└── package.json               # Dependencies
```

## 🛠️ Tech Stack

- **Framework**: Next.js 15.5.4 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS 4
- **State Management**: Zustand
- **HTTP Client**: Axios
- **Date Handling**: date-fns
- **Icons**: lucide-react
- **Notifications**: react-hot-toast
- **Charts**: Recharts (for analytics)

## 📦 Installation

1. **Install dependencies**:
```bash
cd frontend
npm install
```

2. **Configure environment variables**:
```bash
cp .env.example .env.local
```

Edit `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

3. **Run development server**:
```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## 🔧 Available Scripts

- `npm run dev` - Start development server with Turbopack
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run lint` - Run ESLint

## 🏗️ Building for Production

```bash
# Build the application
npm run build

# Start production server
npm start
```

## 🔐 Authentication Flow

1. User registers/logs in via `/register` or `/login`
2. JWT token is stored in localStorage
3. API client automatically includes token in requests
4. Token is verified on protected routes
5. Expired tokens trigger automatic redirect to login

## 📡 API Integration

The frontend integrates with the FastAPI backend through the API client (`src/lib/api-client.ts`):

### Available API Methods:

**Authentication**:
- `register(data)` - User registration
- `login(data)` - User login
- `verifyToken()` - Token verification

**Dashboard**:
- `getOverview(businessId)` - Dashboard statistics
- `getMessages(businessId, params)` - Message list with pagination
- `getAnalytics(businessId, days)` - Analytics data
- `getDocuments(businessId)` - Document list
- `uploadDocument(formData)` - Upload document
- `getBusinessSettings(businessId)` - Get settings
- `updateBusinessSettings(data)` - Update settings

**AI Agent**:
- `testAIMessage(businessId, message)` - Test AI response
- `getAgentStatus(businessId)` - Get agent configuration
- `reloadKnowledge(businessId)` - Reload knowledge base

**WhatsApp**:
- `getWebhookStatus()` - Webhook status
- `sendMessage(to, message)` - Send message

## 🎨 Component Library

### UI Components

**Button**:
```tsx
<Button variant="primary" size="md" isLoading={false}>
  Click Me
</Button>
```

**Input**:
```tsx
<Input
  label="Email"
  type="email"
  placeholder="you@example.com"
  error="Error message"
/>
```

**Card**:
```tsx
<Card title="Card Title" subtitle="Subtitle">
  Content here
</Card>
```

## 🔄 State Management

The app uses Zustand for state management. Main stores:

### Auth Store (`src/store/auth-store.ts`):
- User authentication state
- Business selection
- Login/logout/register actions
- Token verification

```tsx
const { user, selectedBusiness, login, logout } = useAuthStore();
```

## 🌐 Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000` |

## 📱 Responsive Design

The application is fully responsive and optimized for:
- Desktop (1024px+)
- Tablet (768px - 1023px)
- Mobile (< 768px)

## 🔒 Security Features

- JWT token authentication
- Automatic token refresh handling
- Protected routes with authentication guards
- XSS protection via React
- Secure HTTP-only cookies support
- CORS configuration

## 🚀 Deployment

### Vercel (Recommended):

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### Docker:

```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
```

Build and run:
```bash
docker build -t whatsapp-ai-frontend .
docker run -p 3000:3000 whatsapp-ai-frontend
```

## 📊 Performance Optimization

- **Code Splitting**: Automatic via Next.js
- **Image Optimization**: Next.js Image component
- **Font Optimization**: Next.js font optimization
- **Caching**: Browser caching + SWR patterns
- **Lazy Loading**: Dynamic imports for heavy components

## 🔗 Integration with Backend

The frontend expects the FastAPI backend to be running at `http://localhost:8000` by default. All API routes are prefixed with `/api`:

- `/api/auth/*` - Authentication endpoints
- `/api/dashboard/*` - Dashboard endpoints
- `/api/whatsapp/*` - WhatsApp endpoints
- `/api/ai/*` - AI agent endpoints

Make sure CORS is properly configured in the FastAPI backend to allow requests from the frontend domain.
