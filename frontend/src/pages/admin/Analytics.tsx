import React, { useEffect, useState } from 'react';
import { adminApi } from '../../api/client';
import { PlatformAnalytics, AuditLogPagination } from '../../types';
import { 
  BarChart3, DollarSign, TrendingUp, Users, Database, 
  ShoppingBag, Shield, FileText, Search, Loader2, RefreshCw, Layers 
} from 'lucide-react';

export const AdminAnalyticsPage: React.FC = () => {
  const [analytics, setAnalytics] = useState<PlatformAnalytics | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogPagination | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Audit log filtering
  const [searchAction, setSearchAction] = useState('');
  const [searchEntity, setSearchEntity] = useState('');
  const [page, setPage] = useState(1);

  const fetchAnalyticsAndLogs = async () => {
    try {
      setLoading(true);
      const [analyticsData, logsData] = await Promise.all([
        adminApi.getAnalytics(),
        adminApi.getAuditLogs({ page, limit: 15, action: searchAction || undefined, entity: searchEntity || undefined }),
      ]);
      setAnalytics(analyticsData);
      setAuditLogs(logsData);
    } catch (err: any) {
      setError('Failed to load platform analytics & audit logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalyticsAndLogs();
  }, [page]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchAnalyticsAndLogs();
  };

  if (loading && !analytics) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 text-indigo-600 animate-spin mb-2" />
        <p className="text-slate-500 text-sm">Aggregating platform revenue and ledger records...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
            <BarChart3 className="h-7 w-7 text-indigo-600" />
            <span>Platform Revenue & System Audit Analytics</span>
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Real-time double-entry gross marketplace volume, 20% platform take-rate, and immutable system audit trails.
          </p>
        </div>

        <button
          onClick={fetchAnalyticsAndLogs}
          className="inline-flex items-center space-x-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold px-3.5 py-2 rounded-xl transition-colors self-start sm:self-auto"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Refresh Metrics</span>
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-xl text-sm font-medium border border-red-200">
          {error}
        </div>
      )}

      {/* 4 KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* GMV */}
        <div className="bg-gradient-to-br from-indigo-950 via-slate-900 to-indigo-900 text-white p-6 rounded-2xl shadow-md space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-bold text-indigo-200 tracking-wider">Gross Volume (GMV)</span>
            <TrendingUp className="h-5 w-5 text-amber-300" />
          </div>
          <div className="text-3xl font-black font-mono">
            ${((analytics?.gmv_paise || 0) / 100).toFixed(2)}
          </div>
          <p className="text-xs text-indigo-200">Total settled sales volume.</p>
        </div>

        {/* Platform Revenue */}
        <div className="bg-gradient-to-br from-emerald-600 to-teal-700 text-white p-6 rounded-2xl shadow-md space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-bold text-emerald-100 tracking-wider">Platform Take-Rate (20%)</span>
            <DollarSign className="h-5 w-5 text-emerald-200" />
          </div>
          <div className="text-3xl font-black font-mono">
            ${((analytics?.platform_revenue_paise || 0) / 100).toFixed(2)}
          </div>
          <p className="text-xs text-emerald-100">Marketplace commission revenue.</p>
        </div>

        {/* Contributor Payouts */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-bold text-slate-500 tracking-wider">Disbursed Payouts</span>
            <ShoppingBag className="h-5 w-5 text-indigo-500" />
          </div>
          <div className="text-3xl font-black text-slate-900 font-mono">
            ${((analytics?.contributor_payouts_paise || 0) / 100).toFixed(2)}
          </div>
          <p className="text-xs text-slate-500">Paid out to contributors.</p>
        </div>

        {/* Active Marketplace Listings */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-bold text-slate-500 tracking-wider">Active Listings</span>
            <Database className="h-5 w-5 text-emerald-500" />
          </div>
          <div className="text-3xl font-black text-slate-900 font-mono">
            {analytics?.total_active_listings || 0}
          </div>
          <p className="text-xs text-slate-500">{analytics?.total_uploads || 0} total uploaded datasets.</p>
        </div>
      </div>

      {/* Platform Domain Distribution */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden p-6 space-y-4">
        <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
          <Layers className="h-5 w-5 text-indigo-600" />
          <span>Domain Taxonomy Dataset Distribution</span>
        </h2>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {analytics?.category_distribution.map((cat) => (
            <div key={cat.category_id} className="p-3 bg-slate-50 rounded-xl border border-slate-200/70 text-xs space-y-1">
              <span className="font-bold text-slate-800 truncate block">{cat.category_name}</span>
              <div className="text-[11px] text-slate-500 flex justify-between">
                <span>Published:</span>
                <span className="font-bold text-indigo-600">{cat.published_count}</span>
              </div>
              <div className="text-[11px] text-slate-400 font-mono">
                Base: ${(cat.base_price_paise / 100).toFixed(2)}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* System Audit Logs Section */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden space-y-4 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <Shield className="h-5 w-5 text-indigo-600" />
            <span>Immutable System Audit Logs</span>
          </h2>

          {/* Audit filter search */}
          <form onSubmit={handleSearchSubmit} className="flex items-center space-x-2 text-xs">
            <input
              type="text"
              value={searchAction}
              onChange={(e) => setSearchAction(e.target.value)}
              placeholder="Filter action (e.g. PAID, PAYOUT)"
              className="px-3 py-1.5 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
            />
            <button
              type="submit"
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg shadow-sm"
            >
              Filter
            </button>
          </form>
        </div>

        {/* Audit Log Table */}
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs text-left">
            <thead className="bg-slate-50 text-slate-700 font-semibold">
              <tr>
                <th className="px-3 py-2.5">Timestamp</th>
                <th className="px-3 py-2.5">Action</th>
                <th className="px-3 py-2.5">Entity</th>
                <th className="px-3 py-2.5">Entity ID</th>
                <th className="px-3 py-2.5">Actor</th>
                <th className="px-3 py-2.5">Metadata</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white font-mono">
              {auditLogs?.items.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-400 font-sans">
                    No audit records matching criteria.
                  </td>
                </tr>
              ) : (
                auditLogs?.items.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/60">
                    <td className="px-3 py-2 text-slate-500 whitespace-nowrap">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="px-3 py-2">
                      <span className="px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 font-bold">
                        {log.action}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-slate-600">{log.entity}</td>
                    <td className="px-3 py-2 text-slate-600">#{log.entity_id}</td>
                    <td className="px-3 py-2 text-slate-600 font-sans truncate max-w-xs">
                      {log.actor_email || `User #${log.actor_id || 'sys'}`}
                    </td>
                    <td className="px-3 py-2 text-slate-400 text-[10px] truncate max-w-sm">
                      {log.meta ? JSON.stringify(log.meta) : '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination controls */}
        {auditLogs && auditLogs.total_pages > 1 && (
          <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs">
            <span className="text-slate-500">
              Showing page {auditLogs.page} of {auditLogs.total_pages} ({auditLogs.total} total logs)
            </span>
            <div className="flex space-x-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1 bg-slate-100 hover:bg-slate-200 disabled:opacity-40 rounded-lg font-bold"
              >
                Previous
              </button>
              <button
                disabled={page >= auditLogs.total_pages}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1 bg-slate-100 hover:bg-slate-200 disabled:opacity-40 rounded-lg font-bold"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
