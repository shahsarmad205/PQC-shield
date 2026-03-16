import { CopyIcon, Key, PlusIcon, Trash2Icon } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { AppLayout } from '@/components/app-layout';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Dialog,
  DialogClose,
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
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';

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
  const { user } = useAuth();
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

  const handleDeactivate = useCallback(async (id: string) => {
    setDeletingId(id);
    try {
      await api.delete(`/api/v1/keys/${id}`);
      setKeys((prev) => prev.filter((k) => k.id !== id));
    } finally {
      setDeletingId(null);
    }
  }, []);

  const copyKey = useCallback((key: string) => {
    navigator.clipboard.writeText(key);
  }, []);

  if (!user) {
    return (
      <AppLayout>
        <div className="flex min-h-[60vh] items-center justify-center">
          <div className="flex items-center gap-2 text-muted-foreground">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <span>Loading...</span>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="API Keys">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10">
              <Key className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-foreground">API Keys</h1>
              <p className="text-muted-foreground">Manage your API keys for authentication</p>
            </div>
          </div>
          <Dialog open={createOpen} onOpenChange={handleCreateOpenChange}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <PlusIcon className="size-4" />
                Create key
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
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
                  <DialogFooter>
                    <DialogClose asChild>
                      <Button variant="outline">Cancel</Button>
                    </DialogClose>
                    <Button onClick={handleCreateSubmit} disabled={createSubmitting}>
                      {createSubmitting ? 'Creating...' : 'Create key'}
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
                    <p className="rounded-md border border-warning/50 bg-warning/10 px-3 py-2 text-sm text-warning-foreground">
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
                        className="shrink-0 gap-1"
                      >
                        <CopyIcon className="size-4" />
                        Copy
                      </Button>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button onClick={handleCloseAfterCopy}>Done</Button>
                  </DialogFooter>
                </>
              )}
            </DialogContent>
          </Dialog>
        </div>

        {/* Keys Table */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Your API keys</CardTitle>
            <p className="text-sm text-muted-foreground">
              Keys are scoped to your organization. Deactivating a key revokes access immediately.
            </p>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                  <span>Loading...</span>
                </div>
              </div>
            ) : keys.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
                  <Key className="h-6 w-6 text-muted-foreground" />
                </div>
                <p className="text-muted-foreground">No API keys yet. Create one to get started.</p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead className="font-semibold">Name</TableHead>
                      <TableHead className="font-semibold">Prefix</TableHead>
                      <TableHead className="font-semibold">Created</TableHead>
                      <TableHead className="font-semibold">Last used</TableHead>
                      <TableHead className="w-[100px]" />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {keys.map((k) => (
                      <TableRow key={k.id} className={!k.is_active ? 'opacity-60' : 'hover:bg-muted/30'}>
                        <TableCell className="font-medium text-foreground">{k.name}</TableCell>
                        <TableCell className="font-mono text-sm text-muted-foreground">{k.prefix}</TableCell>
                        <TableCell className="text-muted-foreground">{formatDate(k.created_at)}</TableCell>
                        <TableCell className="text-muted-foreground">{formatDate(k.last_used_at)}</TableCell>
                        <TableCell>
                          {k.is_active ? (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="text-destructive hover:text-destructive hover:bg-destructive/10"
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
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}
