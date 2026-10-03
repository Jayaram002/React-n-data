import React from 'react';
import { X, ShieldCheck, FileText, CheckCircle2 } from 'lucide-react';
import { ConsentDocument } from './types';

interface ConsentModalProps {
  isOpen: boolean;
  onClose: () => void;
  document: ConsentDocument | null;
  onAccept?: () => void;
  isAccepted?: boolean;
}

export const ConsentModal: React.FC<ConsentModalProps> = ({
  isOpen,
  onClose,
  document,
  onAccept,
  isAccepted = false,
}) => {
  if (!isOpen || !document) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[85vh] flex flex-col border border-slate-100 animate-in fade-in zoom-in-95 duration-200"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="p-6 border-b border-slate-100 flex items-start justify-between bg-slate-50/50 rounded-t-2xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-slate-900">{document.title}</h3>
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-700">
                  v{document.version}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Effective from: {new Date(document.effective_from).toLocaleDateString()}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* SHA256 Integrity Verification Badge */}
        <div className="px-6 py-2.5 bg-emerald-50 border-b border-emerald-100 flex items-center gap-2 text-xs text-emerald-800">
          <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <div className="truncate">
            <span className="font-semibold">Immutable Document SHA-256: </span>
            <code className="font-mono text-[11px] bg-emerald-100/60 px-1 py-0.5 rounded text-emerald-900">
              {document.sha256}
            </code>
          </div>
        </div>

        {/* Body content */}
        <div className="p-6 overflow-y-auto space-y-4 text-slate-700 text-sm leading-relaxed prose prose-slate max-w-none">
          <div className="whitespace-pre-line font-sans">{document.body_markdown}</div>
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-slate-100 flex items-center justify-between bg-slate-50/60 rounded-b-2xl">
          <div className="text-xs text-slate-500">
            Protected under Digital Personal Data Protection (DPDP) Act, 2023 & Rules 2025.
          </div>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-200/60 rounded-xl transition"
            >
              Close
            </button>
            {onAccept && !isAccepted && (
              <button
                onClick={() => {
                  onAccept();
                  onClose();
                }}
                className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-sm transition flex items-center gap-1.5"
              >
                <CheckCircle2 className="w-4 h-4" />
                Acknowledge & Accept
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
