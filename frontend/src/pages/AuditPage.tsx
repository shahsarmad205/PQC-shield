import { ScrollText } from 'lucide-react';
import { AppLayout } from '@/components/app-layout';
import AuditTable from '@/components/AuditTable';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { useAuth } from '@/lib/auth';

export default function AuditPage() {
  const { user } = useAuth();

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
    <AppLayout title="Audit Log">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10">
            <ScrollText className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-foreground">Audit Log</h1>
            <p className="text-muted-foreground">View and export API operation history for your organization</p>
          </div>
        </div>

        {/* Audit Table */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Audit Entries</CardTitle>
            <p className="text-sm text-muted-foreground">
              All API operations are logged for compliance and security purposes.
            </p>
          </CardHeader>
          <CardContent>
            <AuditTable />
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}
