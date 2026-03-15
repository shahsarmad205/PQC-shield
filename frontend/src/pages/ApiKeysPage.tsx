import { CopyIcon, PlusIcon, Trash2Icon } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  Input,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui';

type KeyItem = {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  last_used_at: string | null;
  is_active: boolean;
};

type CreateResponse = {
  id: string;
  name: string;
  key: string;
  prefix: string;
  created_at: string;
};

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function ApiKeysPage() {
  const { user, logout } = useAuth();
  const [keys, setKeys] = useState<KeyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createdKey, setCreatedKey] = useState<CreateResponse | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchKeys = useCallback(async () => {
    try {
      const { data } = await api.get<KeyItem[]>('/api/v1/keys');
      setKeys(data);
    } catch {
      setKeys([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  const handleCreateSubmit = useCallback(async () => {
    const name = createName.trim();
    if (!name) {
      setCreateError('Name is required');
      return;
    }
    setCreateError(null);
    setCreateSubmitting(true);
    try {
      const { data } = await api.post<CreateResponse>('/api/v1/keys', { name });
      setCreatedKey(data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to create key';
      setCreateError(String(msg));
    } finally {
      setCreateSubmitting(false);
    }
  }, [createName]);

  const handleCreateOpenChange = useCallback((open: boolean) => {
    setCreateOpen(open);
    if (!open) {
      setCreateName('');
      setCreateError(null);
      setCreatedKey(null);
    }
  }, []);

  const handleCloseAfterCopy = useCallback(() => {
    setCreateOpen(false);
    setCreatedKey(null);
    setCreateName('');
    fetchKeys();
  }, [fetchKeys]);

  const handleDeactivate = useCallback(
    async (id: string) => {
      setDeletingId(id);
      try {
        await api.delete(`/api/v1/keys/${id}`);
        setKeys((prev) => prev.filter((k) => k.id !== id));
      } finally {
        setDeletingId(null);
      }
    },
    []
  );

  const copyKey = useCallback((key: string) => {
    navigator.clipboard.writeText(key);
  }, []);

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-6">
            <Link to="/dashboard" className="text-xl font-semibold hover:opacity-90">
              PQC Shield
            </Link>
            <Link to="/compliance" className="text-sm font-medium text-muted-foreground hover:text-foreground">
              Compliance
            </Link>
            <Link to="/api-keys" className="text-sm font-medium text-foreground">
              API Keys
            </Link>
            <Link to="/billing" className="text-sm font-medium text-muted-foreground hover:text-foreground">
              Billing
            </Link>
            <Link to="/cbom" className="text-sm font-medium text-muted-foreground hover:text-foreground">
              CBOM
            </Link>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{user.email}</span>
            <Button type="button" variant="ghost" size="sm" onClick={logout}>
              Sign out
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-semibold">API Keys</h1>
          <Dialog open={createOpen} onOpenChange={handleCreateOpenChange}>
            <DialogTrigger asChild>
              <Button>
                <PlusIcon className="mr-2 size-4" />
                Create key
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md" showCloseButton={!createdKey}>
              {!createdKey ? (
                <>
                  <DialogHeader>
                    <DialogTitle>Create API key</DialogTitle>
                    <DialogDescription>
                      Give this key a name so you can identify it later. The full key will only be shown once.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="grid gap-4 py-4">
                    <div className="grid gap-2">
                      <label htmlFor="key-name" className="text-sm font-medium">
                        Name
                      </label>
                      <Input
                        id="key-name"
                        placeholder="e.g. Production"
                        value={createName}
                        onChange={(e) => setCreateName(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleCreateSubmit()}
                      />
                    </div>
                    {createError && (
                      <p className="text-sm text-destructive" role="alert">
                        {createError}
                      </p>
                    )}
                  </div>
                  <DialogFooter showCloseButton>
                    <Button onClick={handleCreateSubmit} disabled={createSubmitting}>
                      {createSubmitting ? 'Creating…' : 'Create key'}
                    </Button>
                  </DialogFooter>
                </>
              ) : (
                <>
                  <DialogHeader>
                    <DialogTitle>Key created</DialogTitle>
                    <DialogDescription>
                      Copy the key below and store it securely. This key will not be shown again.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="grid gap-4 py-4">
                    <p className="rounded-md border border-amber-500/50 bg-amber-500/10 px-3 py-2 text-sm text-amber-800 dark:text-amber-200">
                      This key will not be shown again.
                    </p>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 truncate rounded-md border bg-muted/50 px-3 py-2 text-sm font-mono">
                        {createdKey.key}
                      </code>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => copyKey(createdKey.key)}
                        className="shrink-0"
                      >
                        <CopyIcon className="mr-1 size-4" />
                        Copy
                      </Button>
                    </div>
                  </div>
                  <DialogFooter showCloseButton>
                    <Button onClick={handleCloseAfterCopy}>Done</Button>
                  </DialogFooter>
                </>
              )}
            </DialogContent>
          </Dialog>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Your API keys</CardTitle>
            <p className="text-sm text-muted-foreground">
              Keys are scoped to your organization. Deactivating a key revokes access immediately.
            </p>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-muted-foreground">Loading…</p>
            ) : keys.length === 0 ? (
              <p className="text-muted-foreground">No API keys yet. Create one to get started.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Prefix</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Last used</TableHead>
                    <TableHead className="w-[100px]" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {keys.map((k) => (
                    <TableRow key={k.id} className={!k.is_active ? 'opacity-60' : ''}>
                      <TableCell className="font-medium">{k.name}</TableCell>
                      <TableCell className="font-mono text-muted-foreground">{k.prefix}</TableCell>
                      <TableCell>{formatDate(k.created_at)}</TableCell>
                      <TableCell>{formatDate(k.last_used_at)}</TableCell>
                      <TableCell>
                        {k.is_active ? (
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="text-destructive hover:text-destructive"
                            disabled={deletingId === k.id}
                            onClick={() => handleDeactivate(k.id)}
                          >
                            <Trash2Icon className="size-4" />
                            <span className="sr-only">Deactivate</span>
                          </Button>
                        ) : (
                          <span className="text-sm text-muted-foreground">Deactivated</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
