import { create } from 'zustand';
import { Session, ChatMessage, AgentInfo } from '@/types';
import { getAllSessions, saveSession, deleteSession, getSession } from '@/lib/db';
import { api } from '@/lib/api';

interface SessionState {
  sessions: Session[];
  currentSession: Session | null;
  agents: AgentInfo[];
  selectedAgent: string;
  isLoading: boolean;
  isSending: boolean;
  connectionMode: 'rest' | 'websocket';
  wsConnection: WebSocket | null;

  // Actions
  loadSessions: () => Promise<void>;
  loadAgents: () => Promise<void>;
  createSession: (agent: string) => Promise<Session>;
  selectSession: (id: string) => Promise<void>;
  deleteSessionById: (id: string) => Promise<void>;
  setSelectedAgent: (agent: string) => void;
  setConnectionMode: (mode: 'rest' | 'websocket') => void;
  sendMessage: (content: string) => Promise<void>;
  addMessage: (message: ChatMessage) => void;
  updateLastMessage: (content: string) => void;
  connectWebSocket: () => void;
  disconnectWebSocket: () => void;
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  sessions: [],
  currentSession: null,
  agents: [],
  selectedAgent: '',
  isLoading: false,
  isSending: false,
  connectionMode: 'rest',
  wsConnection: null,

  loadSessions: async () => {
    set({ isLoading: true });
    try {
      const sessions = await getAllSessions();
      set({ sessions, isLoading: false });
    } catch (error) {
      console.error('Failed to load sessions:', error);
      set({ isLoading: false });
    }
  },

  loadAgents: async () => {
    try {
      const agents = await api.listAgents();
      const selectedAgent = agents.length > 0 ? agents[0].name : '';
      set({ agents, selectedAgent });
    } catch (error) {
      console.error('Failed to load agents:', error);
    }
  },

  createSession: async (agent: string) => {
    const session: Session = {
      id: generateId(),
      name: `Chat ${new Date().toLocaleString()}`,
      agent,
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    await saveSession(session);
    const sessions = await getAllSessions();
    set({ sessions, currentSession: session });
    return session;
  },

  selectSession: async (id: string) => {
    const session = await getSession(id);
    if (session) {
      set({ currentSession: session, selectedAgent: session.agent });
    }
  },

  deleteSessionById: async (id: string) => {
    await deleteSession(id);
    const sessions = await getAllSessions();
    const { currentSession } = get();
    set({
      sessions,
      currentSession: currentSession?.id === id ? null : currentSession,
    });
  },

  setSelectedAgent: (agent: string) => set({ selectedAgent: agent }),
  setConnectionMode: (mode: 'rest' | 'websocket') => set({ connectionMode: mode }),

  sendMessage: async (content: string) => {
    const { currentSession, selectedAgent, connectionMode, wsConnection } = get();
    if (!currentSession) return;

    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    get().addMessage(userMessage);
    set({ isSending: true });

    if (connectionMode === 'websocket' && wsConnection) {
      wsConnection.send(JSON.stringify({ message: content, agent: selectedAgent }));
    } else {
      try {
        const response = await api.chat({
          message: content,
          session_id: currentSession.id,
          agent: selectedAgent,
        });
        const assistantMessage: ChatMessage = {
          id: generateId(),
          role: 'assistant',
          content: response.message,
          timestamp: new Date(),
          agent: response.agent,
        };
        get().addMessage(assistantMessage);
      } catch (error) {
        const errMsg = (error as { detail?: string }).detail || 'Failed to send message';
        const errorMessage: ChatMessage = {
          id: generateId(),
          role: 'assistant',
          content: `Error: ${errMsg}`,
          timestamp: new Date(),
        };
        get().addMessage(errorMessage);
      }
    }
    set({ isSending: false });
  },

  addMessage: (message: ChatMessage) => {
    const { currentSession, sessions } = get();
    if (!currentSession) return;
    const updated = {
      ...currentSession,
      messages: [...currentSession.messages, message],
      updatedAt: new Date(),
    };
    saveSession(updated);
    set({
      currentSession: updated,
      sessions: sessions.map(s => (s.id === updated.id ? updated : s)),
    });
  },

  updateLastMessage: (content: string) => {
    const { currentSession, sessions } = get();
    if (!currentSession || currentSession.messages.length === 0) return;
    const messages = [...currentSession.messages];
    const last = messages[messages.length - 1];
    messages[messages.length - 1] = { ...last, content: last.content + content };
    const updated = { ...currentSession, messages, updatedAt: new Date() };
    saveSession(updated);
    set({
      currentSession: updated,
      sessions: sessions.map(s => (s.id === updated.id ? updated : s)),
    });
  },

  connectWebSocket: () => {
    const { currentSession, selectedAgent, wsConnection } = get();
    if (wsConnection) wsConnection.close();
    if (!currentSession) return;

    const ws = api.createWebSocket(currentSession.id);
    ws.onopen = () => console.log('WebSocket connected');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'chunk') {
        get().updateLastMessage(data.content);
      } else if (data.type === 'complete') {
        set({ isSending: false });
      } else if (data.error) {
        get().addMessage({
          id: generateId(),
          role: 'assistant',
          content: `Error: ${data.error}`,
          timestamp: new Date(),
        });
        set({ isSending: false });
      }
    };
    ws.onerror = () => set({ isSending: false });
    ws.onclose = () => set({ wsConnection: null });
    set({ wsConnection: ws });
  },

  disconnectWebSocket: () => {
    const { wsConnection } = get();
    if (wsConnection) {
      wsConnection.close();
      set({ wsConnection: null });
    }
  },
}));

