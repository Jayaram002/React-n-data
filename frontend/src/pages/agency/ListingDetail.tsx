import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { listingsApi, ordersApi, formatErrorMessage } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { ListingDetail } from '../../types';
import { 
  ArrowLeft, Sparkles, ShieldCheck, FileText, Image as ImageIcon, 
  Database, Tag, DollarSign, CheckCircle2, Lock, Cpu, ShoppingBag, Loader2 
} from 'lucide-react';

export const ListingDetailPage: React.FC = () => {
  const { listingId } = useParams<{ listingId: string }>();
  const [listing, setListing] = useState<ListingDetail | null>(null);
  const [previewData, setPreviewData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(false);
  const [error, setError] = useState('');
  const [purchaseError, setPurchaseError] = useState('');

  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!listingId) return;
    const fetchDetail = async () => {
      try {
        const data = await listingsApi.getListing(Number(listingId));
        setListing(data);
        if (data.data_type === 'tabular') {
          try {
            const preview = await listingsApi.getPreviewData(data.id);
            setPreviewData(preview);
          } catch (prevErr) {
            console.warn('Tabular preview unavailable for listing:', prevErr);
          }
        }
      } catch (err) {
        setError('Failed to load listing detail');
      } finally {
        setLoading(false);
      }
    };
    fetchDetail();
  }, [listingId]);

  const handlePurchase = async () => {
    if (!user) {
      navigate('/login');
      return;
    }
    if (!listing) return;
    setPurchasing(true);
    setPurchaseError('');
    try {
      const order = await ordersApi.createOrder(listing.id);
      navigate(`/mock-checkout/${order.id}`);
    } catch (err: any) {
      setPurchaseError(formatErrorMessage(err, 'Failed to initialize order checkout'));
    } finally {
      setPurchasing(false);
    }
  };


  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 text-indigo-600 animate-spin mb-2" />
        <p className="text-slate-500 text-sm">Loading dataset specifications & trust score...</p>
      </div>
    );
  }

  if (error || !listing) {
    return (
      <div className="max-w-4xl mx-auto p-8 text-center">
        <div className="bg-red-50 text-red-700 p-4 rounded-xl border border-red-200">
          {error || 'Listing not found'}
        </div>
        <Link to="/marketplace" className="mt-4 inline-block text-sm text-indigo-600 font-semibold">
          Return to Marketplace
        </Link>
      </div>
    );
  }

  const analysis = listing.ai_analysis;

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      {/* Breadcrumb Navigation */}
      <div className="flex items-center space-x-2 text-xs text-slate-500">
        <Link to="/marketplace" className="hover:text-indigo-600 font-medium">Marketplace</Link>
        <span>/</span>
        {listing.category && (
          <>
            <Link to={`/marketplace/category/${listing.category.slug}`} className="hover:text-indigo-600 font-medium">
              {listing.category.name}
            </Link>
            <span>/</span>
          </>
        )}
        {listing.subcategory && (
          <>
            <Link to={`/marketplace/category/${listing.category?.slug}?sub=${listing.subcategory.slug}`} className="hover:text-indigo-600 font-medium">
              {listing.subcategory.name}
            </Link>
            <span>/</span>
          </>
        )}
        <span className="text-slate-800 font-semibold truncate max-w-xs">{listing.title}</span>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Columns: Listing Details, Trust Score Breakdown, Safe Preview */}
        <div className="lg:col-span-2 space-y-6">
          {/* Header */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center space-x-2 mb-2">
              {listing.data_type === 'image' ? (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100">
                  <ImageIcon className="h-3.5 w-3.5 mr-1" /> Image Dataset
                </span>
              ) : (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100">
                  <FileText className="h-3.5 w-3.5 mr-1" /> Tabular Dataset
                </span>
              )}
              {listing.category && (
                <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-2.5 py-0.5 rounded">
                  {listing.category.name}
                </span>
              )}
            </div>

            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900">{listing.title}</h1>
            <p className="text-slate-600 text-sm mt-2 leading-relaxed">{listing.description}</p>

            {/* Keyword Tags */}
            <div className="flex flex-wrap gap-1.5 mt-4 pt-4 border-t border-slate-100">
              {listing.tags.map((tag, idx) => (
                <span key={idx} className="text-xs font-medium bg-slate-100 text-slate-700 px-2.5 py-1 rounded-md">
                  #{tag}
                </span>
              ))}
            </div>
          </div>

          {/* AI Trust Score Breakdown Banner */}
          {analysis && (
            <div className="bg-gradient-to-br from-indigo-950 via-slate-900 to-indigo-900 text-white rounded-2xl p-6 shadow-md">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center space-x-2 text-amber-300 text-xs font-semibold uppercase tracking-wider mb-1">
                    <Sparkles className="h-4 w-4" />
                    <span>AI-Verified Trust Score</span>
                  </div>
                  <h2 className="text-xl font-bold">Independent Dataset Trust Rating</h2>
                  <p className="text-xs text-indigo-200 mt-1 max-w-md">
                    {analysis.explanation}
                  </p>
                </div>

                <div className="h-20 w-20 rounded-full border-4 border-amber-400 flex flex-col items-center justify-center bg-indigo-950/80 shadow-inner flex-shrink-0">
                  <span className="text-2xl font-black text-white">{analysis.total_score}</span>
                  <span className="text-[10px] text-amber-300 font-bold uppercase">/ 100</span>
                </div>
              </div>

              {/* 5 Component Bars */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-6 pt-5 border-t border-indigo-800/60">
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

          {/* Safe Preview Section */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center">
              <h2 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                <Database className="h-4 w-4 text-indigo-600" />
                <span>Safe Pre-purchase Data Preview</span>
              </h2>
              <span className="text-xs text-slate-400 font-mono">Originals are private</span>
            </div>

            <div className="p-6">
              {listing.data_type === 'image' ? (
                <div className="flex flex-col items-center">
                  <div className="border border-slate-200 rounded-lg overflow-hidden max-h-96 bg-slate-100">
                    <img
                      src={listingsApi.getPreviewUrl(listing.id)}
                      alt="Watermarked safe preview"
                      className="object-contain max-h-96"
                    />
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    EXIF metadata stripped • Downscaled • Watermarked
                  </p>
                </div>
              ) : (
                <div>
                  {previewData?.sample_rows && previewData.sample_rows.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-slate-200 text-xs text-left">
                        <thead className="bg-slate-50 font-semibold text-slate-700">
                          <tr>
                            {previewData.columns?.map((col: any) => (
                              <th key={col.name} className="px-3 py-2">
                                <div>{col.name}</div>
                                <div className="text-[10px] text-indigo-600 font-mono font-normal">
                                  {col.type}
                                </div>
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 bg-white">
                          {previewData.sample_rows.map((row: any, idx: number) => (
                            <tr key={idx} className="hover:bg-slate-50/50">
                              {previewData.columns?.map((col: any) => (
                                <td key={col.name} className="px-3 py-2 text-slate-600 font-mono">
                                  {row[col.name] !== null ? String(row[col.name]) : <span className="text-slate-300">null</span>}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <p className="text-xs text-slate-400 mt-3">
                        Showing first 5 sample rows with PII values masked. Full licensed download contains {previewData.row_count} rows.
                      </p>
                    </div>
                  ) : (
                    <p className="text-sm text-slate-500">Preview loading or unavailable.</p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right 1 Column: Purchase Box & Specifications */}
        <div className="space-y-6">
          {/* Purchase Box */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
            <div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Commercial License Price</span>
              <div className="text-3xl font-black text-slate-900 mt-1 font-mono">
                ${(listing.price_paise / 100).toFixed(2)}
              </div>
              <p className="text-xs text-emerald-600 font-medium mt-1 flex items-center">
                <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                <span>One-time fee • Instant secure download</span>
              </p>
            </div>

            {purchaseError && (
              <div className="bg-red-50 text-red-700 p-3 rounded-xl text-xs font-medium border border-red-200">
                {purchaseError}
              </div>
            )}

            <button
              disabled={purchasing}
              onClick={handlePurchase}
              className="w-full py-3.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold rounded-xl shadow-md flex items-center justify-center space-x-2 transition-colors"
            >
              {purchasing ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <>
                  <ShoppingBag className="h-5 w-5" />
                  <span>Purchase License (${(listing.price_paise / 100).toFixed(2)})</span>
                </>
              )}
            </button>


            {/* License Terms Summary */}
            <div className="pt-4 border-t border-slate-100 space-y-2.5 text-xs text-slate-600">
              <div className="flex items-start space-x-2">
                <ShieldCheck className="h-4 w-4 text-indigo-600 mt-0.5 flex-shrink-0" />
                <span>Commercial use allowed for analytics, modeling & production.</span>
              </div>
              <div className="flex items-start space-x-2">
                <CheckCircle2 className="h-4 w-4 text-indigo-600 mt-0.5 flex-shrink-0" />
                <span>
                  AI/ML Model Training: <strong>{listing.ai_training_allowed ? 'Allowed' : 'Prohibited'}</strong>
                </span>
              </div>
              <div className="flex items-start space-x-2">
                <Lock className="h-4 w-4 text-slate-400 mt-0.5 flex-shrink-0" />
                <span>No resale or redistribution of raw underlying data.</span>
              </div>
            </div>
          </div>

          {/* Contributor Profile Card */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-3">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Contributor Profile</h3>
            <div className="flex items-center space-x-3">
              <div className="h-10 w-10 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold">
                {(listing.contributor?.display_name || 'V')[0]}
              </div>
              <div>
                <p className="text-sm font-bold text-slate-900">{listing.contributor?.display_name || 'Verified Contributor'}</p>
                <p className="text-xs text-slate-500">Reputation Score: {listing.contributor?.reputation_score || 80.0}/100</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
