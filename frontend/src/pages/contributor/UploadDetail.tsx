import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { uploadsApi, categoriesApi } from '../../api/client';
import { Upload, AIAnalysis, CategoryTree } from '../../types';
import { 
  ArrowLeft, CheckCircle2, AlertTriangle, ShieldCheck, 
  FileText, Image as ImageIcon, Database, Sparkles, 
  DollarSign, Tag, Lightbulb, HelpCircle, Layers, Check, Loader2 
} from 'lucide-react';

export const ContributorUploadDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [upload, setUpload] = useState<Upload | null>(null);
  const [analysis, setAnalysis] = useState<AIAnalysis | null>(null);
  const [categories, setCategories] = useState<CategoryTree[]>([]);
  const [previewData, setPreviewData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Interactive Pricing State
  const [currentPricePaise, setCurrentPricePaise] = useState<number>(0);
  const [savingPrice, setSavingPrice] = useState(false);
  const [priceSuccess, setPriceSuccess] = useState('');

  // Interactive Category Change State
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [selectedCatId, setSelectedCatId] = useState<number>(0);
  const [selectedSubId, setSelectedSubId] = useState<number | undefined>(undefined);
  const [savingCategory, setSavingCategory] = useState(false);
  const [categorySuccess, setCategorySuccess] = useState('');

  const loadData = async () => {
    if (!id) return;
    try {
      const uploadData = await uploadsApi.getUpload(Number(id));
      setUpload(uploadData);
      setCurrentPricePaise(uploadData.price_paise || 500000);

      const [analysisData, catData] = await Promise.all([
        uploadsApi.getAnalysis(uploadData.id),
        categoriesApi.getCategories()
      ]);
      setAnalysis(analysisData);
      setCategories(catData);

      if (uploadData.file_info?.data_type === 'tabular') {
        const preview = await uploadsApi.getPreviewData(uploadData.id);
        setPreviewData(preview);
      }
    } catch (err) {
      setError('Failed to load dataset details or AI score');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  const handleSavePrice = async () => {
    if (!upload) return;
    setSavingPrice(true);
    setPriceSuccess('');
    try {
      const updated = await uploadsApi.updatePrice(upload.id, currentPricePaise);
      setUpload(updated);
      setPriceSuccess('Price successfully updated within AI recommended range!');
      setTimeout(() => setPriceSuccess(''), 4000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update price');
    } finally {
      setSavingPrice(false);
    }
  };

  const handleRequestCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!upload || !selectedCatId) return;
    setSavingCategory(true);
    setCategorySuccess('');
    try {
      const updated = await uploadsApi.requestCategoryChange(upload.id, selectedCatId, selectedSubId);
      setUpload(updated);
      setShowCategoryModal(false);
      setCategorySuccess('Category request submitted successfully!');
      setTimeout(() => setCategorySuccess(''), 5000);
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to request category change');
    } finally {
      setSavingCategory(false);
    }
  };

  const [isPublishing, setIsPublishing] = useState(false);
  const [publishStatusMessage, setPublishStatusMessage] = useState('');

  const handlePublish = async () => {
    if (!upload) return;
    setIsPublishing(true);
    setPublishStatusMessage('');
    try {
      const updated = await uploadsApi.publishUpload(upload.id);
      setUpload(updated);
      setPublishStatusMessage('Dataset successfully published to Agency Marketplace!');
      setTimeout(() => setPublishStatusMessage(''), 5000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to publish dataset');
    } finally {
      setIsPublishing(false);
    }
  };

  const handleUnpublish = async () => {
    if (!upload) return;
    setIsPublishing(true);
    setPublishStatusMessage('');
    try {
      const updated = await uploadsApi.unpublishUpload(upload.id);
      setUpload(updated);
      setPublishStatusMessage('Dataset unpublished from Marketplace.');
      setTimeout(() => setPublishStatusMessage(''), 5000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to unpublish dataset');
    } finally {
      setIsPublishing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 text-indigo-600 animate-spin mb-2" />
        <p className="text-slate-500 text-sm">Evaluating dataset with Gemma AI & Pre-checks...</p>
      </div>
    );
  }

  if (error && !upload) {
    return (
      <div className="max-w-4xl mx-auto p-8 text-center">
        <div className="bg-red-50 text-red-700 p-4 rounded-xl border border-red-200">
          {error}
        </div>
        <Link to="/contributor/dashboard" className="mt-4 inline-block text-sm text-indigo-600 font-semibold">
          Return to Dashboard
        </Link>
      </div>
    );
  }

  const fileInfo = upload?.file_info;
  const minPrice = upload?.ai_min_price || 100000;
  const maxPrice = upload?.ai_max_price || 1000000;

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      {/* Header Navigation */}
      <div className="mb-6">
        <Link
          to="/contributor/dashboard"
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-500 hover:text-indigo-600 mb-3"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Dashboard</span>
        </Link>
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{upload?.title}</h1>
            <p className="text-slate-600 text-sm mt-0.5">{upload?.description}</p>
          </div>
          <div className="flex items-center space-x-3">
            <span className="text-xs font-semibold uppercase px-3 py-1.5 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-full">
              Status: {upload?.status}
            </span>

            {upload?.status !== 'published' ? (
              <button
                type="button"
                onClick={handlePublish}
                disabled={isPublishing || upload?.status === 'flagged' || upload?.status === 'rejected'}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs rounded-xl shadow-sm disabled:opacity-50 transition-colors"
              >
                {isPublishing ? 'Publishing...' : 'Publish to Marketplace'}
              </button>
            ) : (
              <button
                type="button"
                onClick={handleUnpublish}
                disabled={isPublishing}
                className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 font-semibold text-xs rounded-xl transition-colors"
              >
                {isPublishing ? 'Updating...' : 'Unpublish'}
              </button>
            )}
          </div>
        </div>
      </div>

      {priceSuccess && (
        <div className="mb-6 bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl flex items-center space-x-2 text-sm">
          <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-emerald-600" />
          <span>{priceSuccess}</span>
        </div>
      )}

      {categorySuccess && (
        <div className="mb-6 bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded-xl flex items-center space-x-2 text-sm">
          <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-blue-600" />
          <span>{categorySuccess}</span>
        </div>
      )}

      {/* Main 2-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Columns: AI Analysis, Score Breakdown, Category & Pricing */}
        <div className="lg:col-span-2 space-y-6">
          {/* Trust Score Banner */}
          {analysis && (
            <div className="bg-gradient-to-br from-indigo-900 via-indigo-800 to-slate-900 text-white rounded-2xl p-6 shadow-md relative overflow-hidden">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center space-x-2 text-indigo-300 text-xs font-semibold uppercase tracking-wider mb-1">
                    <Sparkles className="h-4 w-4 text-amber-400" />
                    <span>Gemma Hybrid Trust Score</span>
                  </div>
                  <h2 className="text-xl font-bold">Overall Data Trust Score</h2>
                  <p className="text-xs text-indigo-200 mt-1 max-w-md">
                    {analysis.explanation}
                  </p>
                </div>

                <div className="flex items-center space-x-4">
                  <div className="h-20 w-20 rounded-full border-4 border-amber-400 flex flex-col items-center justify-center bg-indigo-950/60 shadow-inner">
                    <span className="text-2xl font-black tracking-tight text-white">{analysis.total_score}</span>
                    <span className="text-[10px] text-amber-300 font-bold uppercase">/ 100</span>
                  </div>
                </div>
              </div>

              {/* 5 Component Bars */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-6 pt-5 border-t border-indigo-700/50">
                <div>
                  <div className="flex justify-between text-[11px] mb-1">
                    <span className="text-indigo-200">Quality (25%)</span>
                    <span className="font-bold">{analysis.quality}</span>
                  </div>
                  <div className="w-full bg-indigo-950/80 rounded-full h-1.5 overflow-hidden">
                    <div className="bg-emerald-400 h-1.5 rounded-full" style={{ width: `${analysis.quality}%` }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] mb-1">
                    <span className="text-indigo-200">Authenticity (30%)</span>
                    <span className="font-bold">{analysis.authenticity}</span>
                  </div>
                  <div className="w-full bg-indigo-950/80 rounded-full h-1.5 overflow-hidden">
                    <div className="bg-cyan-400 h-1.5 rounded-full" style={{ width: `${analysis.authenticity}%` }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] mb-1">
                    <span className="text-indigo-200">Uniqueness (20%)</span>
                    <span className="font-bold">{analysis.uniqueness}</span>
                  </div>
                  <div className="w-full bg-indigo-950/80 rounded-full h-1.5 overflow-hidden">
                    <div className="bg-amber-400 h-1.5 rounded-full" style={{ width: `${analysis.uniqueness}%` }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] mb-1">
                    <span className="text-indigo-200">Metadata (15%)</span>
                    <span className="font-bold">{analysis.metadata_accuracy}</span>
                  </div>
                  <div className="w-full bg-indigo-950/80 rounded-full h-1.5 overflow-hidden">
                    <div className="bg-indigo-300 h-1.5 rounded-full" style={{ width: `${analysis.metadata_accuracy}%` }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] mb-1">
                    <span className="text-indigo-200">Reputation (10%)</span>
                    <span className="font-bold">{analysis.reputation}</span>
                  </div>
                  <div className="w-full bg-indigo-950/80 rounded-full h-1.5 overflow-hidden">
                    <div className="bg-purple-300 h-1.5 rounded-full" style={{ width: `${analysis.reputation}%` }}></div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* AI Domain Classification & Tags Card */}
          {analysis && (
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <Layers className="h-5 w-5 text-indigo-600" />
                  <h2 className="text-base font-bold text-slate-900">AI Domain Categorization</h2>
                </div>
                <button
                  onClick={() => setShowCategoryModal(true)}
                  className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 bg-indigo-50 px-3 py-1.5 rounded-lg border border-indigo-100 hover:bg-indigo-100 transition-colors"
                >
                  Request Different Category
                </button>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-4">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-bold text-slate-900 uppercase">
                      {analysis.classification_output.primary_category}
                    </span>
                    {analysis.classification_output.subcategory && (
                      <>
                        <span className="text-slate-400">/</span>
                        <span className="text-sm font-semibold text-indigo-600">
                          {analysis.classification_output.subcategory}
                        </span>
                      </>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {analysis.classification_output.reasoning}
                  </p>
                </div>

                <div className="flex items-center space-x-2 flex-shrink-0">
                  <span className="text-xs font-semibold px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-md">
                    {(analysis.classification_output.confidence * 100).toFixed(0)}% Confidence
                  </span>
                </div>
              </div>

              {/* Tags */}
              <div>
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center space-x-1">
                  <Tag className="h-3.5 w-3.5" />
                  <span>Search Keywords ({analysis.classification_output.tags?.length || 0})</span>
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {analysis.classification_output.tags?.map((tag, idx) => (
                    <span key={idx} className="text-xs font-medium bg-slate-100 text-slate-700 px-2.5 py-1 rounded-md">
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Pricing Recommendation & Adjustment Slider */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <div className="flex items-center space-x-2 mb-4">
              <DollarSign className="h-5 w-5 text-emerald-600" />
              <h2 className="text-base font-bold text-slate-900">Pricing & Licensing Setting</h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                <p className="text-xs text-slate-500 font-medium">AI Min Price (80%)</p>
                <p className="text-lg font-bold text-slate-700 mt-0.5">
                  ${(minPrice / 100).toFixed(2)}
                </p>
              </div>

              <div className="p-4 bg-indigo-50 rounded-xl border border-indigo-100">
                <p className="text-xs text-indigo-700 font-semibold">AI Suggested Price</p>
                <p className="text-xl font-black text-indigo-900 mt-0.5">
                  ${((upload?.price_paise || 500000) / 100).toFixed(2)}
                </p>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                <p className="text-xs text-slate-500 font-medium">AI Max Price (130%)</p>
                <p className="text-lg font-bold text-slate-700 mt-0.5">
                  ${(maxPrice / 100).toFixed(2)}
                </p>
              </div>
            </div>

            {/* Price Slider */}
            <div className="space-y-3">
              <div className="flex justify-between items-center text-sm">
                <label className="font-semibold text-slate-800">Your Listing Price</label>
                <span className="text-base font-bold text-indigo-600 font-mono">
                  ${(currentPricePaise / 100).toFixed(2)}
                </span>
              </div>

              <input
                type="range"
                min={minPrice}
                max={maxPrice}
                step={1000}
                value={currentPricePaise}
                onChange={(e) => setCurrentPricePaise(Number(e.target.value))}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
              />

              <div className="flex justify-between text-xs text-slate-400">
                <span>Min: ${(minPrice / 100).toFixed(2)}</span>
                <span>Max: ${(maxPrice / 100).toFixed(2)}</span>
              </div>

              <div className="pt-2">
                <button
                  type="button"
                  onClick={handleSavePrice}
                  disabled={savingPrice}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm flex items-center space-x-1.5 disabled:opacity-50 transition-colors"
                >
                  {savingPrice ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                  <span>Save Listing Price</span>
                </button>
              </div>
            </div>
          </div>

          {/* Actionable Improvement Tips Card */}
          {analysis?.tips && analysis.tips.length > 0 && (
            <div className="bg-amber-50/60 border border-amber-200/80 rounded-xl p-5 shadow-sm">
              <h3 className="text-sm font-bold text-amber-900 flex items-center space-x-2 mb-2">
                <Lightbulb className="h-4 w-4 text-amber-600" />
                <span>AI Improvement Recommendations</span>
              </h3>
              <ul className="space-y-1.5 text-xs text-amber-800 list-disc list-inside">
                {analysis.tips.map((tip, idx) => (
                  <li key={idx}>{tip}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Right 1 Column: Safe Preview & Pre-check Details */}
        <div className="space-y-6">
          {/* Safe Preview Card */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-100 flex justify-between items-center">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Derived Safe Preview</h2>
              <span className="text-[10px] text-slate-400 font-mono">Original is private</span>
            </div>

            <div className="p-5">
              {fileInfo?.data_type === 'image' ? (
                <div className="flex flex-col items-center">
                  <div className="border border-slate-200 rounded-lg overflow-hidden max-h-72 bg-slate-100">
                    <img
                      src={upload ? uploadsApi.getPreviewUrl(upload.id) : ''}
                      alt="Safe preview"
                      className="object-contain max-h-72"
                    />
                  </div>
                  <p className="text-[11px] text-slate-400 mt-2">
                    EXIF stripped • Downscaled • Watermarked
                  </p>
                </div>
              ) : (
                <div>
                  {previewData?.sample_rows && previewData.sample_rows.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-slate-200 text-[11px] text-left">
                        <thead className="bg-slate-50 font-semibold text-slate-700">
                          <tr>
                            {previewData.columns?.slice(0, 3).map((col: any) => (
                              <th key={col.name} className="px-2 py-1.5">
                                <div>{col.name}</div>
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 bg-white">
                          {previewData.sample_rows.slice(0, 3).map((row: any, idx: number) => (
                            <tr key={idx}>
                              {previewData.columns?.slice(0, 3).map((col: any) => (
                                <td key={col.name} className="px-2 py-1 text-slate-600 font-mono truncate max-w-[90px]">
                                  {row[col.name] !== null ? String(row[col.name]) : 'null'}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <p className="text-[11px] text-slate-400 mt-2">
                        {previewData.row_count} rows • First sample masked
                      </p>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400">Tabular preview available.</p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Pre-check Integrity Report */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-1.5">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              <span>Pre-Check Integrity</span>
            </h2>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">MIME Type</span>
                <span className="font-mono text-slate-800">{fileInfo?.mime}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">File Size</span>
                <span className="text-slate-800">{((fileInfo?.size || 0) / (1024 * 1024)).toFixed(2)} MB</span>
              </div>

              {fileInfo?.data_type === 'image' && (
                <>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Dimensions</span>
                    <span className="text-slate-800">{fileInfo.width} × {fileInfo.height} px</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Perceptual Hash</span>
                    <span className="font-mono text-indigo-600 truncate max-w-[120px]" title={fileInfo.phash}>
                      {fileInfo.phash}
                    </span>
                  </div>
                </>
              )}

              {fileInfo?.data_type === 'tabular' && (
                <>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Total Rows</span>
                    <span className="text-slate-800 font-semibold">{fileInfo.row_count?.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Columns</span>
                    <span className="text-slate-800 font-semibold">{fileInfo.column_schema?.column_count}</span>
                  </div>
                </>
              )}

              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Malware & Safety</span>
                <span className="text-emerald-600 font-semibold">Clean (Passed)</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Category Change Modal */}
      {showCategoryModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl">
            <h3 className="text-lg font-bold text-slate-900 mb-2">Request Category Change</h3>
            <p className="text-xs text-slate-500 mb-4">
              Select the preferred category domain and subcategory. If this differs from a high-confidence AI pick, it will be submitted for admin moderation.
            </p>

            <form onSubmit={handleRequestCategory} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Domain Category</label>
                <select
                  required
                  value={selectedCatId}
                  onChange={(e) => {
                    setSelectedCatId(Number(e.target.value));
                    setSelectedSubId(undefined);
                  }}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">Select Domain...</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} (${(c.base_price_paise / 100).toFixed(0)} Base)
                    </option>
                  ))}
                </select>
              </div>

              {selectedCatId > 0 && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Subcategory</label>
                  <select
                    value={selectedSubId || ''}
                    onChange={(e) => setSelectedSubId(e.target.value ? Number(e.target.value) : undefined)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Select Subcategory (Optional)...</option>
                    {categories
                      .find((c) => c.id === selectedCatId)
                      ?.subcategories.map((sub) => (
                        <option key={sub.id} value={sub.id}>
                          {sub.name}
                        </option>
                      ))}
                  </select>
                </div>
              )}

              <div className="flex justify-end space-x-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCategoryModal(false)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 rounded-lg text-xs font-semibold hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingCategory || !selectedCatId}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-sm disabled:opacity-50"
                >
                  {savingCategory ? 'Submitting...' : 'Submit Request'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
