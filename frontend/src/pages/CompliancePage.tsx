import { FileDownIcon, ShieldCheck } from 'lucide-react';
import { useCallback, useState } from 'react';
import { AppLayout } from '@/components/app-layout';
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
  const { user } = useAuth();
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
    <AppLayout title="Compliance">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10">
              <ShieldCheck className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-foreground">Compliance Dashboard</h1>
              <p className="text-muted-foreground">NIST-standardized post-quantum cryptographic algorithms</p>
            </div>
          </div>
          <Button onClick={handleExportPdf} disabled={exporting} className="gap-2">
            <FileDownIcon className="size-4" />
            {exporting ? 'Exporting...' : 'Export PDF'}
          </Button>
        </div>

        {/* Algorithm Table */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">NIST-Standardized Algorithms</CardTitle>
            <p className="text-sm text-muted-foreground">
              Algorithms supported by this app (ML-KEM, ML-DSA, SLH-DSA) with FIPS standards and key sizes.
            </p>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50">
                    <TableHead className="font-semibold">Algorithm</TableHead>
                    <TableHead className="font-semibold">FIPS Standard</TableHead>
                    <TableHead className="font-semibold">Security Level</TableHead>
                    <TableHead className="font-semibold">Key Size (pub)</TableHead>
                    <TableHead className="font-semibold">Key Size (sec)</TableHead>
                    <TableHead className="font-semibold">Signature/Ciphertext</TableHead>
                    <TableHead className="font-semibold">Quantum-Safe</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {COMPLIANCE_DATA.map((row) => (
                    <TableRow key={row.algorithm} className="hover:bg-muted/30">
                      <TableCell className="font-medium text-foreground">{row.algorithm}</TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="font-mono text-xs">
                          {row.fips}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge 
                          variant="outline" 
                          className={
                            row.securityLevel === '5' 
                              ? 'border-success/50 bg-success/10 text-success' 
                              : row.securityLevel === '3'
                              ? 'border-primary/50 bg-primary/10 text-primary'
                              : 'border-muted-foreground/50'
                          }
                        >
                          Level {row.securityLevel}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-sm text-muted-foreground">{row.keySizePub}</TableCell>
                      <TableCell className="font-mono text-sm text-muted-foreground">{row.keySizeSec}</TableCell>
                      <TableCell className="font-mono text-sm text-muted-foreground">{row.sigOrCtSize}</TableCell>
                      <TableCell>
                        <Badge className="bg-success/20 text-success hover:bg-success/30 border-0">
                          Yes
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}
