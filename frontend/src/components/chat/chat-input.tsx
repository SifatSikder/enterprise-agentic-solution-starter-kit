'use client';

import { useState, useRef, useEffect } from 'react';
import { useSessionStore } from '@/stores/session-store';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Send, Loader2, Wifi, WifiOff } from 'lucide-react';
import { toast } from 'sonner';

export function ChatInput() {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const {
    currentSession,
    selectedAgent,
    isSending,
    connectionMode,
    wsConnection,
    sendMessage,
    setConnectionMode,
    connectWebSocket,
    disconnectWebSocket,
    createSession,
  } = useSessionStore();

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [message]);

  // Handle WebSocket connection when mode changes
  useEffect(() => {
    if (connectionMode === 'websocket' && currentSession) {
      connectWebSocket();
    } else {
      disconnectWebSocket();
    }
    return () => {
      if (connectionMode === 'websocket') {
        disconnectWebSocket();
      }
    };
  }, [connectionMode, currentSession?.id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    // Auto-create session if none exists
    if (!currentSession) {
      if (!selectedAgent) {
        toast.error('Please select an agent first');
        return;
      }
      await createSession(selectedAgent);
    }

    await sendMessage(message.trim());
    setMessage('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const toggleConnectionMode = () => {
    const newMode = connectionMode === 'rest' ? 'websocket' : 'rest';
    setConnectionMode(newMode);
    toast.success(`Switched to ${newMode.toUpperCase()} mode`);
  };

  return (
    <div className="border-t border-border p-4">
      <div className="max-w-3xl mx-auto">
        {/* Connection Mode Toggle */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Switch
              id="connection-mode"
              checked={connectionMode === 'websocket'}
              onCheckedChange={toggleConnectionMode}
              disabled={!currentSession}
            />
            <Label htmlFor="connection-mode" className="text-sm cursor-pointer">
              {connectionMode === 'websocket' ? (
                <span className="flex items-center gap-1">
                  <Wifi className="h-3 w-3" />
                  WebSocket (Streaming)
                </span>
              ) : (
                <span className="flex items-center gap-1">
                  <WifiOff className="h-3 w-3" />
                  REST (Request/Response)
                </span>
              )}
            </Label>
          </div>
          {connectionMode === 'websocket' && (
            <Badge variant={wsConnection ? 'default' : 'secondary'}>
              {wsConnection ? 'Connected' : 'Disconnected'}
            </Badge>
          )}
        </div>

        {/* Message Input */}
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              currentSession
                ? `Message ${currentSession.agent}...`
                : 'Select or create a chat to start messaging...'
            }
            className="min-h-[44px] max-h-[200px] resize-none"
            rows={1}
            disabled={isSending}
          />
          <Button
            type="submit"
            size="icon"
            disabled={!message.trim() || isSending}
            className="shrink-0 h-11 w-11"
          >
            {isSending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
        <p className="text-xs text-muted-foreground mt-2 text-center">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}

