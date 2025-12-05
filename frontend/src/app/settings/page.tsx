'use client';

import { useState, useEffect } from 'react';
import { ProtectedRoute } from '@/components/auth/protected-route';
import { useAuthStore } from '@/stores/auth-store';
import { api, API_URL } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import {
  Settings,
  ArrowLeft,
  RefreshCw,
  User,
  Shield,
  Server,
  CheckCircle,
  XCircle,
  Loader2,
  Key,
} from 'lucide-react';
import Link from 'next/link';

export default function SettingsPage() {
  const { user, refreshToken } = useAuthStore();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isCheckingHealth, setIsCheckingHealth] = useState(false);
  const [healthStatus, setHealthStatus] = useState<'healthy' | 'unhealthy' | 'unknown'>('unknown');

  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    setIsCheckingHealth(true);
    try {
      await api.healthCheck();
      setHealthStatus('healthy');
    } catch {
      setHealthStatus('unhealthy');
    } finally {
      setIsCheckingHealth(false);
    }
  };

  const handleRefreshToken = async () => {
    setIsRefreshing(true);
    try {
      const success = await refreshToken();
      if (success) {
        toast.success('Token refreshed successfully');
      } else {
        toast.error('Failed to refresh token');
      }
    } catch {
      toast.error('Failed to refresh token');
    } finally {
      setIsRefreshing(false);
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
              <Settings className="h-6 w-6 text-primary" />
              <h1 className="text-xl font-semibold">Settings</h1>
            </div>
          </div>
        </header>

        <main className="container mx-auto px-4 py-8 max-w-2xl space-y-6">
          {/* User Profile */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                User Profile
              </CardTitle>
              <CardDescription>Your account information</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Username</p>
                  <p className="font-medium">{user?.username}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">User ID</p>
                  <p className="font-medium font-mono text-sm">{user?.user_id}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Tenant ID</p>
                  <Badge variant="outline">{user?.tenant_id}</Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Permissions */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Permissions
              </CardTitle>
              <CardDescription>Your access permissions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {user?.permissions.map((permission) => (
                  <Badge key={permission} variant="secondary">
                    {permission}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Token Management */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5" />
                Token Management
              </CardTitle>
              <CardDescription>Manage your authentication token</CardDescription>
            </CardHeader>
            <CardContent>
              <Button onClick={handleRefreshToken} disabled={isRefreshing}>
                {isRefreshing ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-2" />
                )}
                Refresh Token
              </Button>
              <p className="text-xs text-muted-foreground mt-2">
                Refresh your JWT token before it expires
              </p>
            </CardContent>
          </Card>

          {/* API Connection */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Server className="h-5 w-5" />
                API Connection
              </CardTitle>
              <CardDescription>Backend API status</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">API URL</p>
                  <p className="font-mono text-sm">{API_URL}</p>
                </div>
                <div className="flex items-center gap-2">
                  {isCheckingHealth ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : healthStatus === 'healthy' ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-500" />
                  )}
                  <Badge variant={healthStatus === 'healthy' ? 'default' : 'destructive'}>
                    {healthStatus === 'healthy' ? 'Connected' : 'Disconnected'}
                  </Badge>
                </div>
              </div>
              <Separator />
              <Button variant="outline" onClick={checkHealth} disabled={isCheckingHealth}>
                {isCheckingHealth ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-2" />
                )}
                Check Connection
              </Button>
            </CardContent>
          </Card>
        </main>
      </div>
    </ProtectedRoute>
  );
}

