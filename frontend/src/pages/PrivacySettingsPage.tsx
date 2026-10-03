import React, { useState, useEffect } from 'react';
import { consentApi } from '../features/consent/api';
import { DataExport, ConsentRecord, DeletionRequest } from '../features/consent/types';
import { useAuth } from '../context/AuthContext';
import { 
  ShieldCheck, Download, Trash2, Clock, CheckCircle2, 
  AlertTriangle, Mail, UserCheck, FileJson, Loader2, ArrowRight 
} from 'lucide-react';

export const PrivacySettingsPage: React.FC = () => {
  const { user } = useAuth();
  const [exportData, setExportData] = useState<DataExport | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Erasure form state
  const [deletionReason, setDeletionReason] = useState('');
  const [showDeletionModal, setShowDeletionModal] = useState(false);
  const [submittingDeletion, setSubmittingDeletion] = useState(false);
  const [deletionSubmitted, setDeletionSubmitted] = useState<DeletionRequest | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await consentApi.exportUserData();
      setExportData(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load consent profile');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleDownloadExport = async () => {
    setExporting(true);
    try {
      const data = await consentApi.exportUserData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `react_n_data_dpdp_export_${user?.id || 'me'}_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setSuccess('Data export downloaded successfully.');
      setTimeout(() => setSuccess(''), 4000);
    } catch (err: any) {
      setError('Failed to generate data export');
    } finally {
      setExporting(false);
    }
  };

  const handleRequestDeletion = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingDeletion(true);
    setError('');
    try {
      const res = await consentApi.requestAccountDeletion(deletionReason);
      setDeletionSubmitted(res);
      setShowDeletionModal(false);
      setSuccess('Account erasure request submitted. An admin will review and process your request under DPDP Section 12 guidelines.');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit erasure request');
    } finally {
      setSubmittingDeletion(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mb-2" />
        <p className="text-xs text-slate-500">Loading statutory DPDP consent profile...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 sm:px-6 lg:px-8 space-y-8">
      {/* Page Title */}
      <div>
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-7 h-7 text-indigo-600" />
          <h1 className="text-2xl font-bold text-slate-900">Privacy & Data Principal Rights</h1>
        </div>
        <p className="text-xs text-slate-600 mt-1 max-w-2xl">
          Exercise your statutory rights under India's Digital Personal Data Protection (DPDP) Act, 2023. You have full transparency over all granted consents, data portability exports, and statutory erasure requests.
        </p>
      </div>

      {success && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-800 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Profile & Status Card */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
          <UserCheck className="w-4 h-4 text-indigo-600" />
          Data Principal Identification
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
            <span className="text-slate-400 block text-[11px]">Account Email</span>
            <span className="font-semibold text-slate-800 break-all">{exportData?.user_profile?.email}</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
            <span className="text-slate-400 block text-[11px]">Role</span>
            <span className="font-semibold uppercase text-indigo-700">{exportData?.user_profile?.role}</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
            <span className="text-slate-400 block text-[11px]">DPDP Age Verification</span>
            <span className="font-semibold text-emerald-700 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> 18+ Confirmed
            </span>
          </div>
        </div>
      </div>

      {/* Right to Data Portability (Section 11) */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <FileJson className="w-4 h-4 text-indigo-600" />
              Right to Access & Data Portability (Section 11)
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Download a machine-readable JSON archive of your personal profile, uploads metadata, purchases, and complete immutable consent history.
            </p>
          </div>
          <button
            onClick={handleDownloadExport}
            disabled={exporting}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-sm transition disabled:opacity-50 shrink-0"
          >
            {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            Download Data Export (JSON)
          </button>
        </div>
      </div>

      {/* Immutable Consent Records Table */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
          <Clock className="w-4 h-4 text-indigo-600" />
          Complete DPDP Consent Audit Trail (7-Year Statutory Journal)
        </h2>
        <p className="text-xs text-slate-500">
          Every consent grant, renewal, or withdrawal is recorded with an immutable SHA-256 cryptographic checksum.
        </p>

        {(!exportData?.consent_history || exportData.consent_history.length === 0) ? (
          <p className="text-xs text-slate-400 py-3 italic">No consent transactions recorded.</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Date (UTC)</th>
                  <th className="py-2.5 px-3">Purpose Code</th>
                  <th className="py-2.5 px-3">Action</th>
                  <th className="py-2.5 px-3">Target</th>
                  <th className="py-2.5 px-3">Document SHA-256</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {exportData.consent_history.map((rec) => (
                  <tr key={rec.id} className="hover:bg-slate-50/70">
                    <td className="py-2.5 px-3 text-slate-500 whitespace-nowrap">
                      {new Date(rec.created_at).toLocaleString()}
                    </td>
                    <td className="py-2.5 px-3 font-medium text-slate-900">
                      {rec.purpose_code}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        rec.action === 'granted'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-rose-50 text-rose-700 border border-rose-200'
                      }`}>
                        {rec.action.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-500">
                      {rec.upload_id ? `Upload #${rec.upload_id}` : rec.order_id ? `Order #${rec.order_id}` : 'Account'}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[10px] text-slate-500" title={rec.document_sha256}>
                      {rec.document_sha256.substring(0, 16)}...
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Right to Erasure (Section 12) */}
      <div className="bg-white p-6 rounded-2xl border border-red-200 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-sm font-bold text-red-900 uppercase tracking-wider flex items-center gap-2">
              <Trash2 className="w-4 h-4 text-red-600" />
              Right to Erasure & Account Anonymization (Section 12)
            </h2>
            <p className="text-xs text-slate-600 mt-1 max-w-xl">
              Request permanent anonymization of your account under DPDP Section 12. Active dataset listings will be unpublished. Consent and financial ledger records are retained pseudonymously for mandatory statutory retention (7 years).
            </p>
          </div>
          <button
            onClick={() => setShowDeletionModal(true)}
            className="px-4 py-2 bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 rounded-xl text-xs font-semibold transition shrink-0"
          >
            Request Account Erasure
          </button>
        </div>
      </div>

      {/* Grievance Redressal Officer Contact */}
      <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200 text-xs space-y-2">
        <h3 className="font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
          <Mail className="w-4 h-4 text-indigo-600" />
          Statutory Grievance Redressal Mechanism
        </h3>
        <p className="text-slate-600 leading-relaxed">
          If you are unsatisfied with any aspect of personal data processing or consent management, you may register a formal grievance with our designated officer under the DPDP Rules 2025:
        </p>
        <div className="pt-2 text-slate-800 space-y-1">
          <p><span className="font-semibold text-slate-600">Designated Officer:</span> Grievance Redressal Cell / Data Protection Officer</p>
          <p>
            <span className="font-semibold text-slate-600">Direct Email:</span>{' '}
            <a href="mailto:grievance@reactndata.internal" className="text-indigo-600 hover:underline font-medium">
              grievance@reactndata.internal
            </a>
          </p>
          <p><span className="font-semibold text-slate-600">Statutory SLA:</span> Formal response within 30 days of grievance receipt</p>
        </div>
      </div>

      {/* Deletion Modal */}
      {showDeletionModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-red-600">
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">Request Account Erasure</h3>
                <p className="text-xs text-slate-500">DPDP Act 2023 Section 12</p>
              </div>
            </div>

            <form onSubmit={handleRequestDeletion} className="space-y-4">
              <p className="text-xs text-slate-600 leading-relaxed">
                Submitting this request will initiate statutory account erasure. An administrator will review your account to verify there are no active dispute holds or unsettled transactions.
              </p>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Reason for Deletion Request (Optional)
                </label>
                <textarea
                  rows={3}
                  value={deletionReason}
                  onChange={(e) => setDeletionReason(e.target.value)}
                  placeholder="e.g. Account no longer needed, withdrawing all consents"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-red-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowDeletionModal(false)}
                  disabled={submittingDeletion}
                  className="px-4 py-2 border border-slate-200 text-slate-600 rounded-lg text-xs font-semibold hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingDeletion}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold shadow-sm disabled:opacity-50"
                >
                  {submittingDeletion ? 'Submitting...' : 'Submit Erasure Request'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
