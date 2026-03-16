import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckIcon, FileText, Loader2Icon, PlayIcon } from 'lucide-react';
import { useCallback, useState } from 'react';
import { AppLayout } from '@/components/app-layout';
import { Badge, Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui';
import { cn } from '@/lib/utils';

// --- Types (match backend schemas) ---

type CBOMSummary = {
  total_assets: number;
  by_asset_type: Record<string, number>;
  by_quantum_status: { vulnerable?: number; hybrid?: number; quantum_safe?: number };
  by_migration_priority: Record<string, number>;
  critical_count: number;
  last_scan_at: string | null;
  stale_asset_count: number;
};

type ThreatClockResult = {
  years_until_threat: number;
  mosca_threat_year: number;
  current_year: number;
  risk_level: string;
  harvest_now_decrypt_later_exposure: string;
  recommended_urgency: string;
  narrative: string;
  compliance_deadline_risk: Record<string, string>;
  vulnerable_asset_count: number;
  critical_asset_count: number;
  total_asset_count: number;
  estimated_migration_days?: number;
  estimated_migration_years?: number;
  is_at_risk?: boolean;
  migration_velocity_needed?: number;
};

type CryptoFindingRead = {
  id: string;
  algorithm: string;
  usage: string;
  quantum_status: string;
  quantum_risk_label?: string;
};

type AssetRead = {
  id: string;
  display_name: string | null;
  asset_type: string;
  migration_priority: string | null;
  priority_score: number | null;
  findings: CryptoFindingRead[];
  aggregate_quantum_status?: string;
};

type AssetListResponse = {
  items: AssetRead[];
  total: number;
  page: number;
  page_size: number;
};

type MigrationPhase = {
  phase_number: number;
  title: string;
  description: string;
  estimated_effort_days: number;
  compliance_impact: string[];
};

type MigrationPlanResult = {
  summary: string;
  executive_summary: string | null;
  quick_wins: string[];
  phases: MigrationPhase[];
  recommended_algorithms: string[];
  generated_at?: string | null;
};

// Sample payloads for discovery scan (RSA cert, ECDH API, ML-KEM API)
const SAMPLE_PAYLOADS = [
  {
    type: 'certificate',
    source_identifier: 'a1b2c3d4e5f6',
    display_name: 'RSA-2048 TLS Certificate',
    subject: 'CN=api.example.com',
    issuer: 'CN=Example CA',
    key_algorithm: 'RSA',
    key_size_or_oid: '2048',
    findings: [{ algorithm: 'RSA-2048', usage: 'key_exchange', quantum_status: 'vulnerable' }],
  },
  {
    type: 'api_endpoint',
    source_identifier: 'https://api.example.com/v1/keys',
    display_name: 'Key Exchange API',
    host: 'api.example.com',
    base_url: 'https://api.example.com',
    path: '/v1/keys',
    findings: [{ algorithm: 'ECDH-P256', usage: 'key_exchange', quantum_status: 'vulnerable' }],
  },
  {
    type: 'api_endpoint',
    source_identifier: 'https://pqc.example.com/kem',
    display_name: 'PQC KEM API',
    host: 'pqc.example.com',
    base_url: 'https://pqc.example.com',
    path: '/kem',
    findings: [{ algorithm: 'ML-KEM-768', usage: 'key_exchange', quantum_status: 'quantum_safe' }],
  },
];

export default function CBOMPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [scanStep, setScanStep] = useState<string | null>(null);
  const [migrationPlan, setMigrationPlan] = useState<MigrationPlanResult | null>(null);

  const refetchAll = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['cbom-summary'] });
    queryClient.invalidateQueries({ queryKey: ['cbom-threat-clock'] });
    queryClient.invalidateQueries({ queryKey: ['cbom-assets'] });
  }, [queryClient]);

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['cbom-summary'],
    queryFn: async () => {
      const { data } = await api.get<CBOMSummary>('/api/v1/cbom/summary');
      return data;
    },
  });

  const { data: threatClock, isLoading: threatClockLoading } = useQuery({
    queryKey: ['cbom-threat-clock'],
    queryFn: async () => {
      const { data } = await api.get<ThreatClockResult>('/api/v1/cbom/threat-clock');
      return data;
    },
  });

  const { data: assetsData, isLoading: assetsLoading } = useQuery({
    queryKey: ['cbom-assets'],
    queryFn: async () => {
      const { data } = await api.get<AssetListResponse>('/api/v1/cbom/assets?page_size=100');
      return data;
    },
  });

  const runScanMutation = useMutation({
    mutationFn: async () => {
      setScanStep('Starting scan...');
      const { data: run } = await api.post<{ id: string }>('/api/v1/cbom/runs', {
        scope_id: null,
        source: 'dashboard-demo',
      });
      setScanStep('Ingesting assets...');
      await api.post(`/api/v1/cbom/runs/${run.id}/ingest`, { payloads: SAMPLE_PAYLOADS });
      setScanStep('Completing...');
      await api.post(`/api/v1/cbom/runs/${run.id}/finish`);
      setScanStep('Complete');
    },
    onSuccess: () => {
      refetchAll();
      setTimeout(() => setScanStep(null), 2000);
    },
    onError: () => setScanStep(null),
  });

  const migrationPlanMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<MigrationPlanResult>('/api/v1/cbom/migration-plan', {});
      return data;
    },
    onSuccess: (data) => setMigrationPlan(data),
  });

  const vulnerableCount = summary?.by_quantum_status?.vulnerable ?? 0;
  const quantumSafeCount = summary?.by_quantum_status?.quantum_safe ?? 0;

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
    <AppLayout title="CBOM">
      <div className="space-y-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10">
              <FileText className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-foreground">CBOM Security Intelligence</h1>
              <p className="text-muted-foreground">Cryptographic inventory, threat clock, and migration planning.</p>
            </div>
          </div>
          <Button
            type="button"
            onClick={() => runScanMutation.mutate()}
            disabled={runScanMutation.isPending}
            className="gap-2"
          >
            {runScanMutation.isPending ? (
              <>
                <Loader2Icon className="size-4 animate-spin" />
                {scanStep ?? 'Running...'}
              </>
            ) : (
              <>
                <PlayIcon className="size-4" />
                Run Discovery Scan
              </>
            )}
          </Button>
        </div>

        {/* Section 1 — Summary stat cards */}
        <section className="mb-8">
          <h2 className="mb-4 text-lg font-medium">Summary</h2>
          {summaryLoading ? (
            <div className="flex gap-4">
              {[1, 2, 3, 4].map((i) => (
                <Card key={i} className="flex-1">
                  <CardContent className="pt-6">
                    <div className="h-10 animate-pulse rounded bg-muted" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Total Assets</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-semibold">{summary?.total_assets ?? 0}</p>
                </CardContent>
              </Card>
              <Card className={cn((summary?.critical_count ?? 0) > 0 ? 'border-red-500/50 bg-red-500/5' : 'bg-muted/30')}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Critical</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className={cn('text-2xl font-semibold', (summary?.critical_count ?? 0) > 0 && 'text-red-600 dark:text-red-400')}>
                    {summary?.critical_count ?? 0}
                  </p>
                </CardContent>
              </Card>
              <Card className={cn(vulnerableCount > 0 ? 'border-orange-500/50 bg-orange-500/5' : 'bg-muted/30')}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Quantum Vulnerable</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className={cn('text-2xl font-semibold', vulnerableCount > 0 && 'text-orange-600 dark:text-orange-400')}>
                    {vulnerableCount}
                  </p>
                </CardContent>
              </Card>
              <Card className="border-green-500/30 bg-green-500/5">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Quantum Safe</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-semibold text-green-600 dark:text-green-400">{quantumSafeCount}</p>
                </CardContent>
              </Card>
            </div>
          )}
        </section>

        {/* Section 2 — Quantum Threat Clock */}
        <section className="mb-8">
          <h2 className="mb-4 text-lg font-medium">Quantum Threat Clock</h2>
          {threatClockLoading ? (
            <Card>
              <CardContent className="flex items-center justify-center py-12">
                <Loader2Icon className="size-8 animate-spin text-muted-foreground" />
              </CardContent>
            </Card>
          ) : threatClock ? (
            <Card className="overflow-hidden">
              <CardContent className="p-6">
                <div className="mb-4 flex flex-wrap items-start justify-between gap-6">
                  <div>
                    <p className="text-5xl font-bold tabular-nums">{threatClock.years_until_threat}</p>
                    <p className="text-sm text-muted-foreground">years until quantum threat (2030)</p>
                  </div>
                  <div>
                    <Badge
                      variant="secondary"
                      className={cn(
                        threatClock.risk_level === 'critical' && 'bg-red-500/20 text-red-700 dark:text-red-300',
                        threatClock.risk_level === 'high' && 'bg-orange-500/20 text-orange-700 dark:text-orange-300',
                        threatClock.risk_level === 'medium' && 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-300',
                        threatClock.risk_level === 'low' && 'bg-green-500/20 text-green-700 dark:text-green-300'
                      )}
                    >
                      {threatClock.risk_level}
                    </Badge>
                  </div>
                  <div className="space-y-1 text-right text-sm">
                    <p>
                      <span className="font-medium text-muted-foreground">HNDL Exposure:</span>{' '}
                      {threatClock.harvest_now_decrypt_later_exposure}
                    </p>
                    <p>
                      <span className="font-medium text-muted-foreground">Urgency:</span>{' '}
                      {threatClock.recommended_urgency}
                    </p>
                  </div>
                </div>
                <p className="mb-4 italic text-muted-foreground">{threatClock.narrative}</p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(threatClock.compliance_deadline_risk || {}).map(([name, status]) => (
                    <span
                      key={name}
                      className={cn(
                        'rounded-full px-3 py-0.5 text-xs font-medium',
                        status === 'on track' && 'bg-green-500/20 text-green-700 dark:text-green-300',
                        status === 'at risk' && 'bg-red-500/20 text-red-700 dark:text-red-300'
                      )}
                    >
                      {name}: {status}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : null}
        </section>

        {/* Section 3 — Asset inventory table */}
        <section className="mb-8">
          <h2 className="mb-4 text-lg font-medium">Asset Inventory</h2>
          {assetsLoading ? (
            <Card>
              <CardContent className="flex items-center justify-center py-12">
                <Loader2Icon className="size-8 animate-spin text-muted-foreground" />
              </CardContent>
            </Card>
          ) : (
            <Card>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Asset Name</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Algorithm</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Priority</TableHead>
                      <TableHead>Risk Label</TableHead>
                      <TableHead>Score</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(assetsData?.items ?? []).length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                          No assets. Run a discovery scan to populate.
                        </TableCell>
                      </TableRow>
                    ) : (
                      (assetsData?.items ?? []).map((asset) => {
                        const status = asset.aggregate_quantum_status ?? (asset.findings[0]?.quantum_status ?? 'quantum_safe');
                        const finding = asset.findings[0];
                        return (
                          <TableRow key={asset.id}>
                            <TableCell className="font-medium">{asset.display_name ?? asset.id.slice(0, 8)}</TableCell>
                            <TableCell>
                              <span className="rounded-full bg-muted px-2 py-0.5 text-xs">{asset.asset_type}</span>
                            </TableCell>
                            <TableCell className="text-muted-foreground">{finding?.algorithm ?? '—'}</TableCell>
                            <TableCell>
                              <Badge
                                variant="secondary"
                                className={cn(
                                  status === 'vulnerable' && 'bg-red-500/20 text-red-700 dark:text-red-300',
                                  status === 'hybrid' && 'bg-orange-500/20 text-orange-700 dark:text-orange-300',
                                  status === 'quantum_safe' && 'bg-green-500/20 text-green-700 dark:text-green-300'
                                )}
                              >
                                {status === 'vulnerable' ? 'Vulnerable' : status === 'hybrid' ? 'Hybrid' : 'Quantum Safe'}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <Badge
                                variant="secondary"
                                className={cn(
                                  asset.migration_priority === 'critical' && 'bg-red-500/20 text-red-700 dark:text-red-300',
                                  asset.migration_priority === 'high' && 'bg-orange-500/20 text-orange-700 dark:text-orange-300',
                                  asset.migration_priority === 'medium' && 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-300',
                                  (asset.migration_priority === 'low' || !asset.migration_priority) && 'bg-muted text-muted-foreground'
                                )}
                              >
                                {asset.migration_priority ?? 'low'}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-muted-foreground text-sm">
                              {finding?.quantum_risk_label ?? '—'}
                            </TableCell>
                            <TableCell>{asset.priority_score ?? '—'}</TableCell>
                          </TableRow>
                        );
                      })
                    )}
                  </TableBody>
                </Table>
              </div>
            </Card>
          )}
        </section>

        {/* Section 4 — Migration Planner */}
        <section>
          <h2 className="mb-4 text-lg font-medium">Migration Planner</h2>
          {!migrationPlan ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Button
                  type="button"
                  onClick={() => migrationPlanMutation.mutate()}
                  disabled={migrationPlanMutation.isPending}
                  className="gap-2"
                >
                  {migrationPlanMutation.isPending ? (
                    <>
                      <Loader2Icon className="size-4 animate-spin" />
                      Analyzing cryptographic inventory...
                    </>
                  ) : (
                    'Generate AI Migration Plan'
                  )}
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-6">
              {migrationPlan.executive_summary && (
                <div className="rounded-lg border border-blue-500/30 bg-blue-500/10 p-4 text-sm">
                  {migrationPlan.executive_summary}
                </div>
              )}
              {migrationPlan.quick_wins?.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Quick wins</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {migrationPlan.quick_wins.map((win, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm">
                          <CheckIcon className="mt-0.5 size-4 shrink-0 text-green-600 dark:text-green-400" />
                          {win}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
              {migrationPlan.phases?.map((phase) => (
                <Card key={phase.phase_number}>
                  <CardHeader>
                    <CardTitle className="text-base">
                      Phase {phase.phase_number} — {phase.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm text-muted-foreground">{phase.description}</p>
                    <p className="text-sm font-medium">{phase.estimated_effort_days} days estimated</p>
                    {phase.compliance_impact?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {phase.compliance_impact.map((c) => (
                          <span key={c} className="rounded-full bg-muted px-2.5 py-0.5 text-xs">
                            {c}
                          </span>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
              {migrationPlan.recommended_algorithms?.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Recommended algorithms</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-1.5">
                      {migrationPlan.recommended_algorithms.map((alg) => (
                        <span key={alg} className="rounded-full bg-green-500/20 px-2.5 py-0.5 text-xs text-green-700 dark:text-green-300">
                          {alg}
                        </span>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </section>
      </div>
    </AppLayout>
  );
}
