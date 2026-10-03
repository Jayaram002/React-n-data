import React, { useState, useEffect } from 'react';
import { Upload } from '../../types';
import { consentApi } from './api';
import { ConsentRecord, ConsentDocument } from './types';
import { ConsentModal } from './ConsentModal';
import { 
  ShieldCheck, AlertTriangle, FileText, CheckCircle2, 
  XCircle, Clock, Hash, Lock, RefreshCw, AlertCircle 
} from 'lucide-react';

interface ConsentRightsPanelProps {
  upload: Upload;
  onUpdated: () => void;
}

export const ConsentRightsPanel: React.FC<ConsentRightsPanelProps> = ({ upload, onUpdated }) => {
  const [records, setRecords] = useState<ConsentRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeDocs, setActiveDocs] = useState<Record<string, ConsentDocument>>({});

  // Document modal viewer
  const [selectedDoc, setSelectedDoc] = useState<ConsentDocument | null>(null);

  // Withdrawal confirmation modal state
  const [withdrawingPurpose, setWithdrawingPurpose] = useState<string | null>(null);
  const [isSubmittingWithdrawal, setIsSubmittingWithdrawal] = useState(false);
  const [withdrawalSuccess, setWithdrawalSuccess] = useState<string | null>(null);

  const loadConsentData = async () => {
    setLoading(true);
    try {
      const [recs, docs] = await Promise.all([
        consentApi.getUploadConsentRecords(upload.id),
        consentApi.getActiveDocuments(),
      ]);
      setRecords(recs);
      const docMap: Record<string, ConsentDocument> = {};
      docs.forEach(d => {
        docMap[d.purpose_code] = d;
      });
      setActiveDocs(docMap);
    } catch (err: any) {
      console.error('Failed to load consent records', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConsentData();
  }, [upload.id]);

  const handleWithdraw = async (purposeCode: string) => {
    setIsSubmittingWithdrawal(true);
    setError('');
    try {
      const res = await consentApi.withdrawUploadConsent(upload.id, purposeCode);
      setWithdrawalSuccess(res.effects?.message || 'Consent successfully withdrawn.');
      setWithdrawingPurpose(null);
      await loadConsentData();
      onUpdated();
      setTimeout(() => setWithdrawalSuccess(null), 6000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to withdraw consent');
    } finally {
      setIsSubmittingWithdrawal(false);
    }
  };

  const isListingActive = upload.status === 'published';
  const isAITrainingAllowed = upload.ai_training_allowed;

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-indigo-600" />
            <h3 className="text-base font-bold text-slate-900">DPDP Consent & Legal Rights Management</h3>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Statutory records under India's DPDP Act 2023 & Rules 2025. All grants and revocations are immutably logged with SHA-256 integrity.
          </p>
        </div>
        <button
          onClick={loadConsentData}
          disabled={loading}
          className="inline-flex items-center gap-1.5 text-xs text-slate-600 hover:text-indigo-600 px-3 py-1.5 rounded-lg border border-slate-200 hover:border-indigo-300 transition-colors self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Journal
        </button>
      </div>

      {withdrawalSuccess && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{withdrawalSuccess}</span>
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Active Grants Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 1. Contributor Rights Warranty */}
        <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Ownership & Warranty</span>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                <CheckCircle2 className="w-3 h-3 mr-1" /> Active
              </span>
            </div>
            <p className="text-sm font-bold text-slate-900 mb-1">Contributor Rights Warranty</p>
            <p className="text-xs text-slate-600 mb-3">
              Legally warrants exclusive dataset ownership, authorization, and absence of infringing IP.
            </p>
          </div>
          <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-[11px] text-slate-500">
            <span>Doc v{upload.consent_version || '1.0'}</span>
            <button
              onClick={() => setSelectedDoc(activeDocs['contributor_rights_warranty'] || null)}
              className="text-indigo-600 hover:text-indigo-800 font-medium"
            >
              View Document & SHA
            </button>
          </div>
        </div>

        {/* 2. Platform Listing License */}
        <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Listing Authorization</span>
              {upload.status === 'unpublished' ? (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-800">
                  <XCircle className="w-3 h-3 mr-1" /> Withdrawn (Unpublished)
                </span>
              ) : (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                  <CheckCircle2 className="w-3 h-3 mr-1" /> Granted
                </span>
              )}
            </div>
            <p className="text-sm font-bold text-slate-900 mb-1">Platform Listing License</p>
            <p className="text-xs text-slate-600 mb-3">
              Authorizes platform display, customer previews, and commercial marketplace sublicensing.
            </p>
          </div>
          <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-[11px]">
            <button
              onClick={() => setSelectedDoc(activeDocs['platform_listing_license'] || null)}
              className="text-indigo-600 hover:text-indigo-800 font-medium"
            >
              View License
            </button>
            {upload.status !== 'unpublished' && (
              <button
                onClick={() => setWithdrawingPurpose('platform_listing_license')}
                className="text-xs font-semibold text-rose-600 hover:text-rose-800 bg-rose-50 hover:bg-rose-100 px-2.5 py-1 rounded-md transition-colors"
              >
                Withdraw License
              </button>
            )}
          </div>
        </div>

        {/* 3. Personal Data Attestation */}
        <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Personal Data Status</span>
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                upload.personal_data_status === 'contains_personal_data'
                  ? 'bg-amber-100 text-amber-800'
                  : upload.personal_data_status === 'anonymized'
                  ? 'bg-blue-100 text-blue-800'
                  : 'bg-emerald-100 text-emerald-800'
              }`}>
                {upload.personal_data_status === 'contains_personal_data'
                  ? 'Contains Personal Data'
                  : upload.personal_data_status === 'anonymized'
                  ? 'Anonymized / Synthetic'
                  : 'No Personal Data'}
              </span>
            </div>
            <p className="text-sm font-bold text-slate-900 mb-1">Third-Party Data Attestation</p>
            <div className="text-xs text-slate-600 space-y-1 mb-3">
              {upload.lawful_basis && (
                <p><span className="font-semibold">Lawful Basis:</span> {upload.lawful_basis}</p>
              )}
              {upload.lawful_basis_note && (
                <p><span className="font-semibold">Note:</span> {upload.lawful_basis_note}</p>
              )}
              {upload.evidence_storage_key && (
                <p className="text-indigo-600 flex items-center gap-1 font-medium">
                  <Lock className="w-3 h-3" /> Private evidence file on file
                </p>
              )}
            </div>
          </div>
          <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-[11px] text-slate-500">
            <span>Section 6 DPDP Compliance</span>
            <button
              onClick={() => setSelectedDoc(activeDocs['third_party_data_attestation'] || null)}
              className="text-indigo-600 hover:text-indigo-800 font-medium"
            >
              View Notice
            </button>
          </div>
        </div>

        {/* 4. AI Training Permission */}
        <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">AI Model Training</span>
              {isAITrainingAllowed ? (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                  <CheckCircle2 className="w-3 h-3 mr-1" /> Permitted
                </span>
              ) : (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-200 text-slate-700">
                  <XCircle className="w-3 h-3 mr-1" /> Excluded (Default OFF)
                </span>
              )}
            </div>
            <p className="text-sm font-bold text-slate-900 mb-1">AI Training Authorization</p>
            <p className="text-xs text-slate-600 mb-3">
              Independent consent grant for algorithmic weight training, LLM fine-tuning, and diffusion model adaptation.
            </p>
          </div>
          <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-[11px]">
            <button
              onClick={() => setSelectedDoc(activeDocs['ai_training_use'] || null)}
              className="text-indigo-600 hover:text-indigo-800 font-medium"
            >
              View Policy
            </button>
            {isAITrainingAllowed && (
              <button
                onClick={() => setWithdrawingPurpose('ai_training_use')}
                className="text-xs font-semibold text-rose-600 hover:text-rose-800 bg-rose-50 hover:bg-rose-100 px-2.5 py-1 rounded-md transition-colors"
              >
                Revoke AI Training
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Consent Records Audit Table */}
      <div className="pt-4 border-t border-slate-100">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-3 flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-slate-500" />
          Immutable Consent Records Journal (7-Year DPDP Statutory Log)
        </h4>

        {records.length === 0 ? (
          <p className="text-xs text-slate-400 py-3 italic">No consent transactions recorded yet.</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Timestamp (UTC)</th>
                  <th className="py-2.5 px-3">Purpose Code</th>
                  <th className="py-2.5 px-3">Action</th>
                  <th className="py-2.5 px-3">Document SHA-256</th>
                  <th className="py-2.5 px-3">Record ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {records.map((rec) => (
                  <tr key={rec.id} className="hover:bg-slate-50/70">
                    <td className="py-2 px-3 whitespace-nowrap text-slate-500">
                      {new Date(rec.created_at).toLocaleString()}
                    </td>
                    <td className="py-2 px-3 font-medium text-slate-900">
                      {rec.purpose_code}
                    </td>
                    <td className="py-2 px-3">
                      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        rec.action === 'granted'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-rose-50 text-rose-700 border border-rose-200'
                      }`}>
                        {rec.action.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-mono text-[10px] text-slate-500" title={rec.document_sha256}>
                      {rec.document_sha256.substring(0, 14)}...
                    </td>
                    <td className="py-2 px-3 font-mono text-[10px] text-slate-400">
                      #{rec.id}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Document Viewer Modal */}
      {selectedDoc && (
        <ConsentModal
          isOpen={true}
          onClose={() => setSelectedDoc(null)}
          document={selectedDoc}
        />
      )}

      {/* Withdrawal Confirmation Modal */}
      {withdrawingPurpose && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center gap-3 text-rose-600">
              <div className="w-10 h-10 rounded-full bg-rose-100 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">Confirm Statutory Consent Withdrawal</h3>
                <p className="text-xs text-slate-500">Digital Personal Data Protection Act, 2023</p>
              </div>
            </div>

            <div className="bg-slate-50 rounded-xl p-3.5 border border-slate-200 text-xs text-slate-700 space-y-2">
              {withdrawingPurpose === 'platform_listing_license' ? (
                <>
                  <p className="font-semibold text-slate-900">Effects of withdrawing Platform Listing License:</p>
                  <ul className="list-disc pl-4 space-y-1 text-slate-600">
                    <li>This dataset will be <strong>immediately unpublished</strong> and hidden from public search & purchase.</li>
                    <li>Past commercial licenses already issued to buyers remain legally valid.</li>
                    <li>Accrued earnings on your 80/20 ledger will not be reversed.</li>
                  </ul>
                </>
              ) : (
                <>
                  <p className="font-semibold text-slate-900">Effects of revoking AI Training Consent:</p>
                  <ul className="list-disc pl-4 space-y-1 text-slate-600">
                    <li><strong>Future commercial sales</strong> will exclude rights to use this dataset for model training or fine-tuning.</li>
                    <li>Existing models trained under prior licenses remain lawful as per Section 6(7) DPDP Act.</li>
                  </ul>
                </>
              )}
            </div>

            <p className="text-[11px] text-slate-500 italic">
              Note: This revocation event is permanent and will be logged in the immutable consent ledger.
            </p>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setWithdrawingPurpose(null)}
                disabled={isSubmittingWithdrawal}
                className="px-4 py-2 border border-slate-200 text-slate-700 rounded-lg text-xs font-semibold hover:bg-slate-50 transition-colors"
              >
                Keep Consent Active
              </button>
              <button
                type="button"
                onClick={() => handleWithdraw(withdrawingPurpose)}
                disabled={isSubmittingWithdrawal}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors disabled:opacity-50"
              >
                {isSubmittingWithdrawal ? 'Recording Revocation...' : 'Confirm Withdrawal'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
