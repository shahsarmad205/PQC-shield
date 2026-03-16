import { Activity, CopyIcon, TrendingUp, Zap } from 'lucide-react';
import { useCallback, useState } from 'react';
import { AppLayout } from '@/components/app-layout';
import EncryptPanel from '@/components/EncryptPanel';
import {
  Badge,
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

function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  trendLabel,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  trend?: 'up' | 'down' | 'neutral';
  trendLabel?: string;
}) {
  return (
    <Card className="relative overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
          <Icon className="h-4 w-4 text-primary" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-foreground">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </div>
        {trendLabel && (
          <p className={cn(
            'mt-1 flex items-center gap-1 text-xs',
            trend === 'up' && 'text-success',
            trend === 'down' && 'text-destructive',
            trend === 'neutral' && 'text-muted-foreground'
          )}>
            {trend === 'up' && <TrendingUp className="h-3 w-3" />}
            {trendLabel}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();

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
    <AppLayout title="Dashboard">
      <div className="space-y-8">
        {/* Welcome section */}
        <div className="flex flex-col gap-1">
          <h2 className="text-2xl font-semibold text-foreground">
            Welcome back, {user.full_name}
          </h2>
          {user.organization && (
            <p className="text-muted-foreground">
              {user.organization.name}
            </p>
          )}
        </div>

        {/* Stats grid */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard
            title="Operations Used"
            value={opsUsed}
            icon={Activity}
            trend="up"
            trendLabel="+12% from last month"
          />
          <StatCard
            title="Operations Remaining"
            value={opsRemaining}
            icon={Zap}
            trend="neutral"
            trendLabel="Resets in 16 days"
          />
          <StatCard
            title="Current Plan"
            value={plan}
            icon={TrendingUp}
            trendLabel="Upgrade for more operations"
          />
        </div>

        {/* Crypto operations */}
        <Tabs defaultValue="kem" className="space-y-6">
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="kem" className="gap-2">
              <span>Encrypt (KEM)</span>
            </TabsTrigger>
            <TabsTrigger value="dsa" className="gap-2">
              <span>Sign (DSA)</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="kem" className="space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <Zap className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">Key Encapsulation (KEM)</CardTitle>
                    <p className="text-sm text-muted-foreground">
                      Generate a keypair or encapsulate a secret with a recipient public key.
                    </p>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <EncryptPanel />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="dsa" className="space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10">
                    <Activity className="h-5 w-5 text-accent" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">Digital Signatures (DSA)</CardTitle>
                    <p className="text-sm text-muted-foreground">
                      Select algorithm, enter message, then sign.
                    </p>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-foreground">Algorithm</label>
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
                          <span className="flex items-center gap-2">
                            {alg}
                            <Badge variant="secondary" className="text-[10px]">
                              NIST
                            </Badge>
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-foreground">Message</label>
                  <Input
                    placeholder="Message to sign"
                    value={dsaMessage}
                    onChange={(e) => setDsaMessage(e.target.value)}
                    className="font-mono text-sm"
                  />
                </div>
                <Button onClick={handleDsaSubmit} className="gap-2">
                  Sign Message
                </Button>
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
      </div>
    </AppLayout>
  );
}
