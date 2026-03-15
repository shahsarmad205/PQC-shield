import { CopyIcon } from 'lucide-react';
import { useCallback, useState } from 'react';
import { Link } from 'react-router-dom';
import EncryptPanel from '@/components/EncryptPanel';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui';
import { useAuth } from '@/lib/auth';
import { cn } from '@/lib/utils';

const DSA_ALGORITHMS = ['ML-DSA-44', 'ML-DSA-65', 'ML-DSA-87'] as const;

function ResultBlock({
  value,
  label,
  className,
}: {
  value: string;
  label: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);
  const copy = useCallback(() => {
    if (!value) return;
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [value]);

  if (!value) return null;

  return (
    <div className={cn('space-y-1.5', className)}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-muted-foreground">{label}</span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={copy}
          className="gap-1.5"
        >
          <CopyIcon className="size-3.5" />
          {copied ? 'Copied' : 'Copy'}
        </Button>
      </div>
      <pre className="rounded-lg border border-input bg-muted/50 p-3 text-xs font-mono overflow-x-auto whitespace-pre-wrap break-all">
        {value}
      </pre>
    </div>
  );
}

export default function DashboardPage() {
  const { user, logout } = useAuth();

  const [opsUsed] = useState(1234);
  const [opsRemaining] = useState(8766);
  const [plan] = useState('Free');

  const [dsaAlg, setDsaAlg] = useState<string>(DSA_ALGORITHMS[0]);
  const [dsaMessage, setDsaMessage] = useState('');
  const [dsaSignature, setDsaSignature] = useState('');

  const handleDsaSubmit = useCallback(() => {
    setDsaSignature(
      btoa('mock-signature-' + dsaAlg + '-' + dsaMessage.slice(0, 16) + '-' + Date.now())
    );
  }, [dsaAlg, dsaMessage]);

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
            <h1 className="text-xl font-semibold">PQC Shield</h1>
            <Link to="/compliance" className="text-sm font-medium text-muted-foreground hover:text-foreground">
              Compliance
            </Link>
            <Link to="/api-keys" className="text-sm font-medium text-muted-foreground hover:text-foreground">
              API Keys
            </Link>
            <Link to="/billing" className="text-sm font-medium text-muted-foreground hover:text-foreground">
              Billing
            </Link>
            <Link to="/audit" className="text-sm font-medium text-muted-foreground hover:text-foreground">
              Audit
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
        <h2 className="mb-2 text-2xl font-medium">
          Welcome, {user.full_name}
        </h2>
        {user.organization && (
          <p className="mb-8 text-muted-foreground">
            {user.organization.name}
          </p>
        )}

        <div className="mb-8 grid gap-4 sm:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Ops used this month
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">{opsUsed.toLocaleString()}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Ops remaining
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">{opsRemaining.toLocaleString()}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Current plan
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">{plan}</p>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="kem" className="space-y-4">
          <TabsList className="grid w-full max-w-sm grid-cols-2">
            <TabsTrigger value="kem">Encrypt (KEM)</TabsTrigger>
            <TabsTrigger value="dsa">Sign (DSA)</TabsTrigger>
          </TabsList>

          <TabsContent value="kem" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Key encapsulation (KEM)</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Generate a keypair or encapsulate a secret with a recipient public key.
                </p>
              </CardHeader>
              <CardContent>
                <EncryptPanel />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="dsa" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Sign (DSA)</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Select algorithm, enter message, then sign.
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Algorithm</label>
                  <Select
                    value={dsaAlg}
                    onValueChange={(v) => setDsaAlg(v ?? DSA_ALGORITHMS[0])}
                  >
                    <SelectTrigger className="w-full max-w-xs">
                      <SelectValue placeholder="Select algorithm" />
                    </SelectTrigger>
                    <SelectContent>
                      {DSA_ALGORITHMS.map((alg) => (
                        <SelectItem key={alg} value={alg}>
                          {alg}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Message</label>
                  <Input
                    placeholder="Message to sign"
                    value={dsaMessage}
                    onChange={(e) => setDsaMessage(e.target.value)}
                    className="font-mono text-sm"
                  />
                </div>
                <Button onClick={handleDsaSubmit}>Sign</Button>
                <div className="rounded-lg border bg-muted/30 p-4">
                  <ResultBlock
                    label="Signature (base64)"
                    value={dsaSignature}
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
