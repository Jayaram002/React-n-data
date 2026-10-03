import React, { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { consentApi } from '../features/consent/api';
import { 
  AlertOctagon, CheckCircle2, AlertTriangle, ShieldAlert, 
  Mail, ArrowLeft, Loader2, FileWarning 
} from 'lucide-react';

export const TakedownRequestPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const prefilledUploadId = searchParams.get('upload_id') || '';

  const [uploadId, setUploadId] = useState(prefilledUploadId);
  const [claimantName, setClaimantName] = useState('');
  const [claimantEmail, setClaimantEmail] = useState('');
  const [reason, setReason] = useState('copyright_infringement');
  const [details, setDetails] = useState('');

  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const parsedId = Number(uploadId);
    if (isNaN(parsedId) || parsedId <= 0) {
      setError('Please provide a valid numeric Dataset / Upload ID.');
      return;
    }
    if (!claimantName.trim() || !claimantEmail.trim() || !details.trim()) {
      setError('Please fill in all required fields.');
      return;
    }

    setLoading(true);
    try {
      await consentApi.submitTakedownRequest({
        upload_id: parsedId,
        claimant_name: claimantName.trim(),
        claimant_email: claimantEmail.trim(),
        reason,
        details: details.trim(),
      });
      setSubmitted(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit takedown notice. Please verify the Dataset ID.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-12 sm:px-6">
      <div className="mb-6">
        <Link to="/" className="inline-flex items-center text-xs text-slate-500 hover:text-slate-800 transition mb-3">
          <ArrowLeft className="w-3.5 h-3.5 mr-1" /> Back to Home
        </Link>
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-rose-50 text-rose-600">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">Notice & Takedown Request</h1>
            <p className="text-xs text-slate-500">
              Statutory Intermediary Takedown & DPDP Privacy Rights Procedure
            </p>
          </div>
        </div>
      </div>

      {submitted ? (
        <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-slate-900">Takedown Notice Successfully Registered</h2>
          <p className="text-xs text-slate-600 max-w-md mx-auto leading-relaxed">
            Your grievance has been logged with our Compliance and Legal Review team under IT Act (Intermediary Guidelines) and DPDP Rules 2025. You will receive acknowledgement and status updates at <span className="font-semibold text-slate-800">{claimantEmail}</span>.
          </p>
          <div className="pt-4 border-t border-slate-100">
            <Link
              to="/marketplace"
              className="inline-block px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-sm transition"
            >
              Return to Marketplace
            </Link>
          </div>
        </div>
      ) : (
        <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6">
          <p className="text-xs text-slate-600 leading-relaxed">
            If you believe a dataset hosted on React n Data infringes your copyright, privacy rights as a Data Principal, or contains unauthorized confidential data, please submit this formal notice.
          </p>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-800 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Dataset / Upload ID <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                required
                value={uploadId}
                onChange={(e) => setUploadId(e.target.value)}
                placeholder="e.g. 42"
                className="w-full px-3.5 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-rose-500"
              />
              <p className="text-[11px] text-slate-400 mt-1">Found in the URL of the dataset preview or listing page.</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Full Name / Legal Entity <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={claimantName}
                  onChange={(e) => setClaimantName(e.target.value)}
                  placeholder="e.g. Jane Doe or Acclaim Corp"
                  className="w-full px-3.5 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-rose-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Contact Email <span className="text-red-500">*</span>
                </label>
                <input
                  type="email"
                  required
                  value={claimantEmail}
                  onChange={(e) => setClaimantEmail(e.target.value)}
                  placeholder="e.g. legal@example.com"
                  className="w-full px-3.5 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-rose-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Infringement Category <span className="text-red-500">*</span>
              </label>
              <select
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="w-full px-3.5 py-2 border border-slate-300 rounded-lg text-xs bg-white focus:ring-2 focus:ring-rose-500"
              >
                <option value="copyright_infringement">Copyright & Intellectual Property Infringement</option>
                <option value="dpdp_privacy_violation">DPDP Violation (Unconsented Personal Data / Face / PII)</option>
                <option value="confidentiality_breach">Trade Secret or Confidentiality Breach</option>
                <option value="unlawful_content">Unlawful, Defamatory, or Prohibited Content</option>
                <option value="other">Other Statutory Grounds</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Detailed Statement & Proof of Right <span className="text-red-500">*</span>
              </label>
              <textarea
                required
                rows={4}
                value={details}
                onChange={(e) => setDetails(e.target.value)}
                placeholder="Identify the specific infringing elements, provide proof of ownership, or explain the nature of the privacy violation..."
                className="w-full px-3.5 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-rose-500"
              />
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-[11px] text-slate-500 space-y-1">
              <p className="font-semibold text-slate-700">Statutory Notice</p>
              <p>
                By submitting this notice, you confirm under penalty of perjury that you are the rightful copyright owner or authorized representative, or the Data Principal whose personal data is unlawfully included.
              </p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-xl shadow-sm transition disabled:opacity-50"
            >
              {loading ? 'Submitting Notice...' : 'Submit Formal Takedown Notice'}
            </button>
          </form>
        </div>
      )}
    </div>
  );
};
