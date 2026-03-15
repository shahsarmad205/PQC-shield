import { useMutation } from '@tanstack/react-query';
import { CopyIcon } from 'lucide-react';
import { useCallback, useState } from 'react';
import {
  Badge,
  Button,
  Input,
  RadioGroup,
  RadioGroupItem,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

const KEM_OPTIONS = [
  { value: 'ML-KEM-512', level: 1 },
  { value: 'ML-KEM-768', level: 3 },
  { value: 'ML-KEM-1024', level: 5 },
] as const;

type KemMode = 'keygen' | 'encapsulate';

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
      <pre className="overflow-x-auto whitespace-pre-wrap break-all rounded-lg border border-input bg-muted/50 p-3 text-xs font-mono">
        {value}
      </pre>
    </div>
  );
}

export default function EncryptPanel() {
  const [mode, setMode] = useState<KemMode>('keygen');
  const [algorithm, setAlgorithm] = useState<string>(KEM_OPTIONS[0].value);
  const [publicKeyInput, setPublicKeyInput] = useState('');

  const [keygenResult, setKeygenResult] = useState<{
    public_key?: string;
    secret_key?: string;
  }>({});
  const [encapResult, setEncapResult] = useState<{
    ciphertext?: string;
    shared_secret?: string;
  }>({});

  const keygenMutation = useMutation({
    mutationFn: async (alg: string) => {
      const { data } = await api.post<{ public_key: string; secret_key: string }>(
        '/api/v1/crypto/kem/keygen',
        { algorithm: alg }
      );
      return data;
    },
    onSuccess: (data) => {
      setKeygenResult({ public_key: data.public_key, secret_key: data.secret_key });
      setEncapResult({});
    },
  });

  const encapsulateMutation = useMutation({
    mutationFn: async ({ alg, public_key }: { alg: string; public_key: string }) => {
      const { data } = await api.post<{
        ciphertext: string;
        shared_secret: string;
      }>('/api/v1/crypto/kem/encapsulate', { algorithm: alg, public_key });
      return data;
    },
    onSuccess: (data) => {
      setEncapResult({ ciphertext: data.ciphertext, shared_secret: data.shared_secret });
      setKeygenResult({});
    },
  });

  const handleKeygen = useCallback(() => {
    keygenMutation.mutate(algorithm);
  }, [algorithm, keygenMutation]);

  const handleEncapsulate = useCallback(() => {
    encapsulateMutation.mutate({ alg: algorithm, public_key: publicKeyInput.trim() });
  }, [algorithm, publicKeyInput, encapsulateMutation]);

  const keygenError = keygenMutation.error as { response?: { data?: { detail?: string } } } | undefined;
  const encapError = encapsulateMutation.error as { response?: { data?: { detail?: string } } } | undefined;

  return (
    <div className="space-y-6">
      <RadioGroup
        value={mode}
        onValueChange={(v) => setMode(v as KemMode)}
        className="flex gap-6"
      >
        <label className="flex cursor-pointer items-center gap-2">
          <RadioGroupItem value="keygen" />
          <span className="text-sm font-medium">Generate keypair</span>
        </label>
        <label className="flex cursor-pointer items-center gap-2">
          <RadioGroupItem value="encapsulate" />
          <span className="text-sm font-medium">Encapsulate secret</span>
        </label>
      </RadioGroup>

      <div className="space-y-2">
        <span className="text-sm font-medium">Algorithm</span>
        <Select
          value={algorithm}
          onValueChange={(v) => setAlgorithm(v ?? KEM_OPTIONS[0].value)}
        >
          <SelectTrigger className="w-full max-w-xs">
            <SelectValue placeholder="Select algorithm" />
          </SelectTrigger>
          <SelectContent>
            {KEM_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                <span className="flex items-center gap-2">
                  {opt.value}
                  <Badge variant="secondary" className="text-[10px]">
                    NIST level {opt.level}
                  </Badge>
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {mode === 'keygen' && (
        <>
          <Button
            onClick={handleKeygen}
            disabled={keygenMutation.isPending}
          >
            {keygenMutation.isPending ? 'Generating…' : 'Generate keypair'}
          </Button>
          {keygenError && (
            <p className="text-sm text-destructive">
              {keygenError.response?.data?.detail ?? 'Keygen failed'}
            </p>
          )}
          <div className="space-y-4 rounded-lg border bg-muted/30 p-4">
            <ResultBlock
              label="Public key (base64)"
              value={keygenResult.public_key ?? ''}
            />
            <ResultBlock
              label="Secret key (base64)"
              value={keygenResult.secret_key ?? ''}
            />
          </div>
        </>
      )}

      {mode === 'encapsulate' && (
        <>
          <div className="space-y-2">
            <label className="text-sm font-medium">Public key (base64)</label>
            <Input
              placeholder="Paste recipient public key (base64)"
              value={publicKeyInput}
              onChange={(e) => setPublicKeyInput(e.target.value)}
              className="font-mono text-sm"
            />
          </div>
          <Button
            onClick={handleEncapsulate}
            disabled={encapsulateMutation.isPending || !publicKeyInput.trim()}
          >
            {encapsulateMutation.isPending ? 'Encapsulating…' : 'Encapsulate secret'}
          </Button>
          {encapError && (
            <p className="text-sm text-destructive">
              {encapError.response?.data?.detail ?? 'Encapsulate failed'}
            </p>
          )}
          <div className="space-y-4 rounded-lg border bg-muted/30 p-4">
            <ResultBlock
              label="Ciphertext (base64)"
              value={encapResult.ciphertext ?? ''}
            />
            <ResultBlock
              label="Shared secret (base64)"
              value={encapResult.shared_secret ?? ''}
            />
          </div>
        </>
      )}
    </div>
  );
}
