// API Response Types

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  tenant_id: string;
}

export interface UserInfo {
  user_id: string;
  username: string;
  tenant_id: string;
  permissions: string[];
}

export interface AgentInfo {
  name: string;
  description: string;
  capabilities: string[];
  status: string;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  agent?: string;
  context?: Record<string, unknown>;
}

export interface ChatResponse {
  message: string;
  agent: string;
  session_id: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface MemoryStatusResponse {
  enabled: boolean;
  initialized: boolean;
  auto_save: boolean;
  project_id?: string;
  location?: string;
  agent_engine_id?: string;
}

export interface SaveSessionRequest {
  session_id: string;
  user_id?: string;
}

export interface SaveSessionResponse {
  success: boolean;
  message: string;
  session_id: string;
  tenant_id: string;
  user_id: string;
}

export interface SearchMemoryRequest {
  query: string;
  user_id?: string;
  limit?: number;
}

export interface SearchMemoryResponse {
  query: string;
  memories: Record<string, unknown>[];
  count: number;
  tenant_id: string;
  user_id: string;
}

// WebSocket Message Types
export interface WSMessage {
  message: string;
  agent?: string;
}

export interface WSChunk {
  type: 'chunk' | 'complete' | 'error';
  content?: string;
  agent?: string;
  error?: string;
}

// Session Types (for local storage)
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  agent?: string;
}

export interface Session {
  id: string;
  name: string;
  agent: string;
  messages: ChatMessage[];
  createdAt: Date;
  updatedAt: Date;
}

// API Error
export interface APIError {
  detail: string;
  status?: number;
}

