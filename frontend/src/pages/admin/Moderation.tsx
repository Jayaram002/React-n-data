import React, { useEffect, useState } from 'react';
import { adminApi, categoriesApi } from '../../api/client';
import { ModerationItem, CategoryTree } from '../../types';
import { 
  Shield, AlertTriangle, CheckCircle2, XCircle, Tag, 
  HelpCircle, Sparkles, Loader2, ArrowRight, RefreshCw, Eye 
} from 'lucide-react';

export const AdminModerationPage: React.FC = () => {
  const [items, setItems] = useState<ModerationItem[]>([]);
  const [categories, setCategories] = useState<CategoryTree[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'flagged' | 'held' | 'contributor_requested'>('all');
  
  // Action modal
  const [selectedItem, setSelectedItem] = useState<ModerationItem | null>(null);
  const [actionCategory, setActionCategory] = useState<number | ''>('');
  const [actionSubcategory, setActionSubcategory] = useState<number | ''>('');
  const [actionReason, setActionReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const fetchQueue = async () => {
    try {
      setLoading(true);
      const [queueData, catsData] = await Promise.all([
        adminApi.getModerationQueue(),
        categoriesApi.getCategories(),
      ]);
      setItems(queueData);
      setCategories(catsData);
    } catch (err: any) {
      setError('Failed to load moderation queue');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  const handleAction = async (uploadId: number, action: 'approve' | 'flag' | 'reject' | 'unpublish') => {
    try {
      setSubmitting(true);
      await adminApi.executeModerationAction(uploadId, {
        action,
        category_id: actionCategory ? Number(actionCategory) : undefined,
        subcategory_id: actionSubcategory ? Number(actionSubcategory) : undefined,
        reason: actionReason || undefined,
      });
      setSelectedItem(null);
      setActionReason('');
      setActionCategory('');
      setActionSubcategory('');
      setActionSuccess(`Upload #${uploadId} action '${action.toUpperCase()}' completed successfully!`);
      await fetchQueue();
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Moderation action failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResolveFlag = async (flagId: number, action: 'resolve' | 'dismiss') => {
    try {
      await adminApi.resolveFlag(flagId, { action });
      setActionSuccess(`Flag #${flagId} ${action}d!`);
      await fetchQueue();
      setTimeout(() => setActionSuccess(null), 3000);
    } catch (err: any) {
      alert('Failed to resolve flag');
    }
  };

  const filteredItems = items.filter((item) => {
    if (activeTab === 'flagged') return item.status === 'flagged' || item.flags_count > 0;
    if (activeTab === 'held') return item.status === 'held_uncategorized';
    if (activeTab === 'contributor_requested') return item.category_source === 'contributor';
    return true;
  });

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 text-indigo-600 animate-spin mb-2" />
        <p className="text-slate-500 text-sm">Loading admin moderation queue...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
            <Shield className="h-7 w-7 text-indigo-600" />
            <span>Admin Moderation & Quality Queue</span>
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Review security flags, low-confidence Gemma AI classifications, and contributor category override requests.
          </p>
        </div>

        <button
          onClick={fetchQueue}
          className="inline-flex items-center space-x-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold px-3 py-2 rounded-xl transition-colors self-start sm:self-auto"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Refresh Queue</span>
        </button>
      </div>

      {actionSuccess && (
        <div className="bg-emerald-50 text-emerald-800 p-4 rounded-xl text-sm font-medium border border-emerald-200 flex items-center space-x-2">
          <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-xl text-sm font-medium border border-red-200">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex space-x-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setActiveTab('all')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-colors ${
            activeTab === 'all' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          All Items ({items.length})
        </button>
        <button
          onClick={() => setActiveTab('flagged')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-colors ${
            activeTab === 'flagged' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Security & Flags ({items.filter((i) => i.status === 'flagged' || i.flags_count > 0).length})
        </button>
        <button
          onClick={() => setActiveTab('held')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-colors ${
            activeTab === 'held' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Held Uncategorized ({items.filter((i) => i.status === 'held_uncategorized').length})
        </button>
        <button
          onClick={() => setActiveTab('contributor_requested')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-colors ${
            activeTab === 'contributor_requested' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Contributor Requests ({items.filter((i) => i.category_source === 'contributor').length})
        </button>
      </div>

      {/* Moderation Items Table / List */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {filteredItems.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            <CheckCircle2 className="h-10 w-10 text-emerald-500 mx-auto mb-2" />
            <p className="font-bold text-slate-800">Queue is clear</p>
            <p className="text-xs text-slate-400 mt-1">No pending moderation flags or unassigned datasets found.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filteredItems.map((item) => (
              <div key={item.id} className="p-5 hover:bg-slate-50/50 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
                <div className="space-y-2 flex-grow">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                        item.status === 'flagged'
                          ? 'bg-red-100 text-red-800'
                          : item.status === 'held_uncategorized'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-indigo-100 text-indigo-800'
                      }`}
                    >
                      {item.status.toUpperCase()}
                    </span>

                    <span className="text-xs font-mono text-slate-400">Upload #{item.id}</span>
                    <span className="text-xs text-slate-400">• Contributor: {item.contributor_name} ({item.contributor_email})</span>
                  </div>

                  <div>
                    <h3 className="text-base font-bold text-slate-900">{item.title}</h3>
                    <p className="text-xs text-slate-600 mt-0.5 line-clamp-2">{item.description}</p>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 pt-1">
                    <span>Domain: <strong>{item.category_name || 'Unassigned'}</strong> {item.subcategory_name && `(${item.subcategory_name})`}</span>
                    <span>Source: <span className="font-semibold uppercase text-indigo-600">{item.category_source}</span></span>
                    {item.category_confidence !== undefined && item.category_confidence !== null && (
                      <span>AI Conf: <strong>{(item.category_confidence * 100).toFixed(0)}%</strong></span>
                    )}
                    {item.ai_total_score && (
                      <span className="text-amber-700 font-bold bg-amber-50 px-2 py-0.5 rounded">
                        Trust Score: {item.ai_total_score}/100
                      </span>
                    )}
                  </div>

                  {/* Open Flags List */}
                  {item.open_flags.length > 0 && (
                    <div className="bg-red-50 p-3 rounded-xl border border-red-100 space-y-2 text-xs text-red-900 mt-2">
                      <div className="font-bold flex items-center space-x-1.5 text-red-700">
                        <AlertTriangle className="h-4 w-4" />
                        <span>Active Review Flags ({item.open_flags.length})</span>
                      </div>
                      {item.open_flags.map((f) => (
                        <div key={f.id} className="flex items-center justify-between gap-2 pl-2 border-l-2 border-red-300">
                          <div>
                            <p className="font-medium">{f.reason}</p>
                            <span className="text-[10px] text-red-600 font-mono">Source: {f.source}</span>
                          </div>
                          <div className="flex space-x-1.5">
                            <button
                              onClick={() => handleResolveFlag(f.id, 'resolve')}
                              className="px-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[10px] font-bold"
                            >
                              Resolve
                            </button>
                            <button
                              onClick={() => handleResolveFlag(f.id, 'dismiss')}
                              className="px-2 py-1 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded text-[10px] font-bold"
                            >
                              Dismiss
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Moderation action buttons */}
                <div className="flex flex-wrap lg:flex-nowrap items-center gap-2 self-stretch lg:self-auto border-t lg:border-t-0 pt-3 lg:pt-0 border-slate-100">
                  <button
                    onClick={() => {
                      setSelectedItem(item);
                      setActionCategory(item.category_id || '');
                      setActionSubcategory(item.subcategory_id || '');
                    }}
                    className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-sm transition-colors flex items-center space-x-1.5"
                  >
                    <Tag className="h-3.5 w-3.5" />
                    <span>Assign Domain</span>
                  </button>

                  <button
                    onClick={() => handleAction(item.id, 'approve')}
                    className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-sm transition-colors flex items-center space-x-1.5"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Approve</span>
                  </button>

                  <button
                    onClick={() => handleAction(item.id, 'flag')}
                    className="px-3 py-2 bg-amber-50 hover:bg-amber-100 text-amber-800 text-xs font-bold rounded-xl border border-amber-200 transition-colors"
                  >
                    Flag
                  </button>

                  <button
                    onClick={() => handleAction(item.id, 'reject')}
                    className="px-3 py-2 bg-red-50 hover:bg-red-100 text-red-700 text-xs font-bold rounded-xl border border-red-200 transition-colors"
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ASSIGN CATEGORY / MODERATION MODAL */}
      {selectedItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
                <Tag className="h-5 w-5 text-indigo-600" />
                <span>Assign Domain & Approve Upload #{selectedItem.id}</span>
              </h3>
              <button
                onClick={() => setSelectedItem(null)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <p className="font-bold text-slate-800">{selectedItem.title}</p>
                <p className="text-slate-500 text-[11px] mt-0.5">{selectedItem.description}</p>
              </div>

              {/* Category Select */}
              <div>
                <label className="font-bold text-slate-700 block mb-1">Primary Domain Category</label>
                <select
                  value={actionCategory}
                  onChange={(e) => {
                    setActionCategory(e.target.value ? Number(e.target.value) : '');
                    setActionSubcategory('');
                  }}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">-- Select Category --</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} (${(c.base_price_paise / 100).toFixed(2)})
                    </option>
                  ))}
                </select>
              </div>

              {/* Subcategory Select */}
              {actionCategory && (
                <div>
                  <label className="font-bold text-slate-700 block mb-1">Subcategory (Optional)</label>
                  <select
                    value={actionSubcategory}
                    onChange={(e) => setActionSubcategory(e.target.value ? Number(e.target.value) : '')}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">-- None --</option>
                    {categories
                      .find((c) => c.id === Number(actionCategory))
                      ?.subcategories.map((sub) => (
                        <option key={sub.id} value={sub.id}>
                          {sub.name}
                        </option>
                      ))}
                  </select>
                </div>
              )}

              {/* Moderator notes */}
              <div>
                <label className="font-bold text-slate-700 block mb-1">Moderator Notes (Optional)</label>
                <textarea
                  value={actionReason}
                  onChange={(e) => setActionReason(e.target.value)}
                  placeholder="Reason for assignment or approval..."
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  rows={2}
                />
              </div>

              <div className="pt-3 flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setSelectedItem(null)}
                  className="px-4 py-2 text-slate-600 font-bold hover:bg-slate-100 rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={submitting || !actionCategory}
                  onClick={() => handleAction(selectedItem.id, 'approve')}
                  className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold rounded-xl shadow flex items-center space-x-2 transition-colors"
                >
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                  <span>Save & Approve</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
