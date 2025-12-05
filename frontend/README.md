# ADK Agent Platform - Frontend

A comprehensive Next.js frontend application for testing and interacting with the Multi-Agent ADK FastAPI backend.

## Features

- **Authentication**: JWT-based login with protected routes
- **Chat Interface**: ChatGPT-style interface with real-time messaging
- **Agent Selection**: Switch between available ADK agents
- **Session Management**: Persistent chat history using IndexedDB
- **Connection Modes**: REST and WebSocket support with toggle
- **Memory Bank**: Interface for Vertex AI Memory Bank operations
- **Settings**: Token management and API connection status

## Prerequisites

- Node.js 18+ (latest recommended)
- npm
- Backend API running on `http://localhost:8000`

## Quick Start

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Configure environment:**
   The `.env.local` file is already configured with:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
   Modify if your backend runs on a different URL.

3. **Start the development server:**
   ```bash
   npm run dev
   ```

4. **Open the application:**
   Navigate to [http://localhost:3000](http://localhost:3000)

## Pages

| Path | Description |
|------|-------------|
| `/login` | Authentication page |
| `/chat` | Main chat interface with agents |
| `/memory` | Memory Bank management |
| `/settings` | User profile and API settings |

## Demo Credentials

| Username | Password | Tenant | Permissions |
|----------|----------|--------|-------------|
| admin | admin123 | default | Full access |
| user1 | user123 | tenant1 | agent:read, agent:execute |
| user2 | user123 | tenant2 | agent:read, agent:execute |

## API Endpoints Tested

### Authentication
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user
- `POST /api/auth/refresh` - Refresh JWT token
- `POST /api/auth/logout` - Logout

### Agents
- `GET /api/agents/list` - List available agents
- `POST /api/agents/chat` - Chat with an agent (REST)
- `WS /ws/chat/{session_id}` - Real-time chat (WebSocket)

### Memory Bank
- `GET /api/memory/status` - Memory Bank status
- `POST /api/memory/save` - Save session to memory
- `POST /api/memory/search` - Search memories

### Health
- `GET /api/health` - API health check

## Tech Stack

- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui
- **State Management**: Zustand
- **Persistence**: IndexedDB (via idb)
- **Icons**: Lucide React
- **Toasts**: Sonner

## Project Structure

```
frontend/
├── src/
│   ├── app/                 # Next.js App Router pages
│   │   ├── chat/           # Chat page
│   │   ├── login/          # Login page
│   │   ├── memory/         # Memory management page
│   │   ├── settings/       # Settings page
│   │   ├── layout.tsx      # Root layout
│   │   └── page.tsx        # Redirects to /chat
│   ├── components/
│   │   ├── auth/           # Auth components
│   │   ├── chat/           # Chat components
│   │   └── ui/             # shadcn/ui components
│   ├── lib/
│   │   ├── api.ts          # API client
│   │   ├── db.ts           # IndexedDB operations
│   │   └── utils.ts        # Utilities
│   ├── stores/
│   │   ├── auth-store.ts   # Auth state
│   │   └── session-store.ts # Session state
│   └── types/
│       └── index.ts        # TypeScript types
├── .env.local              # Environment variables
└── package.json
```

## Development

```bash
# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Lint code
npm run lint
```

## Notes

- The frontend uses a dark theme by default
- Sessions are stored locally in IndexedDB for persistence
- WebSocket mode enables real-time streaming responses
- The Memory Bank features require the backend to have Vertex AI configured
