'use client';

import { useSessionStore } from '@/stores/session-store';
import { useAuthStore } from '@/stores/auth-store';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { Menu, Bot, User } from 'lucide-react';
import { ChatSidebar } from './chat-sidebar';

export function ChatHeader() {
  const { currentSession } = useSessionStore();
  const { user } = useAuthStore();

  return (
    <header className="h-14 border-b border-border flex items-center justify-between px-4 bg-card">
      {/* Mobile Menu */}
      <div className="flex items-center gap-3">
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="md:hidden">
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="p-0 w-64">
            <ChatSidebar />
          </SheetContent>
        </Sheet>

        {/* Current Chat Info */}
        {currentSession ? (
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            <div>
              <p className="font-medium text-sm">{currentSession.agent}</p>
              <p className="text-xs text-muted-foreground">
                {currentSession.messages.length} messages
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">No chat selected</span>
          </div>
        )}
      </div>

      {/* User Info */}
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="hidden sm:flex">
          {user?.tenant_id}
        </Badge>
        <div className="flex items-center gap-2 text-sm">
          <User className="h-4 w-4" />
          <span className="hidden sm:inline">{user?.username}</span>
        </div>
      </div>
    </header>
  );
}

