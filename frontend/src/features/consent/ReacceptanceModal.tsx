import React, { useState, useEffect } from 'react';
import { AlertTriangle, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { ConsentDocument } from './types';
import { consentApi } from './api';
import { useAuth } from '../../context/AuthContext';

export interface ReacceptanceModalProps {
  isOpen?: boolean;
  termsDoc?: ConsentDocument | null;
  privacyDoc?: ConsentDocument | null;
  onAccepted?: () => void;
}

export const ReacceptanceModal: React.FC<ReacceptanceModalProps> = ({
  isOpen: propIsOpen,
  termsDoc: propTermsDoc,
  privacyDoc: propPrivacyDoc,
  onAccepted: propOnAccepted,
}) => {
  const { user } = useAuth();
  const [internalOpen, setInternalOpen] = useState(false);
  const [internalTermsDoc, setInternalTermsDoc] = useState<ConsentDocument | null>(null);
  const [internalPrivacyDoc, setInternalPrivacyDoc] = useState<ConsentDocument | null>(null);

  const [termsAgreed, setTermsAgreed] = useState(false);
  const [privacyAgreed, setPrivacyAgreed] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // If props not provided, evaluate autonomously based on logged in user's version vs active document versions
  useEffect(() => {
    if (propIsOpen !== undefined) return;
    if (!user) {
      setInternalOpen(false);
      return;
    }

    const checkDocumentVersions = async () => {
      try {
        const docs = await consentApi.getActiveDocuments();
        const activeTerms = docs.find((d) => d.purpose_code === 'terms_of_service');
        const activePrivacy = docs.find((d) => d.purpose_code === 'privacy_notice');

        let needsReacceptance = false;
        let tDoc: ConsentDocument | null = null;
        let pDoc: ConsentDocument | null = null;

        if (activeTerms && user.terms_accepted_version && user.terms_accepted_version !== activeTerms.version) {
          needsReacceptance = true;
          tDoc = activeTerms;
        }
        if (activePrivacy && user.privacy_accepted_version && user.privacy_accepted_version !== activePrivacy.version) {
          needsReacceptance = true;
          pDoc = activePrivacy;
        }

        if (needsReacceptance) {
          setInternalTermsDoc(tDoc);
          setInternalPrivacyDoc(pDoc);
          setInternalOpen(true);
        } else {
          setInternalOpen(false);
        }
      } catch (err) {
        console.error('Failed to check active document versions for reacceptance', err);
      }
    };

    checkDocumentVersions();
  }, [user, propIsOpen]);

  const isOpen = propIsOpen !== undefined ? propIsOpen : internalOpen;
  const termsDoc = propTermsDoc !== undefined ? propTermsDoc : internalTermsDoc;
  const privacyDoc = propPrivacyDoc !== undefined ? propPrivacyDoc : internalPrivacyDoc;

  if (!isOpen || (!termsDoc && !privacyDoc)) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (termsDoc && !termsAgreed) {
      setError('You must accept the updated Terms of Service to continue.');
      return;
    }
    if (privacyDoc && !privacyAgreed) {
      setError('You must accept the updated Privacy Notice to continue.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await consentApi.reacceptConsent({
        terms_accepted: termsAgreed,
        privacy_accepted: privacyAgreed,
      });
      if (propOnAccepted) {
        propOnAccepted();
      } else {
        setInternalOpen(false);
        window.location.reload();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to record re-acceptance. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/70 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-xl w-full p-6 border border-slate-100">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center flex-shrink-0">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900">Legal Policies Updated</h3>
            <p className="text-xs text-slate-500">
              India DPDP Act, 2023 & Rules 2025 Statutory Notice
            </p>
          </div>
        </div>

        <p className="text-xs text-slate-600 mb-5 leading-relaxed">
          We have updated our compliance documents. Under Indian data protection principles, purpose-specific re-consent is required when terms or privacy notices evolve.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {termsDoc && (
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs">
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-bold text-slate-800">{termsDoc.title}</span>
                <span className="text-[10px] font-semibold bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                  v{termsDoc.version}
                </span>
              </div>
              <p className="text-slate-500 text-[11px] mb-2 line-clamp-2">
                {termsDoc.body_markdown.substring(0, 150)}...
              </p>
              <label className="flex items-center gap-2 cursor-pointer pt-1 border-t border-slate-200/60">
                <input
                  type="checkbox"
                  checked={termsAgreed}
                  onChange={(e) => setTermsAgreed(e.target.checked)}
                  className="rounded text-blue-600 border-slate-300 focus:ring-blue-500 w-4 h-4 cursor-pointer"
                />
                <span className="font-medium text-slate-900">I have read and accept the updated Terms of Service</span>
              </label>
            </div>
          )}

          {privacyDoc && (
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs">
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-bold text-slate-800">{privacyDoc.title}</span>
                <span className="text-[10px] font-semibold bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                  v{privacyDoc.version}
                </span>
              </div>
              <p className="text-slate-500 text-[11px] mb-2 line-clamp-2">
                {privacyDoc.body_markdown.substring(0, 150)}...
              </p>
              <label className="flex items-center gap-2 cursor-pointer pt-1 border-t border-slate-200/60">
                <input
                  type="checkbox"
                  checked={privacyAgreed}
                  onChange={(e) => setPrivacyAgreed(e.target.checked)}
                  className="rounded text-blue-600 border-slate-300 focus:ring-blue-500 w-4 h-4 cursor-pointer"
                />
                <span className="font-medium text-slate-900">I have read and accept the updated Privacy Notice</span>
              </label>
            </div>
          )}

          <div className="pt-2 flex justify-end gap-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl shadow-sm transition disabled:opacity-50 flex items-center justify-center gap-1.5"
            >
              <CheckCircle2 className="w-4 h-4" />
              {isSubmitting ? 'Recording Consent...' : 'Accept & Continue'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
