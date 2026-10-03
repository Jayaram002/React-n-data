import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadsApi, formatErrorMessage } from '../../api/client';
import { consentApi } from '../../features/consent/api';
import { ConsentDocument } from '../../features/consent/types';
import { ConsentCheckbox } from '../../features/consent/ConsentCheckbox';
import { 
  UploadCloud, FileText, Image as ImageIcon, AlertCircle, 
  CheckCircle2, Info, ShieldCheck, Loader2, Paperclip, Lock, HelpCircle 
} from 'lucide-react';

export const ContributorUpload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  
  // DPDP Consent Checkboxes (Unticked by default, non-bundled)
  const [contributorRightsAgreed, setContributorRightsAgreed] = useState(false);
  const [platformLicenseAgreed, setPlatformLicenseAgreed] = useState(false);
  const [personalDataAttestationAgreed, setPersonalDataAttestationAgreed] = useState(false);
  const [aiTrainingAgreed, setAiTrainingAgreed] = useState(false); // Default OFF

  // Personal Data Attestation Sub-fields
  const [personalDataStatus, setPersonalDataStatus] = useState<'none' | 'anonymized' | 'contains_personal_data'>('none');
  const [lawfulBasis, setLawfulBasis] = useState('Explicit Consent');
  const [lawfulBasisNote, setLawfulBasisNote] = useState('');
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);

  // Active documents for modal inspection
  const [activeDocs, setActiveDocs] = useState<Record<string, ConsentDocument>>({});

  // UI state
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const evidenceInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const docs = await consentApi.getActiveDocuments();
        const map: Record<string, ConsentDocument> = {};
        docs.forEach((d) => {
          map[d.purpose_code] = d;
        });
        setActiveDocs(map);
      } catch (err) {
        console.error('Failed to load active consent documents', err);
      }
    };
    fetchDocs();
  }, []);

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

  const handleEvidenceFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setEvidenceFile(e.target.files[0]);
    }
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!file) {
      newErrors.file = 'Please select a dataset file to upload.';
    }
    if (!title.trim()) {
      newErrors.title = 'Title is required.';
    }
    if (!description.trim()) {
      newErrors.description = 'Description is required.';
    }
    if (!contributorRightsAgreed) {
      newErrors.contributorRights = 'You must warrant ownership and authorization to proceed.';
    }
    if (!platformLicenseAgreed) {
      newErrors.platformLicense = 'You must grant the platform listing license to publish or monetize.';
    }
    if (!personalDataAttestationAgreed) {
      newErrors.personalDataAttestation = 'You must complete the DPDP personal data attestation.';
    }
    if (personalDataStatus === 'contains_personal_data' && !lawfulBasis.trim()) {
      newErrors.lawfulBasis = 'A valid lawful basis is required when dataset contains personal data.';
    }

    setErrors(newErrors);
    if (Object.keys(newErrors).length > 0) {
      setError('Please review required legal consents and highlighted fields.');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setError('');
    setIsUploading(true);
    setUploadProgress(0);

    const formData = new FormData();
    if (file) formData.append('file', file);
    formData.append('title', title);
    formData.append('description', description);
    formData.append('contributor_rights_agreed', 'true');
    formData.append('platform_license_agreed', 'true');
    formData.append('personal_data_attestation_agreed', 'true');
    formData.append('ai_training_agreed', String(aiTrainingAgreed));
    formData.append('personal_data_status', personalDataStatus);
    formData.append('consent_version', '1.0');

    if (personalDataStatus === 'contains_personal_data') {
      formData.append('lawful_basis', lawfulBasis);
      if (lawfulBasisNote.trim()) {
        formData.append('lawful_basis_note', lawfulBasisNote.trim());
      }
      if (evidenceFile) {
        formData.append('evidence_file', evidenceFile);
      }
    }

    try {
      const uploaded = await uploadsApi.uploadDataset(formData, (percent) => {
        setUploadProgress(percent);
      });
      navigate(`/contributor/uploads/${uploaded.id}`);
    } catch (err: any) {
      setError(formatErrorMessage(err, 'Upload failed. Please check file format and try again.'));
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
          Upload image or tabular datasets. Datasets undergo automated MIME verification, PII detection, perceptual hashing, and DPDP compliance screening.
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center space-x-3 text-red-800 text-sm">
          <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Dropzone File Upload */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${
            isDragging
              ? 'border-indigo-500 bg-indigo-50/50 scale-[1.01]'
              : file
              ? 'border-emerald-300 bg-emerald-50/20'
              : 'border-slate-300 hover:border-slate-400 bg-white'
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".jpg,.jpeg,.png,.webp,.csv,.json"
            className="hidden"
          />

          {file ? (
            <div className="flex flex-col items-center">
              <div className="h-12 w-12 rounded-xl bg-white shadow-sm border border-slate-200 flex items-center justify-center mb-3">
                {getFileCategoryIcon()}
              </div>
              <h3 className="text-sm font-semibold text-slate-900">{file.name}</h3>
              <p className="text-xs text-slate-500 mt-1">
                {(file.size / (1024 * 1024)).toFixed(2)} MB • Click or drag to replace
              </p>
              <div className="mt-3 flex items-center space-x-1.5 text-xs text-emerald-600 font-medium bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>File attached ready for pre-checks</span>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <div className="h-12 w-12 rounded-xl bg-indigo-50 flex items-center justify-center mb-3">
                <UploadCloud className="h-6 w-6 text-indigo-600" />
              </div>
              <h3 className="text-sm font-semibold text-slate-900">
                Choose a file or drag & drop here
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Supports Images (JPG, PNG, WebP) and Tabular (CSV, JSON) up to 100MB
              </p>
              {errors.file && (
                <p className="text-xs text-red-600 font-medium mt-2">{errors.file}</p>
              )}
            </div>
          )}
        </div>

        {/* Metadata Fields */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
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
            {errors.title && <p className="text-xs text-red-600 mt-1">{errors.title}</p>}
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
              placeholder="Describe what this dataset contains, collection methodology, schema attributes, and intended use cases..."
              className="w-full px-3.5 py-2 border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:outline-none text-sm"
            />
            {errors.description && <p className="text-xs text-red-600 mt-1">{errors.description}</p>}
          </div>
        </div>

        {/* DPDP Act 2023 / Rules 2025 Separate Consent Declarations */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-5">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <ShieldCheck className="h-5 w-5 text-indigo-600" />
            <div>
              <h3 className="text-sm font-bold text-slate-900">DPDP Statutory Consents & Attestations</h3>
              <p className="text-xs text-slate-500">
                In compliance with India's Digital Personal Data Protection Act 2023: consents must be purpose-specific, unbundled, and revocable.
              </p>
            </div>
          </div>

          {/* 1. Contributor Rights Warranty (Required) */}
          <ConsentCheckbox
            id="contributor_rights_agreed"
            checked={contributorRightsAgreed}
            onChange={setContributorRightsAgreed}
            label="Contributor Rights & Ownership Warranty"
            summary="I warrant that I am the sole owner or authorized custodian of this dataset and possess all legal rights to license and distribute it without infringing any third-party intellectual property or confidentiality obligations."
            document={activeDocs['contributor_rights_warranty']}
            documentPurposeCode="contributor_rights_warranty"
            required={true}
            error={errors.contributorRights}
          />

          {/* 2. Platform Listing License (Required) */}
          <ConsentCheckbox
            id="platform_license_agreed"
            checked={platformLicenseAgreed}
            onChange={setPlatformLicenseAgreed}
            label="Platform Listing & Distribution License"
            summary="I grant React n Data a non-exclusive license to host, generate analytical previews, index, and sub-license this dataset through the marketplace on an 80/20 platform ledger basis."
            document={activeDocs['platform_listing_license']}
            documentPurposeCode="platform_listing_license"
            required={true}
            error={errors.platformLicense}
          />

          {/* 3. Personal Data Attestation (Required) with Sub-form */}
          <div className="space-y-3">
            <ConsentCheckbox
              id="personal_data_attestation_agreed"
              checked={personalDataAttestationAgreed}
              onChange={setPersonalDataAttestationAgreed}
              label="Third-Party Data & DPDP Attestation"
              summary="I confirm compliance with Section 6 of the DPDP Act regarding personal data, data principals' notices, and de-identification standards."
              document={activeDocs['third_party_data_attestation']}
              documentPurposeCode="third_party_data_attestation"
              required={true}
              error={errors.personalDataAttestation}
            />

            {/* Nested Personal Data Details */}
            <div className="ml-7 p-4 bg-slate-50 rounded-xl border border-slate-200/80 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Personal Data Classification <span className="text-red-500">*</span>
                </label>
                <select
                  value={personalDataStatus}
                  onChange={(e) => setPersonalDataStatus(e.target.value as any)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs bg-white focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="none">No personal or identifiable individuals present (synthetic/environmental/telemetry)</option>
                  <option value="anonymized">Data contains anonymized or de-identified subjects (irreversibly masked)</option>
                  <option value="contains_personal_data">Dataset contains personal data of data principals (Requires Lawful Basis)</option>
                </select>
              </div>

              {personalDataStatus === 'contains_personal_data' && (
                <div className="space-y-3 pt-2 border-t border-slate-200 animate-in fade-in">
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-xs flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                    <span>
                      Datasets containing personal data will be held for Admin Moderation before being published to the marketplace.
                    </span>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Lawful Basis under DPDP Section 6 <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={lawfulBasis}
                      onChange={(e) => setLawfulBasis(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs bg-white focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="Explicit Consent">Explicit Notice & Consent from Data Principals</option>
                      <option value="Legitimate Uses / Employment">Legitimate Uses / Employment or Commercial Contract</option>
                      <option value="Compliance with Law">Compliance with Law or Judicial Directive</option>
                      <option value="Statutory Public Function">Statutory Public Function or Health Emergency</option>
                      <option value="Other">Other Documented Lawful Basis</option>
                    </select>
                    {errors.lawfulBasis && (
                      <p className="text-xs text-red-600 mt-1">{errors.lawfulBasis}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Basis Notes & Consent Collection Context (Optional)
                    </label>
                    <input
                      type="text"
                      value={lawfulBasisNote}
                      onChange={(e) => setLawfulBasisNote(e.target.value)}
                      placeholder="e.g. Consent forms signed on 2026-03-12 for diagnostic image study"
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs bg-white focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1 flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <Lock className="w-3.5 h-3.5 text-indigo-600" />
                        Private Consent Evidence File (Optional)
                      </span>
                      <span className="text-[10px] text-slate-500 font-normal">Admin & Compliance view only</span>
                    </label>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => evidenceInputRef.current?.click()}
                        className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-100 flex items-center gap-1.5 transition"
                      >
                        <Paperclip className="w-3.5 h-3.5" />
                        {evidenceFile ? 'Replace Evidence File' : 'Upload Evidence (PDF / Consent Forms)'}
                      </button>
                      {evidenceFile && (
                        <span className="text-xs text-slate-600 truncate max-w-xs font-medium">
                          {evidenceFile.name} ({(evidenceFile.size / 1024).toFixed(1)} KB)
                        </span>
                      )}
                    </div>
                    <input
                      type="file"
                      ref={evidenceInputRef}
                      onChange={handleEvidenceFileChange}
                      accept=".pdf,.png,.jpg,.jpeg,.zip"
                      className="hidden"
                    />
                    <p className="text-[11px] text-slate-500 mt-1">
                      Uploaded evidence is stored in a private, encrypted storage vault inaccessible to public buyers.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 4. AI Training Use (Optional - Default OFF) */}
          <ConsentCheckbox
            id="ai_training_agreed"
            checked={aiTrainingAgreed}
            onChange={setAiTrainingAgreed}
            label="AI Model Training & Fine-Tuning Authorization"
            summary="Allow commercial buyers to utilize this dataset for algorithmic training, LLM fine-tuning, and neural network optimization. Unticked by default."
            document={activeDocs['ai_training_use']}
            documentPurposeCode="ai_training_use"
            required={false}
          />
        </div>

        {/* Upload Progress Bar */}
        {isUploading && (
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1.5">
              <span>Uploading dataset & executing pre-checks...</span>
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
          className="w-full py-3.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl shadow-sm flex items-center justify-center space-x-2 disabled:opacity-50 transition-colors"
        >
          {isUploading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>Verifying Integrity & Running Pre-checks...</span>
            </>
          ) : (
            <>
              <UploadCloud className="h-5 w-5" />
              <span>Submit Dataset for AI Quality Analysis</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
};
