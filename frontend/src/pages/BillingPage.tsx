import { CheckIcon, CreditCard, Sparkles } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { AppLayout } from '@/components/app-layout';
import { Badge, Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
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
    popular: false,
  },
  {
    id: 'pro',
    name: 'Pro',
    price: '$49',
    period: '/month',
    description: 'For growing teams',
    features: ['100,000 ops/month', 'Everything in Starter', 'Priority support', 'SLA 99.9%'],
    popular: true,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    description: 'For large organizations',
    features: ['1,000,000+ ops/month', 'Everything in Pro', 'Dedicated support', 'Custom SLA'],
    popular: false,
  },
] as const;

export default function BillingPage() {
  const { user } = useAuth();
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
    <AppLayout title="Billing">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10">
            <CreditCard className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-foreground">Billing</h1>
            <p className="text-muted-foreground">Manage your plan and usage</p>
          </div>
        </div>

        {error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}

        {/* Current plan & usage */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Current Plan</CardTitle>
            <p className="text-sm text-muted-foreground">
              Usage resets each billing period.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            {loading ? (
              <div className="flex items-center justify-center py-4">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                  <span>Loading...</span>
                </div>
              </div>
            ) : (
              <>
                <div className="flex flex-wrap items-center gap-4">
                  <Badge variant="secondary" className="text-base font-medium capitalize px-3 py-1">
                    {usage?.plan ?? 'Starter'}
                  </Badge>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleManageBilling}
                    disabled={portalLoading}
                  >
                    {portalLoading ? 'Opening...' : 'Manage billing'}
                  </Button>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Operations this month</span>
                    <span className="font-medium text-foreground">
                      {(usage?.ops_used_this_month ?? 0).toLocaleString()} / {(usage?.monthly_quota ?? 0).toLocaleString()}
                    </span>
                  </div>
                  <div
                    className="h-2.5 w-full overflow-hidden rounded-full bg-muted"
                    role="progressbar"
                    aria-valuenow={progressPercent}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  >
                    <div
                      className={cn(
                        'h-full rounded-full transition-all duration-500',
                        progressPercent >= 90 ? 'bg-destructive' : progressPercent >= 70 ? 'bg-warning' : 'bg-primary'
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
        <div>
          <h2 className="mb-4 text-lg font-semibold text-foreground">Available Plans</h2>
          <div className="grid gap-6 sm:grid-cols-3">
            {PLANS.map((plan) => {
              const isCurrent = currentPlanId === plan.id;
              return (
                <Card
                  key={plan.id}
                  className={cn(
                    'relative flex flex-col overflow-hidden transition-shadow hover:shadow-lg',
                    isCurrent && 'ring-2 ring-primary',
                    plan.popular && !isCurrent && 'ring-1 ring-primary/50'
                  )}
                >
                  {plan.popular && !isCurrent && (
                    <div className="absolute right-4 top-4">
                      <Badge className="gap-1 bg-primary text-primary-foreground">
                        <Sparkles className="h-3 w-3" />
                        Popular
                      </Badge>
                    </div>
                  )}
                  <CardHeader>
                    {isCurrent && (
                      <Badge variant="secondary" className="mb-2 w-fit">
                        Current plan
                      </Badge>
                    )}
                    <CardTitle className="text-xl">{plan.name}</CardTitle>
                    <p className="text-sm text-muted-foreground">{plan.description}</p>
                    <p className="mt-3 text-3xl font-bold text-foreground">
                      {plan.price}
                      <span className="text-base font-normal text-muted-foreground">{plan.period}</span>
                    </p>
                  </CardHeader>
                  <CardContent className="flex flex-1 flex-col gap-4">
                    <ul className="space-y-3 text-sm">
                      {plan.features.map((feature) => (
                        <li key={feature} className="flex items-center gap-2">
                          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10">
                            <CheckIcon className="h-3 w-3 text-primary" />
                          </div>
                          <span className="text-foreground">{feature}</span>
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
                            ? 'Redirecting...'
                            : 'Upgrade'}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
