import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { CheckIcon, DownloadIcon, XIcon } from 'lucide-react';
import { useCallback, useMemo, useState } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  Button,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui';
import { cn } from '@/lib/utils';

export type AuditRow = {
  id: string;
  organization_id: string;
  user_id: string | null;
  operation: string;
  algorithm: string | null;
  ip_address: string | null;
  latency_ms: number | null;
  success: boolean;
  created_at: string;
};

type AuditPage = {
  items: AuditRow[];
  total: number;
  page: number;
  page_size: number;
};

const PAGE_SIZE = 20;

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    dateStyle: 'short',
    timeStyle: 'medium',
  });
}

export default function AuditTable() {
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [operation, setOperation] = useState<string>('');
  const [page, setPage] = useState(1);

  const startParam = startDate || undefined;
  const endParam = endDate || undefined;
  const operationParam = operation || undefined;

  const { data: operations = [] } = useQuery({
    queryKey: ['audit-operations'],
    queryFn: async () => {
      const { data } = await api.get<string[]>('/api/v1/audit/operations');
      return data;
    },
  });

  const {
    data,
    isFetching,
    isPlaceholderData,
  } = useQuery({
    queryKey: ['audit', page, PAGE_SIZE, startParam, endParam, operationParam],
    queryFn: async (): Promise<AuditPage> => {
      const params = new URLSearchParams();
      params.set('page', String(page));
      params.set('page_size', String(PAGE_SIZE));
      if (startParam) params.set('start_date', startParam);
      if (endParam) params.set('end_date', endParam);
      if (operationParam) params.set('operation', operationParam);
      const { data: res } = await api.get<AuditPage>(
        `/api/v1/audit?${params.toString()}`
      );
      return res;
    },
    placeholderData: keepPreviousData,
  });

  const exportCsv = useCallback(async () => {
    const params = new URLSearchParams();
    if (startParam) params.set('start_date', startParam);
    if (endParam) params.set('end_date', endParam);
    if (operationParam) params.set('operation', operationParam);
    const { data: blob } = await api.get<Blob>(
      `/api/v1/audit/export?${params.toString()}`,
      { responseType: 'blob' }
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'audit_export.csv';
    a.click();
    URL.revokeObjectURL(url);
  }, [startParam, endParam, operationParam]);

  const columns = useMemo<ColumnDef<AuditRow>[]>(
    () => [
      {
        accessorKey: 'created_at',
        header: 'Timestamp',
        cell: ({ getValue }) => formatTimestamp(getValue() as string),
      },
      {
        accessorKey: 'operation',
        header: 'Operation',
      },
      {
        accessorKey: 'algorithm',
        header: 'Algorithm',
        cell: ({ getValue }) => (getValue() as string | null) ?? '—',
      },
      {
        accessorKey: 'latency_ms',
        header: 'Latency (ms)',
        cell: ({ getValue }) => {
          const v = getValue() as number | null;
          return v != null ? String(v) : '—';
        },
      },
      {
        accessorKey: 'ip_address',
        header: 'IP address',
        cell: ({ getValue }) => (getValue() as string | null) ?? '—',
      },
      {
        accessorKey: 'success',
        header: 'Success',
        cell: ({ getValue }) => {
          const ok = getValue() as boolean;
          return ok ? (
            <span className="inline-flex text-green-600 dark:text-green-400" aria-label="Success">
              <CheckIcon className="size-4" />
            </span>
          ) : (
            <span className="inline-flex text-red-600 dark:text-red-400" aria-label="Failed">
              <XIcon className="size-4" />
            </span>
          );
        },
      },
    ],
    []
  );

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const hasPrev = page > 1;
  const hasNext = page < totalPages;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-muted-foreground">From date</label>
          <Input
            type="date"
            value={startDate}
            onChange={(e) => {
              setStartDate(e.target.value);
              setPage(1);
            }}
            className="w-[160px]"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-muted-foreground">To date</label>
          <Input
            type="date"
            value={endDate}
            onChange={(e) => {
              setEndDate(e.target.value);
              setPage(1);
            }}
            className="w-[160px]"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-muted-foreground">Operation</label>
          <Select
            value={operation || 'all'}
            onValueChange={(v: string) => {
              setOperation(v === 'all' ? '' : v);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="All operations" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All operations</SelectItem>
              {operations.map((op) => (
                <SelectItem key={op} value={op}>
                  {op}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={exportCsv}
          className="gap-1.5"
        >
          <DownloadIcon className="size-4" />
          Export CSV
        </Button>
      </div>

      <div
        className={cn(
          'relative rounded-lg border',
          (isFetching && !isPlaceholderData) && 'opacity-70'
        )}
      >
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center text-muted-foreground">
                  No audit entries.
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          {total === 0
            ? 'No rows'
            : `Showing ${(page - 1) * PAGE_SIZE + 1}–${Math.min(page * PAGE_SIZE, total)} of ${total}`}
        </p>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={!hasPrev || isFetching}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={!hasNext || isFetching}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
