'use client';

import { useEffect } from 'react';
import { useSessionStore } from '@/stores/session-store';
import { useAuthStore } from '@/stores/auth-store';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Bot,
  MessageSquarePlus,
  Trash2,
  MessageSquare,
  Settings,
  Database,
  LogOut,
} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';

export function ChatSidebar() {
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const {
    sessions,
    currentSession,
    agents,
    selectedAgent,
    loadSessions,
    loadAgents,
    createSession,
    selectSession,
    deleteSessionById,
    setSelectedAgent,
  } = useSessionStore();

  useEffect(() => {
    loadSessions();
    loadAgents();
  }, [loadSessions, loadAgents]);

  const handleNewChat = async () => {
    if (!selectedAgent) {
      toast.error('Please select an agent first');
      return;
    }
    await createSession(selectedAgent);
    toast.success('New chat created');
  };

  const handleDeleteSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await deleteSessionById(id);
    toast.success('Chat deleted');
  };

  const handleLogout = async () => {
    await logout();
    router.push('/login');
    toast.success('Logged out successfully');
  };

  return (
    <div className="flex flex-col h-full w-64 bg-card border-r border-border">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2 mb-4">
          <Bot className="h-6 w-6 text-primary" />
          <span className="font-semibold">ADK Agents</span>
        </div>
        
        {/* Agent Selector */}
        <Select value={selectedAgent} onValueChange={setSelectedAgent}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select agent" />
          </SelectTrigger>
          <SelectContent>
            {agents.map((agent) => (
              <SelectItem key={agent.name} value={agent.name}>
                <div className="flex items-center gap-2">
                  <span>{agent.name}</span>
                  <Badge variant="secondary" className="text-xs">
                    {agent.status}
                  </Badge>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button onClick={handleNewChat} className="w-full mt-3" variant="default">
          <MessageSquarePlus className="h-4 w-4 mr-2" />
          New Chat
        </Button>
      </div>

      {/* Sessions List */}
      <ScrollArea className="flex-1">
        <div className="p-2">
          <p className="text-xs text-muted-foreground px-2 mb-2">Recent Chats</p>
          {sessions.length === 0 ? (
            <p className="text-sm text-muted-foreground px-2 py-4 text-center">
              No chats yet
            </p>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => selectSession(session.id)}
                className={`group flex items-center gap-2 p-2 rounded-lg cursor-pointer hover:bg-accent transition-colors ${
                  currentSession?.id === session.id ? 'bg-accent' : ''
                }`}
              >
                <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm truncate">{session.name}</p>
                  <p className="text-xs text-muted-foreground truncate">
                    {session.agent} · {session.messages.length} msgs
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 opacity-0 group-hover:opacity-100"
                  onClick={(e) => handleDeleteSession(session.id, e)}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            ))
          )}
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="p-2 border-t border-border space-y-1">
        <Link href="/memory">
          <Button variant="ghost" className="w-full justify-start">
            <Database className="h-4 w-4 mr-2" />
            Memory Bank
          </Button>
        </Link>
        <Link href="/settings">
          <Button variant="ghost" className="w-full justify-start">
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </Button>
        </Link>
        <Separator className="my-2" />
        <div className="px-2 py-1">
          <p className="text-sm font-medium truncate">{user?.username}</p>
          <p className="text-xs text-muted-foreground truncate">{user?.tenant_id}</p>
        </div>
        <Button variant="ghost" className="w-full justify-start text-destructive" onClick={handleLogout}>
          <LogOut className="h-4 w-4 mr-2" />
          Logout
        </Button>
      </div>
    </div>
  );
}

