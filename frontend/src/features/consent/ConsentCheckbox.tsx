import React, { useState } from 'react';
import { ExternalLink, Check } from 'lucide-react';
import { ConsentDocument } from './types';
import { ConsentModal } from './ConsentModal';

interface ConsentCheckboxProps {
  id: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  summary: string;
  document?: ConsentDocument | null;
  documentPurposeCode?: string;
  required?: boolean;
  error?: string;
  disabled?: boolean;
}

export const ConsentCheckbox: React.FC<ConsentCheckboxProps> = ({
  id,
  checked,
  onChange,
  label,
  summary,
  document,
  required = false,
  error,
  disabled = false,
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <div className="space-y-1.5">
      <div className={`flex items-start gap-3 p-3.5 rounded-xl border transition ${
        checked
          ? 'bg-blue-50/40 border-blue-200'
          : error
          ? 'bg-red-50/30 border-red-200'
          : 'bg-white border-slate-200 hover:border-slate-300'
      }`}>
        <div className="flex items-center h-5 mt-0.5">
          <input
            id={id}
            type="checkbox"
            checked={checked}
            disabled={disabled}
            onChange={(e) => onChange(e.target.checked)}
            className="w-4 h-4 text-blue-600 bg-white border-slate-300 rounded focus:ring-blue-500 focus:ring-2 cursor-pointer disabled:opacity-50"
          />
        </div>
        <div className="flex-1 text-xs">
          <label htmlFor={id} className="font-semibold text-slate-900 cursor-pointer flex items-center gap-1.5">
            {label}
            {required && <span className="text-red-500 font-bold">*</span>}
            {!required && (
              <span className="text-[10px] font-medium bg-slate-100 text-slate-600 px-1.5 py-0.2 rounded">
                Optional
              </span>
            )}
          </label>
          <p className="text-slate-600 mt-0.5 leading-relaxed">{summary}</p>
          {document && (
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-600 hover:text-blue-800 hover:underline mt-1.5"
            >
              <span>Read {document.title} (v{document.version})</span>
              <ExternalLink className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
      {error && <p className="text-[11px] font-medium text-red-600 ml-1">{error}</p>}

      {document && (
        <ConsentModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          document={document}
          onAccept={() => onChange(true)}
          isAccepted={checked}
        />
      )}
    </div>
  );
};
