import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { categoriesApi, listingsApi } from '../../api/client';
import { CategoryTree, ListingItem } from '../../types';
import { 
  Store, Search, Layers, Sparkles, ArrowRight, 
  FileText, Image as ImageIcon, ShieldCheck, Tag, Loader2 
} from 'lucide-react';

export const MarketplaceHome: React.FC = () => {
  const [categories, setCategories] = useState<CategoryTree[]>([]);
  const [recentListings, setRecentListings] = useState<ListingItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([
      categoriesApi.getCategories(),
      listingsApi.browseListings({ limit: 6, sort: 'score_desc' })
    ])
      .then(([catData, listingData]) => {
        setCategories(catData);
        setRecentListings(listingData.items);
      })
      .catch((err) => setError('Failed to load marketplace data'))
      .finally(() => setLoading(false));
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/marketplace/category/all?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 text-indigo-600 animate-spin mb-2" />
        <p className="text-slate-500 text-sm">Loading agency data marketplace...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12">
      {/* Hero Search Section */}
      <div className="bg-gradient-to-br from-indigo-900 via-slate-900 to-indigo-950 text-white rounded-3xl p-8 sm:p-12 shadow-xl relative overflow-hidden">
        <div className="max-w-2xl relative z-10">
          <div className="inline-flex items-center space-x-2 bg-indigo-500/20 text-indigo-300 px-3 py-1 rounded-full text-xs font-semibold mb-4 border border-indigo-400/30">
            <Sparkles className="h-3.5 w-3.5 text-amber-400" />
            <span>AI-Scored & Verified Marketplace</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight leading-tight">
            Commercial Datasets with Transparent AI Trust Scoring
          </h1>
          <p className="text-indigo-200 text-sm sm:text-base mt-3 leading-relaxed">
            Browse verified datasets grouped by domain. Inspect safe previews, quality breakdowns, and license high-integrity data from top contributors.
          </p>

          {/* Search Form */}
          <form onSubmit={handleSearchSubmit} className="mt-6 flex items-center bg-white rounded-xl p-1.5 shadow-lg max-w-lg">
            <div className="pl-3 text-slate-400">
              <Search className="h-5 w-5" />
            </div>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by keywords (e.g. quantum mechanics, solar, sales)..."
              className="w-full px-3 py-2 text-slate-900 text-sm focus:outline-none placeholder-slate-400"
            />
            <button
              type="submit"
              className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-lg text-xs font-semibold transition-colors flex-shrink-0"
            >
              Search
            </button>
          </form>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-xl text-sm border border-red-200">
          {error}
        </div>
      )}

      {/* Domain Category Tiles */}
      <div>
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Explore by Category Domain</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Datasets from all contributors are unified under domain taxonomies.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {categories.map((cat) => (
            <Link
              key={cat.id}
              to={`/marketplace/category/${cat.slug}`}
              className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm hover:border-indigo-400 hover:shadow-md transition-all group flex flex-col justify-between"
            >
              <div>
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100">
                    Domain
                  </span>
                  <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full">
                    {cat.published_count} {cat.published_count === 1 ? 'dataset' : 'datasets'}
                  </span>
                </div>
                <h3 className="text-base font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
                  {cat.name} Datasets
                </h3>
                <p className="text-xs text-slate-400 mt-1 line-clamp-1">
                  {cat.subcategories.map((s) => s.name).join(', ')}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-slate-500 group-hover:text-indigo-600">
                <span>Browse {cat.name}</span>
                <ArrowRight className="h-3.5 w-3.5 group-hover:translate-x-1 transition-transform" />
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Top AI-Scored Datasets */}
      <div>
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-xl font-bold text-slate-900 flex items-center space-x-2">
              <Sparkles className="h-5 w-5 text-amber-500" />
              <span>Highest AI Trust Scored Datasets</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Top-rated datasets validated across Quality, Authenticity, and Uniqueness.
            </p>
          </div>
        </div>

        {recentListings.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center">
            <Store className="h-10 w-10 text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-600">No active listings published yet.</p>
            <p className="text-xs text-slate-400 mt-1">Contributors can publish analyzed datasets from their dashboard.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {recentListings.map((listing) => (
              <Link
                key={listing.id}
                to={`/marketplace/${listing.id}`}
                className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-md hover:border-indigo-300 transition-all flex flex-col justify-between"
              >
                <div className="p-6">
                  {/* Top Bar */}
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center space-x-1.5">
                      {listing.data_type === 'image' ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-indigo-50 text-indigo-700">
                          <ImageIcon className="h-3 w-3 mr-1" /> Image
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700">
                          <FileText className="h-3 w-3 mr-1" /> Tabular
                        </span>
                      )}
                      {listing.category && (
                        <span className="text-xs font-medium text-slate-500">
                          {listing.category.name}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center space-x-1 bg-amber-50 text-amber-800 px-2.5 py-1 rounded-full text-xs font-bold border border-amber-200">
                      <Sparkles className="h-3 w-3 text-amber-500" />
                      <span>{listing.trust_score}</span>
                    </div>
                  </div>

                  <h3 className="text-base font-bold text-slate-900 line-clamp-1 mb-1.5">
                    {listing.title}
                  </h3>
                  <p className="text-xs text-slate-500 line-clamp-2 mb-4 leading-relaxed">
                    {listing.description}
                  </p>

                  {/* Tags */}
                  <div className="flex flex-wrap gap-1 mb-2">
                    {listing.tags.slice(0, 3).map((tag, idx) => (
                      <span key={idx} className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                        #{tag}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Card Footer */}
                <div className="px-6 py-3.5 bg-slate-50 border-t border-slate-100 flex justify-between items-center">
                  <div className="text-xs">
                    <span className="text-slate-400">By </span>
                    <span className="font-semibold text-slate-700">{listing.contributor?.display_name || 'Verified Creator'}</span>
                  </div>

                  <div className="text-sm font-bold text-slate-900 font-mono">
                    ${(listing.price_paise / 100).toFixed(2)}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
