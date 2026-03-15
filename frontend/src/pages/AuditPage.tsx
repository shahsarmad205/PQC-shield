import { Link } from 'react-router-dom';
import AuditTable from '@/components/AuditTable';
import { Button } from '@/components/ui';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { useAuth } from '@/lib/auth';

export default function AuditPage() {
  const { user, logout } = useAuth();

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
            <Link to="/billing" className="text-sm font-medium text-muted-foreground hover:text-foreground">
              Billing
            </Link>
            <Link to="/cbom" className="text-sm font-medium text-muted-foreground hover:text-foreground">
              CBOM
            </Link>
            <Link to="/audit" className="text-sm font-medium text-foreground">
              Audit
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
        <h1 className="mb-2 text-2xl font-semibold">Audit log</h1>
        <p className="mb-6 text-muted-foreground">
          View and export API operation history for your organization.
        </p>
        <Card>
          <CardHeader>
            <CardTitle>Audit entries</CardTitle>
          </CardHeader>
          <CardContent>
            <AuditTable />
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
