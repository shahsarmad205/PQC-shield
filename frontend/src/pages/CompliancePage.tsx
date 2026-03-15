import { FileDownIcon } from 'lucide-react';
import { useCallback, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';

type AlgorithmRow = {
  algorithm: string;
  fips: string;
  securityLevel: string;
  keySizePub: string;
  keySizeSec: string;
  sigOrCtSize: string;
};

const COMPLIANCE_DATA: AlgorithmRow[] = [
  { algorithm: 'ML-KEM-512', fips: 'FIPS 203', securityLevel: '1', keySizePub: '800 B', keySizeSec: '1,632 B', sigOrCtSize: '768 B (ciphertext)' },
  { algorithm: 'ML-KEM-768', fips: 'FIPS 203', securityLevel: '3', keySizePub: '1,184 B', keySizeSec: '2,400 B', sigOrCtSize: '1,088 B (ciphertext)' },
  { algorithm: 'ML-KEM-1024', fips: 'FIPS 203', securityLevel: '5', keySizePub: '1,568 B', keySizeSec: '3,168 B', sigOrCtSize: '1,568 B (ciphertext)' },
  { algorithm: 'ML-DSA-44', fips: 'FIPS 204', securityLevel: '1', keySizePub: '1,312 B', keySizeSec: '2,528 B', sigOrCtSize: '2,420 B (signature)' },
  { algorithm: 'ML-DSA-65', fips: 'FIPS 204', securityLevel: '3', keySizePub: '1,952 B', keySizeSec: '4,032 B', sigOrCtSize: '3,309 B (signature)' },
  { algorithm: 'ML-DSA-87', fips: 'FIPS 204', securityLevel: '5', keySizePub: '2,592 B', keySizeSec: '4,896 B', sigOrCtSize: '4,627 B (signature)' },
  { algorithm: 'SLH-DSA-SHA2-128f', fips: 'FIPS 205', securityLevel: '1', keySizePub: '32 B', keySizeSec: '64 B', sigOrCtSize: '~17,088 B (signature)' },
  { algorithm: 'SLH-DSA-SHA2-128s', fips: 'FIPS 205', securityLevel: '1', keySizePub: '32 B', keySizeSec: '64 B', sigOrCtSize: '~7,856 B (signature)' },
  { algorithm: 'SLH-DSA-SHA2-192f', fips: 'FIPS 205', securityLevel: '3', keySizePub: '48 B', keySizeSec: '96 B', sigOrCtSize: '~35,664 B (signature)' },
  { algorithm: 'SLH-DSA-SHA2-192s', fips: 'FIPS 205', securityLevel: '3', keySizePub: '48 B', keySizeSec: '96 B', sigOrCtSize: '~16,224 B (signature)' },
  { algorithm: 'SLH-DSA-SHA2-256f', fips: 'FIPS 205', securityLevel: '5', keySizePub: '64 B', keySizeSec: '128 B', sigOrCtSize: '~49,856 B (signature)' },
  { algorithm: 'SLH-DSA-SHA2-256s', fips: 'FIPS 205', securityLevel: '5', keySizePub: '64 B', keySizeSec: '128 B', sigOrCtSize: '~29,792 B (signature)' },
];

export default function CompliancePage() {
  const { user, logout } = useAuth();
  const [exporting, setExporting] = useState(false);

  const handleExportPdf = useCallback(async () => {
    setExporting(true);
    try {
      const { data } = await api.get<Blob>('/api/v1/compliance/report', {
        responseType: 'blob',
      });
      const url = URL.createObjectURL(data);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'pqc-shield-compliance-report.pdf';
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
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
            <Link to="/compliance" className="text-sm font-medium text-foreground">
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
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{user.email}</span>
            <Button type="button" variant="ghost" size="sm" onClick={logout}>
              Sign out
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8 space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-2xl font-semibold">Compliance</h2>
        <Button onClick={handleExportPdf} disabled={exporting} className="gap-2">
          <FileDownIcon className="size-4" />
          {exporting ? 'Exporting…' : 'Export PDF'}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>NIST-standardized algorithms</CardTitle>
          <p className="text-sm text-muted-foreground">
            Algorithms supported by this app (ML-KEM, ML-DSA, SLH-DSA) with FIPS standards and key sizes.
          </p>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Algorithm</TableHead>
                <TableHead>FIPS standard</TableHead>
                <TableHead>Security level</TableHead>
                <TableHead>Key size (pub)</TableHead>
                <TableHead>Key size (sec)</TableHead>
                <TableHead>Signature/ciphertext size</TableHead>
                <TableHead>Quantum-safe</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {COMPLIANCE_DATA.map((row) => (
                <TableRow key={row.algorithm}>
                  <TableCell className="font-medium">{row.algorithm}</TableCell>
                  <TableCell>{row.fips}</TableCell>
                  <TableCell>{row.securityLevel}</TableCell>
                  <TableCell>{row.keySizePub}</TableCell>
                  <TableCell>{row.keySizeSec}</TableCell>
                  <TableCell>{row.sigOrCtSize}</TableCell>
                  <TableCell>
                    <Badge variant="secondary">Yes</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      </main>
    </div>
  );
}
