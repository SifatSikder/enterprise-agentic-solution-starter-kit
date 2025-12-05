import { create } from 'zustand';
import { UserInfo, TokenResponse } from '@/types';
import { api } from '@/lib/api';

interface AuthState {
  user: UserInfo | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  login: (username: string, password: string, tenantId?: string) => Promise<boolean>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  loadUser: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: typeof window !== 'undefined' ? localStorage.getItem('access_token') : null,
  isAuthenticated: false,
  isLoading: true,
  error: null,

  login: async (username: string, password: string, tenantId?: string) => {
    set({ isLoading: true, error: null });
    try {
      const response: TokenResponse = await api.login(username, password, tenantId);
      localStorage.setItem('access_token', response.access_token);
      set({ token: response.access_token });
      
      // Load user info after login
      const user = await api.getMe();
      set({ user, isAuthenticated: true, isLoading: false });
      return true;
    } catch (error) {
      const message = (error as { detail?: string }).detail || 'Login failed';
      set({ error: message, isLoading: false });
      return false;
    }
  },

  logout: async () => {
    try {
      await api.logout();
    } catch {
      // Ignore logout errors
    }
    localStorage.removeItem('access_token');
    set({ user: null, token: null, isAuthenticated: false, error: null });
  },

  refreshToken: async () => {
    try {
      const response = await api.refreshToken();
      localStorage.setItem('access_token', response.access_token);
      set({ token: response.access_token });
      return true;
    } catch {
      await get().logout();
      return false;
    }
  },

  loadUser: async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      set({ isLoading: false, isAuthenticated: false });
      return;
    }

    try {
      const user = await api.getMe();
      set({ user, isAuthenticated: true, isLoading: false, token });
    } catch {
      localStorage.removeItem('access_token');
      set({ user: null, token: null, isAuthenticated: false, isLoading: false });
    }
  },

  clearError: () => set({ error: null }),
}));

