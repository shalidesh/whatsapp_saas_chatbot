# Quick Start Guide - WhatsApp AI SaaS Frontend

Get your frontend up and running in 5 minutes!

## Prerequisites

- Node.js 18+ installed
- FastAPI backend running on `http://localhost:8000`
- npm or yarn package manager

## 🚀 Quick Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

This installs all required packages including:
- Next.js 15.5.4
- React 19
- TypeScript
- Tailwind CSS
- Axios, Zustand, and more

### 2. Configure Environment

```bash
cp .env.example .env.local
```

Edit `.env.local` if your backend runs on a different URL:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Start Development Server

```bash
npm run dev
```

The application will start at `http://localhost:3000`

## 🎯 First Steps

### 1. Create an Account

1. Navigate to `http://localhost:3000`
2. You'll be redirected to `/login`
3. Click "Sign up" to go to `/register`
4. Fill in the registration form:
   - **First Name**: Your first name
   - **Last Name**: Your last name
   - **Email**: Your email address
   - **Password**: At least 8 characters
   - **Phone**: Your WhatsApp phone number
   - **Business Name**: Your business name

5. Click "Create Account"
6. You'll be automatically logged in and redirected to the dashboard

### 2. Explore the Dashboard

After registration, you'll see:
- **Overview Dashboard**: Key metrics and statistics
- **Recent Messages**: Latest customer conversations
- **Quick Action Cards**: Fast access to features

### 3. Configure Your Business

Navigate to **Settings** from the sidebar:

1. Update business information:
   - Business name and description
   - Website URL
   - WhatsApp phone number
   - Business category

2. Configure AI Agent:
   - **AI Persona**: Define how your AI should behave
   - **Supported Languages**: Select languages (EN, SI, TA, ES, FR)
   - **Default Language**: Choose default language

3. Click "Save Changes"

### 4. Upload Documents

Navigate to **Documents** from the sidebar:

1. Click "Upload Document"
2. Choose upload type:
   - **File**: Upload PDF, TXT, CSV, or XLSX
   - **URL**: Import from website URL
3. Select document type
4. Upload your content
5. Documents will be processed in the background

### 5. Test Your AI Agent

Navigate to **AI Agent** from the sidebar:

1. View agent status and configuration
2. Type a test message in the input field
3. Click "Send" or press Enter
4. View AI response with:
   - Response text
   - Detected language
   - Confidence score
   - Processing time

Try sample messages like:
- "What are your business hours?"
- "Do you offer international shipping?"
- "How can I track my order?"

### 6. Monitor Messages

Navigate to **Messages** from the sidebar:

- View all conversations
- Filter by direction (inbound/outbound)
- Filter by status
- Navigate through pages
- See message details including language and processing time

## 🎨 UI Overview

### Navigation

The sidebar contains:
- **Dashboard**: Home/overview
- **Messages**: Conversation management
- **Documents**: Knowledge base
- **AI Agent**: Testing and configuration
- **Settings**: Business settings

### Business Selector

At the top of the sidebar:
- Shows current selected business
- Click to switch between businesses (if you have multiple)

### User Menu

At the bottom of the sidebar:
- User avatar and name
- Logout button

## 📱 Mobile View

The interface is fully responsive:
- Tap the menu icon (☰) to open sidebar
- All features accessible on mobile
- Touch-optimized interface

## 🔧 Development Tips

### Hot Reload

Changes to code automatically refresh the browser. No manual reload needed.

### Type Safety

TypeScript provides autocomplete and type checking:
```tsx
import { useAuthStore } from '@/store/auth-store';

// TypeScript knows the shape of the store
const { user, selectedBusiness } = useAuthStore();
```

### API Client Usage

```tsx
import { apiClient } from '@/lib/api-client';

// All methods are typed
const messages = await apiClient.getMessages(businessId, {
  page: 1,
  limit: 20
});
```

### Toast Notifications

```tsx
import toast from 'react-hot-toast';

toast.success('Success message');
toast.error('Error message');
toast.loading('Loading...');
```

## 🔍 Troubleshooting

### Port Already in Use

If port 3000 is already in use:
```bash
# Kill process on port 3000 (Windows)
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Kill process on port 3000 (Mac/Linux)
lsof -ti:3000 | xargs kill
```

Or run on a different port:
```bash
PORT=3001 npm run dev
```

### API Connection Error

Check that:
1. Backend is running on `http://localhost:8000`
2. `.env.local` has correct `NEXT_PUBLIC_API_URL`
3. CORS is configured in backend to allow `http://localhost:3000`

### Login Not Working

1. Check browser console for errors
2. Verify backend is running
3. Check network tab for API responses
4. Ensure user exists in database

### Token Expired

If you see "Session expired":
1. You'll be automatically redirected to login
2. Simply login again
3. Token is valid for the duration configured in backend

## 📚 Learn More

### Project Structure
```
frontend/
├── src/
│   ├── app/              # Pages (Next.js App Router)
│   ├── components/       # Reusable components
│   ├── lib/              # Utilities and API client
│   ├── store/            # State management
│   └── types/            # TypeScript types
```

### Key Files
- `src/lib/api-client.ts` - API integration
- `src/store/auth-store.ts` - Authentication state
- `src/types/index.ts` - Type definitions
- `next.config.ts` - Next.js configuration

### Available Pages
- `/` - Home (redirects to dashboard or login)
- `/login` - User login
- `/register` - User registration
- `/dashboard` - Main dashboard
- `/dashboard/messages` - Message management
- `/dashboard/documents` - Document management
- `/dashboard/settings` - Business settings
- `/dashboard/ai-agent` - AI agent testing

## 🎯 Next Steps

1. ✅ Complete initial setup
2. ✅ Create account and login
3. ✅ Configure business settings
4. ✅ Upload knowledge base documents
5. ✅ Test AI agent responses
6. ✅ Monitor incoming messages

## 💡 Pro Tips

1. **Multiple Businesses**: Create multiple businesses for different use cases
2. **Language Testing**: Test AI responses in different languages
3. **Document Types**: Upload various document types for better AI knowledge
4. **AI Persona**: Customize AI personality for your brand voice
5. **Response Time**: Monitor average response time in dashboard

## 🔗 Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Zustand Documentation](https://docs.pmnd.rs/zustand)

## 🆘 Need Help?

If you encounter issues:
1. Check the browser console for errors
2. Check the terminal for server errors
3. Verify backend is running and accessible
4. Review the README.md for detailed documentation
5. Check FEATURES.md for architecture details

Happy building! 🚀
