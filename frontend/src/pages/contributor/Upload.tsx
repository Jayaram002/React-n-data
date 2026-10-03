import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadsApi } from '../../api/client';
import { 
  UploadCloud, FileText, Image as ImageIcon, AlertCircle, 
  CheckCircle2, Info, ShieldCheck, Loader2 
} from 'lucide-react';

export const ContributorUpload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [aiTrainingAllowed, setAiTrainingAllowed] = useState(true);
  const [consentAgreed, setConsentAgreed] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState('');
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a dataset file to upload.');
      return;
    }
    if (!consentAgreed) {
      setError('You must agree to the data rights and consent declaration.');
      return;
    }

    setError('');
    setIsUploading(true);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);
    formData.append('description', description);
    formData.append('ai_training_allowed', String(aiTrainingAllowed));
    formData.append('consent_agreed', String(consentAgreed));
    formData.append('consent_version', '1.0');

    try {
      const uploaded = await uploadsApi.uploadDataset(formData, (percent) => {
        setUploadProgress(percent);
      });
      navigate(`/contributor/uploads/${uploaded.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed. Please check file format and try again.');
      setIsUploading(false);
    }
  };

  const getFileCategoryIcon = () => {
    if (!file) return null;
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (['jpg', 'jpeg', 'png', 'webp'].includes(ext || '')) {
      return <ImageIcon className="h-8 w-8 text-indigo-500" />;
    }
    return <FileText className="h-8 w-8 text-emerald-500" />;
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
          <UploadCloud className="h-7 w-7 text-indigo-600" />
          <span>Upload Dataset</span>
        </h1>
        <p className="text-slate-600 text-sm mt-1">
          Upload image or tabular datasets. Files undergo automatic MIME integrity verification, PII detection, perceptual hashing, and metadata stripping.
        </p>
      </div>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center space-x-3 text-sm">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* File Dropzone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
            isDragging
              ? 'border-indigo-600 bg-indigo-50/50'
              : file
              ? 'border-emerald-400 bg-emerald-50/30'
              : 'border-slate-300 hover:border-indigo-400 bg-white'
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".csv,.json,.xlsx,.xls,.jpg,.jpeg,.png,.webp"
            className="hidden"
          />

          {file ? (
            <div className="flex flex-col items-center">
              {getFileCategoryIcon()}
              <p className="text-base font-semibold text-slate-900 mt-2">{file.name}</p>
              <p className="text-xs text-slate-500 mt-0.5">
                {(file.size / (1024 * 1024)).toFixed(2)} MB • Ready for pre-checks
              </p>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setFile(null);
                }}
                className="mt-3 text-xs text-red-600 hover:underline font-medium"
              >
                Choose different file
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <div className="p-3 bg-indigo-50 text-indigo-600 rounded-full mb-3">
                <UploadCloud className="h-8 w-8" />
              </div>
              <p className="text-sm font-semibold text-slate-800">
                Click to browse or drag and drop dataset file here
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Supported formats: Images (JPEG, PNG, WebP up to 15MB) or Tabular (CSV, JSON, XLSX up to 50MB)
              </p>
            </div>
          )}
        </div>

        {/* Dataset Details */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 space-y-4">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1">
              Dataset Title <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. High-Resolution Solar Flares Dataset or Q3 E-Commerce Transactions"
              className="w-full px-3.5 py-2 border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:outline-none text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1">
              Description & Context <span className="text-red-500">*</span>
            </label>
            <textarea
              required
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this dataset contains, collection methods, and intended use cases..."
              className="w-full px-3.5 py-2 border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:outline-none text-sm"
            />
          </div>

          {/* AI Training License Permissions */}
          <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-800">Allow AI Model Training License</p>
              <p className="text-xs text-slate-500">
                Allow buyers to use this data to train and fine-tune AI/ML foundation models
              </p>
            </div>
            <input
              type="checkbox"
              checked={aiTrainingAllowed}
              onChange={(e) => setAiTrainingAllowed(e.target.checked)}
              className="h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
            />
          </div>
        </div>

        {/* Consent & Rights Declaration */}
        <div className="bg-indigo-50/60 border border-indigo-100 p-5 rounded-xl space-y-3">
          <div className="flex items-start space-x-2">
            <ShieldCheck className="h-5 w-5 text-indigo-600 mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="text-sm font-bold text-indigo-900">Ownership & Consent Declaration (v1.0)</h3>
              <p className="text-xs text-indigo-700 mt-0.5 leading-relaxed">
                By uploading, I explicitly warrant and represent that: (1) I hold all copyright and proprietary rights to this dataset; (2) any identifiable individuals have consented to inclusion and distribution; (3) no trade secrets, illegal materials, or unmasked sensitive PII are present.
              </p>
            </div>
          </div>

          <label className="flex items-center space-x-2.5 pt-2 cursor-pointer">
            <input
              type="checkbox"
              required
              checked={consentAgreed}
              onChange={(e) => setConsentAgreed(e.target.checked)}
              className="h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
            />
            <span className="text-xs font-semibold text-slate-800">
              I agree to the Contributor Declaration & Terms of Distribution
            </span>
          </label>
        </div>

        {/* Upload Progress Bar */}
        {isUploading && (
          <div className="bg-white p-4 rounded-xl border border-slate-200">
            <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1.5">
              <span>Uploading & executing pre-checks...</span>
              <span>{uploadProgress}%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div
                className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* Submit CTA */}
        <button
          type="submit"
          disabled={isUploading}
          className="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg shadow-sm flex items-center justify-center space-x-2 disabled:opacity-50 transition-colors"
        >
          {isUploading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>Processing Dataset Pre-checks...</span>
            </>
          ) : (
            <>
              <UploadCloud className="h-5 w-5" />
              <span>Submit for AI Analysis</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
};
