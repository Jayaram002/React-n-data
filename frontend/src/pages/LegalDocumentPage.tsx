import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { consentApi } from '../features/consent/api';
import { ConsentDocument } from '../features/consent/types';
import { ShieldCheck, Hash, ArrowLeft, Loader2, Calendar } from 'lucide-react';

interface LegalDocumentPageProps {
  fixedPurposeCode?: string;
}

export const LegalDocumentPage: React.FC<LegalDocumentPageProps> = ({ fixedPurposeCode }) => {
  const { purposeCode: paramCode } = useParams<{ purposeCode?: string }>();
  const purposeCode = fixedPurposeCode || paramCode || 'terms_of_service';

  const [doc, setDoc] = useState<ConsentDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchDoc = async () => {
      setLoading(true);
      setError('');
      try {
        const res = await consentApi.getDocumentByPurpose(purposeCode);
        setDoc(res);
      } catch (err: any) {
        setError('Document not found or unavailable');
      } finally {
        setLoading(false);
      }
    };
    fetchDoc();
  }, [purposeCode]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mb-2" />
        <p className="text-xs text-slate-500">Loading statutory document...</p>
      </div>
    );
  }

  if (error || !doc) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-12 text-center">
        <p className="text-sm text-red-600 mb-4">{error || 'Document not found'}</p>
        <Link to="/" className="text-xs text-indigo-600 font-semibold hover:underline">
          Return to Home
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-12 sm:px-6 space-y-6">
      <Link to="/" className="inline-flex items-center text-xs text-slate-500 hover:text-slate-800 transition">
        <ArrowLeft className="w-3.5 h-3.5 mr-1" /> Back to Marketplace
      </Link>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8 space-y-6">
        <div className="border-b border-slate-100 pb-5">
          <div className="flex items-center gap-2 mb-1">
            <ShieldCheck className="w-6 h-6 text-indigo-600" />
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
              Official Legal Disclosure (DPDP Act 2023)
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900">{doc.title}</h1>
          <div className="flex flex-wrap items-center gap-3 mt-3 text-xs text-slate-500">
            <span className="px-2 py-0.5 rounded-full bg-slate-100 font-semibold text-slate-700">
              Version {doc.version}
            </span>
            <span className="flex items-center gap-1 font-mono text-[11px] text-slate-600">
              <Hash className="w-3.5 h-3.5 text-slate-400" />
              SHA-256: {doc.sha256}
            </span>
          </div>
        </div>

        <div className="prose prose-sm max-w-none text-slate-700 space-y-4 text-xs leading-relaxed whitespace-pre-line">
          {doc.body_markdown}
        </div>

        <div className="pt-6 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-[11px] text-slate-500">
          <p>
            Effective from: {new Date(doc.effective_from).toLocaleDateString()}
          </p>
          <p className="italic">
            Note: Final legal phrasing subject to formal counsel review under DPDP Rules 2025.
          </p>
        </div>
      </div>
    </div>
  );
};
