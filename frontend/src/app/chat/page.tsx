'use client';

import { ProtectedRoute } from '@/components/auth/protected-route';
import { ChatSidebar } from '@/components/chat/chat-sidebar';
import { ChatHeader } from '@/components/chat/chat-header';
import { ChatMessages } from '@/components/chat/chat-messages';
import { ChatInput } from '@/components/chat/chat-input';

export default function ChatPage() {
  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-background">
        {/* Sidebar - hidden on mobile */}
        <div className="hidden md:block">
          <ChatSidebar />
        </div>

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col min-w-0">
          <ChatHeader />
          <ChatMessages />
          <ChatInput />
        </div>
      </div>
    </ProtectedRoute>
  );
}

