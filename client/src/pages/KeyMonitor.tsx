import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { api } from '@/lib/api';

type LocalKey = {
  key_id: string;
  requester_sae: string;
  recipient_sae: string;
  key_size: number;
  algorithm: string;
  state: string;
  created_at?: string | null;
  served_at?: string | null;
  consumed_at?: string | null;
  expires_at?: string | null;
  key_material: string;
};

const formatDateTime = (value?: string | null) =>
  value ? new Date(value).toLocaleString() : '—';

const truncate = (val: string | undefined | null, len = 24) => {
  const s = val ?? '';
  return s.length > len ? `${s.slice(0, len)}…` : s;
};

interface KeyMonitorProps {
  email: string;
  backTo?: string;
  label?: string;
}

export default function KeyMonitor({ email, backTo = '/dashboard', label }: KeyMonitorProps) {
  const navigate = useNavigate();
  const [keys, setKeys] = useState<LocalKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadKeys = useCallback(async () => {
    if (!email) {
      setError('No email specified');
      setLoading(false);
      return;
    }
    try {
      const data = await api.listKmKeysForEmail(email, 200);
      setKeys(data.keys || []);
      setError('');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load keys';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [email]);

  useEffect(() => {
    loadKeys();
    const id = setInterval(loadKeys, 5000);
    return () => clearInterval(id);
  }, [loadKeys]);

  const renderTable = (data: LocalKey[]) => (
    <div className="overflow-x-auto">
      <table className="min-w-full overflow-x-scroll text-sm text-left">
        <thead className="bg-slate-100">
          <tr>
            <th className="px-3 py-2">S.No</th>
            <th className="px-3 py-2">Key ID</th>
            <th className="px-3 py-2">Key Material</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Size</th>
            <th className="px-3 py-2">Requester</th>
            <th className="px-3 py-2">Recipient</th>
            <th className="px-3 py-2">Created</th>
            <th className="px-3 py-2">Consumed</th>
          </tr>
        </thead>
        <tbody>
          {data.length === 0 && (
            <tr>
              <td colSpan={9} className="px-3 py-4 text-center text-slate-500">
                No keys found
              </td>
            </tr>
          )}
          {data.map((k, idx) => (
            <tr key={k.key_id} className="border-b last:border-0">
              <td className="px-3 py-2">{idx + 1}</td>
              <td className="px-3 py-2 font-mono text-xs">{truncate(k.key_id, 18)}</td>
              <td className="px-3 py-2 font-mono text-xs">{truncate(k.key_material, 22)}</td>
              <td className="px-3 py-2 capitalize">{k.state}</td>
              <td className="px-3 py-2">{k.key_size}</td>
              <td className="px-3 py-2">{k.requester_sae}</td>
              <td className="px-3 py-2">{k.recipient_sae}</td>
              <td className="px-3 py-2">{formatDateTime(k.created_at)}</td>
              <td className="px-3 py-2">
                {k.state === 'consumed' ? formatDateTime(k.consumed_at) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="min-h-screen w-full bg-linear-to-br from-slate-50 via-white to-slate-100">
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">KM Key Monitor</h1>
            <p className="text-sm text-slate-600">
              Keys from KM service where this mailbox is requester or recipient. Auto-refresh every 5s.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => loadKeys()} disabled={loading}>
              Refresh
            </Button>
            <Button onClick={() => navigate(backTo)}>Back</Button>
          </div>
        </div>

        {error && (
          <div className="rounded-md bg-red-50 text-red-700 px-4 py-3 border border-red-200">
            {error}
          </div>
        )}

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">KM Keys</h2>
                <p className="text-sm text-slate-600">
                  Mailbox: {label || email}
                </p>
              </div>
              <span className="text-sm text-slate-500">Total: {keys.length}</span>
            </div>
          </CardHeader>
          <Separator />
          <CardContent>
            <ScrollArea className="h-[520px] overflow-x-scroll pr-2">
              {loading ? (
                <div className="text-center text-slate-500 py-8">Loading keys...</div>
              ) : (
                renderTable(keys)
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

