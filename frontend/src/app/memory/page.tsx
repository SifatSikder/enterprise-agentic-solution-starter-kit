'use client';

import { useState, useEffect } from 'react';
import { ProtectedRoute } from '@/components/auth/protected-route';
import { api } from '@/lib/api';
import { MemoryStatusResponse, SearchMemoryResponse } from '@/types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import {
  Database,
  Search,
  Save,
  ArrowLeft,
  CheckCircle,
  XCircle,
  Loader2,
  Brain,
} from 'lucide-react';
import Link from 'next/link';

export default function MemoryPage() {
  const [status, setStatus] = useState<MemoryStatusResponse | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(true);
  const [sessionId, setSessionId] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchLimit, setSearchLimit] = useState(10);
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchMemoryResponse | null>(null);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    setIsLoadingStatus(true);
    try {
      const data = await api.getMemoryStatus();
      setStatus(data);
    } catch (error) {
      const msg = (error as { detail?: string }).detail || 'Failed to load memory status';
      toast.error(msg);
    } finally {
      setIsLoadingStatus(false);
    }
  };

  const handleSaveSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionId.trim()) {
      toast.error('Please enter a session ID');
      return;
    }
    setIsSaving(true);
    try {
      await api.saveSession({ session_id: sessionId });
      toast.success('Session saved to memory');
      setSessionId('');
    } catch (error) {
      const msg = (error as { detail?: string }).detail || 'Failed to save session';
      toast.error(msg);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      toast.error('Please enter a search query');
      return;
    }
    setIsSearching(true);
    try {
      const results = await api.searchMemory({ query: searchQuery, limit: searchLimit });
      setSearchResults(results);
      toast.success(`Found ${results.count} memories`);
    } catch (error) {
      const msg = (error as { detail?: string }).detail || 'Failed to search memories';
      toast.error(msg);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background">
        {/* Header */}
        <header className="border-b border-border">
          <div className="container mx-auto px-4 py-4 flex items-center gap-4">
            <Link href="/chat">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="h-5 w-5" />
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Database className="h-6 w-6 text-primary" />
              <h1 className="text-xl font-semibold">Memory Bank</h1>
            </div>
          </div>
        </header>

        <main className="container mx-auto px-4 py-8 max-w-4xl">
          {/* Status Card */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-5 w-5" />
                Memory Bank Status
              </CardTitle>
              <CardDescription>
                Vertex AI Memory Bank configuration and status
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoadingStatus ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Loading status...</span>
                </div>
              ) : status ? (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <StatusItem label="Enabled" value={status.enabled} />
                  <StatusItem label="Initialized" value={status.initialized} />
                  <StatusItem label="Auto Save" value={status.auto_save} />
                  {status.project_id && (
                    <div className="col-span-2 md:col-span-3">
                      <p className="text-sm text-muted-foreground">Project: {status.project_id}</p>
                      <p className="text-sm text-muted-foreground">Location: {status.location}</p>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-muted-foreground">Unable to load status</p>
              )}
            </CardContent>
          </Card>

          <div className="grid md:grid-cols-2 gap-6">
            {/* Save Session */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Save className="h-5 w-5" />
                  Save Session
                </CardTitle>
                <CardDescription>
                  Manually save a session to the Memory Bank
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSaveSession} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="session-id">Session ID</Label>
                    <Input
                      id="session-id"
                      value={sessionId}
                      onChange={(e) => setSessionId(e.target.value)}
                      placeholder="Enter session ID"
                      disabled={isSaving}
                    />
                  </div>
                  <Button type="submit" disabled={isSaving || !status?.enabled} className="w-full">
                    {isSaving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                    Save to Memory
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* Search Memories */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Search className="h-5 w-5" />
                  Search Memories
                </CardTitle>
                <CardDescription>
                  Query the Memory Bank for relevant memories
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSearch} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="search-query">Search Query</Label>
                    <Input
                      id="search-query"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="What do you want to find?"
                      disabled={isSearching}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="limit">Result Limit</Label>
                    <Input
                      id="limit"
                      type="number"
                      min={1}
                      max={100}
                      value={searchLimit}
                      onChange={(e) => setSearchLimit(Number(e.target.value))}
                      disabled={isSearching}
                    />
                  </div>
                  <Button type="submit" disabled={isSearching || !status?.enabled} className="w-full">
                    {isSearching ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Search className="h-4 w-4 mr-2" />}
                    Search
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>

          {/* Search Results */}
          {searchResults && (
            <Card className="mt-6">
              <CardHeader>
                <CardTitle>Search Results ({searchResults.count})</CardTitle>
                <CardDescription>Query: &quot;{searchResults.query}&quot;</CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-64">
                  {searchResults.memories.length > 0 ? (
                    <div className="space-y-4">
                      {searchResults.memories.map((memory, idx) => (
                        <div key={idx} className="p-3 rounded-lg bg-muted">
                          <pre className="text-xs overflow-auto">{JSON.stringify(memory, null, 2)}</pre>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-center py-8">No memories found</p>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          )}
        </main>
      </div>
    </ProtectedRoute>
  );
}

function StatusItem({ label, value }: { label: string; value: boolean }) {
  return (
    <div className="flex items-center gap-2">
      {value ? (
        <CheckCircle className="h-4 w-4 text-green-500" />
      ) : (
        <XCircle className="h-4 w-4 text-red-500" />
      )}
      <span className="text-sm">{label}</span>
      <Badge variant={value ? 'default' : 'secondary'}>{value ? 'Yes' : 'No'}</Badge>
    </div>
  );
}

