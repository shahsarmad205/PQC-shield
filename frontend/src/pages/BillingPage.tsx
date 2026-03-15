import { CheckIcon } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { cn } from '@/lib/utils';

type BillingUsage = {
  plan: string;
  ops_used_this_month: number;
  monthly_quota: number;
};

const PLANS = [
  {
    id: 'starter',
    name: 'Starter',
    price: '$0',
    period: '/month',
    description: 'For small teams and experiments',
    features: ['10,000 ops/month', 'KEM & DSA APIs', 'API keys', 'Compliance report'],
  },
  {
    id: 'pro',
    name: 'Pro',
    price: '$49',
    period: '/month',
    description: 'For growing teams',
    features: ['100,000 ops/month', 'Everything in Starter', 'Priority support', 'SLA 99.9%'],
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    description: 'For large organizations',
    features: ['1,000,000+ ops/month', 'Everything in Pro', 'Dedicated support', 'Custom SLA'],
  },
] as const;

export default function BillingPage() {
  const { user, logout } = useAuth();
  const [usage, setUsage] = useState<BillingUsage | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgradingPlan, setUpgradingPlan] = useState<string | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchUsage = useCallback(async () => {
    try {
      const { data } = await api.get<BillingUsage>('/api/v1/billing');
      setUsage(data);
    } catch {
      setUsage(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsage();
  }, [fetchUsage]);

  const handleUpgrade = useCallback(async (planId: string) => {
    setUpgradingPlan(planId);
    setError(null);
    try {
      const { data } = await api.post<{ url: string }>('/api/v1/billing/create-checkout-session', {
        plan: planId,
      });
      if (data?.url) {
        window.location.href = data.url;
        return;
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to start checkout';
      setError(String(msg));
    } finally {
      setUpgradingPlan(null);
    }
  }, []);

  const handleManageBilling = useCallback(async () => {
    setPortalLoading(true);
    setError(null);
    try {
      const { data } = await api.post<{ url: string }>('/api/v1/billing/create-portal-session');
      if (data?.url) {
        window.location.href = data.url;
        return;
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to open billing portal';
      setError(String(msg));
    } finally {
      setPortalLoading(false);
    }
  }, []);

  const currentPlanId = usage?.plan?.toLowerCase() ?? 'starter';
  const progressPercent =
    usage && usage.monthly_quota > 0
      ? Math.min(100, (usage.ops_used_this_month / usage.monthly_quota) * 100)
      : 0;

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
            <Link to="/api-keys" className="text-sm font-medium text-muted-foreground hover:text-foreground">
              API Keys
            </Link>
            <Link to="/cbom" className="text-sm font-medium text-muted-foreground hover:text-foreground">
              CBOM
            </Link>
            <Link to="/billing" className="text-sm font-medium text-foreground">
              Billing
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

      <main className="mx-auto max-w-5xl px-4 py-8">
        <h1 className="mb-2 text-2xl font-semibold">Billing</h1>
        <p className="mb-8 text-muted-foreground">
          Manage your plan and usage.
        </p>

        {error && (
          <div className="mb-6 rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}

        {/* Current plan & usage */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Current plan</CardTitle>
            <p className="text-sm text-muted-foreground">
              Usage resets each billing period.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            {loading ? (
              <p className="text-muted-foreground">Loading…</p>
            ) : (
              <>
                <div className="flex flex-wrap items-center gap-4">
                  <span className="text-lg font-medium capitalize">
                    {usage?.plan ?? 'Starter'}
                  </span>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleManageBilling}
                    disabled={portalLoading}
                  >
                    {portalLoading ? 'Opening…' : 'Manage billing'}
                  </Button>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Ops this month</span>
                    <span>
                      {(usage?.ops_used_this_month ?? 0).toLocaleString()} / {(usage?.monthly_quota ?? 0).toLocaleString()}
                    </span>
                  </div>
                  <div
                    className="h-2 w-full overflow-hidden rounded-full bg-muted"
                    role="progressbar"
                    aria-valuenow={progressPercent}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  >
                    <div
                      className={cn(
                        'h-full rounded-full transition-all',
                        progressPercent >= 100 ? 'bg-destructive' : 'bg-primary'
                      )}
                      style={{ width: `${progressPercent}%` }}
                    />
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Plan cards */}
        <div className="grid gap-6 sm:grid-cols-3">
          {PLANS.map((plan) => {
            const isCurrent = currentPlanId === plan.id;
            return (
              <Card
                key={plan.id}
                className={cn(
                  'flex flex-col',
                  isCurrent && 'ring-2 ring-primary'
                )}
              >
                <CardHeader>
                  {isCurrent && (
                    <span className="mb-1 inline-block w-fit rounded-full bg-primary/15 px-2.5 py-0.5 text-xs font-medium text-primary">
                      Current plan
                    </span>
                  )}
                  <CardTitle className="text-lg">{plan.name}</CardTitle>
                  <p className="text-sm text-muted-foreground">{plan.description}</p>
                  <p className="mt-2 text-2xl font-semibold">
                    {plan.price}
                    <span className="text-sm font-normal text-muted-foreground">{plan.period}</span>
                  </p>
                </CardHeader>
                <CardContent className="flex flex-1 flex-col gap-4">
                  <ul className="space-y-2 text-sm">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex items-center gap-2">
                        <CheckIcon className="size-4 shrink-0 text-primary" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  <div className="mt-auto pt-4">
                    <Button
                      type="button"
                      variant={isCurrent ? 'outline' : 'default'}
                      className="w-full"
                      disabled={isCurrent || upgradingPlan !== null}
                      onClick={() => handleUpgrade(plan.id)}
                    >
                      {isCurrent
                        ? 'Current plan'
                        : upgradingPlan === plan.id
                          ? 'Redirecting…'
                          : 'Upgrade'}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </main>
    </div>
  );
}
