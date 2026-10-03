import React, { useEffect, useState } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import { categoriesApi, listingsApi } from '../../api/client';
import { CategoryTree, ListingPagination, ListingItem } from '../../types';
import { 
  Layers, Search, Filter, Sparkles, FileText, 
  Image as ImageIcon, ArrowLeft, ArrowUpDown, Tag, DollarSign, Loader2 
} from 'lucide-react';

export const CategoryBrowse: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const [searchParams, setSearchParams] = useSearchParams();

  const [categories, setCategories] = useState<CategoryTree[]>([]);
  const [pagination, setPagination] = useState<ListingPagination | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filter States
  const [selectedSubcategory, setSelectedSubcategory] = useState<string>(searchParams.get('sub') || '');
  const [selectedDataType, setSelectedDataType] = useState<string>(searchParams.get('type') || '');
  const [searchQuery, setSearchQuery] = useState<string>(searchParams.get('q') || '');
  const [minScore, setMinScore] = useState<number>(Number(searchParams.get('minScore')) || 0);
  const [sortOption, setSortOption] = useState<string>(searchParams.get('sort') || 'score_desc');
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Current domain category object
  const currentCategory = categories.find((c) => c.slug === slug);

  const fetchListings = async () => {
    setLoading(true);
    setError('');
    try {
      const params: any = {
        page: currentPage,
        limit: 12,
        sort: sortOption,
      };
      if (selectedSubcategory) params.subcategory = selectedSubcategory;
      if (selectedDataType) params.data_type = selectedDataType;
      if (searchQuery.trim()) params.q = searchQuery.trim();
      if (minScore > 0) params.min_score = minScore;

      let res: ListingPagination;
      if (slug && slug !== 'all') {
        res = await listingsApi.getCategoryListings(slug, params);
      } else {
        res = await listingsApi.browseListings(params);
      }
      setPagination(res);
    } catch (err) {
      setError('Failed to load datasets for this category');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    categoriesApi.getCategories().then((data) => setCategories(data)).catch(() => {});
  }, []);

  useEffect(() => {
    fetchListings();
  }, [slug, selectedSubcategory, selectedDataType, sortOption, minScore, currentPage]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    fetchListings();
  };

  const domainName = currentCategory ? currentCategory.name : (slug === 'all' ? 'All Datasets' : slug);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Back Link & Category Header */}
      <div>
        <Link
          to="/marketplace"
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-500 hover:text-indigo-600 mb-3"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Marketplace Home</span>
        </Link>

        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2.5 py-0.5 rounded border border-indigo-100">
                Category Domain
              </span>
              {currentCategory && (
                <span className="text-xs text-slate-400 font-mono">
                  Base: ${(currentCategory.base_price_paise / 100).toFixed(2)}
                </span>
              )}
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mt-1">{domainName} Datasets</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Verified image and tabular datasets classified into {domainName} by Gemma AI.
            </p>
          </div>

          <div className="text-right">
            <span className="text-2xl font-bold text-slate-900">{pagination?.total || 0}</span>
            <p className="text-xs text-slate-500">Available Datasets</p>
          </div>
        </div>
      </div>

      {/* Subcategory Pills */}
      {currentCategory && currentCategory.subcategories.length > 0 && (
        <div className="flex items-center space-x-2 overflow-x-auto pb-2">
          <button
            onClick={() => {
              setSelectedSubcategory('');
              setCurrentPage(1);
            }}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-colors ${
              selectedSubcategory === ''
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
            }`}
          >
            All {domainName}
          </button>

          {currentCategory.subcategories.map((sub) => (
            <button
              key={sub.id}
              onClick={() => {
                setSelectedSubcategory(sub.slug);
                setCurrentPage(1);
              }}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-colors flex items-center space-x-1.5 ${
                selectedSubcategory === sub.slug
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
              }`}
            >
              <span>{sub.name}</span>
              <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                selectedSubcategory === sub.slug ? 'bg-indigo-500 text-white' : 'bg-slate-100 text-slate-500'
              }`}>
                {sub.published_count}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="relative flex-grow max-w-md">
          <Search className="h-4 w-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search within this domain..."
            className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 text-slate-800"
          />
        </form>

        <div className="flex flex-wrap items-center gap-3">
          {/* Data Type Filter */}
          <div className="flex rounded-lg border border-slate-200 p-0.5 bg-slate-50 text-xs">
            <button
              type="button"
              onClick={() => { setSelectedDataType(''); setCurrentPage(1); }}
              className={`px-3 py-1.5 rounded-md font-medium ${
                selectedDataType === '' ? 'bg-white text-indigo-600 shadow-sm font-semibold' : 'text-slate-600'
              }`}
            >
              All Types
            </button>
            <button
              type="button"
              onClick={() => { setSelectedDataType('tabular'); setCurrentPage(1); }}
              className={`px-3 py-1.5 rounded-md font-medium flex items-center space-x-1 ${
                selectedDataType === 'tabular' ? 'bg-white text-emerald-600 shadow-sm font-semibold' : 'text-slate-600'
              }`}
            >
              <FileText className="h-3.5 w-3.5" />
              <span>Tabular</span>
            </button>
            <button
              type="button"
              onClick={() => { setSelectedDataType('image'); setCurrentPage(1); }}
              className={`px-3 py-1.5 rounded-md font-medium flex items-center space-x-1 ${
                selectedDataType === 'image' ? 'bg-white text-indigo-600 shadow-sm font-semibold' : 'text-slate-600'
              }`}
            >
              <ImageIcon className="h-3.5 w-3.5" />
              <span>Images</span>
            </button>
          </div>

          {/* Min Score Filter */}
          <div className="flex items-center space-x-2 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 text-xs">
            <Sparkles className="h-3.5 w-3.5 text-amber-500" />
            <span className="text-slate-600 font-medium">Min Score:</span>
            <input
              type="range"
              min="0"
              max="95"
              step="5"
              value={minScore}
              onChange={(e) => { setMinScore(Number(e.target.value)); setCurrentPage(1); }}
              className="w-16 accent-indigo-600 cursor-pointer"
            />
            <span className="font-bold text-slate-800">{minScore}</span>
          </div>

          {/* Sort Selector */}
          <div className="flex items-center space-x-1.5 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 text-xs">
            <ArrowUpDown className="h-3.5 w-3.5 text-slate-500" />
            <select
              value={sortOption}
              onChange={(e) => { setSortOption(e.target.value); setCurrentPage(1); }}
              className="bg-transparent text-slate-700 font-semibold focus:outline-none cursor-pointer"
            >
              <option value="score_desc">Highest AI Score</option>
              <option value="newest">Newest First</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-xl text-sm border border-red-200">
          {error}
        </div>
      )}

      {/* Listings Grid */}
      {loading ? (
        <div className="flex flex-col items-center justify-center min-h-[40vh]">
          <Loader2 className="h-8 w-8 text-indigo-600 animate-spin mb-2" />
          <p className="text-slate-500 text-sm">Loading dataset listings...</p>
        </div>
      ) : pagination?.items.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center">
          <Layers className="h-10 w-10 text-slate-300 mx-auto mb-2" />
          <h3 className="text-base font-bold text-slate-800">No datasets found matching your filters</h3>
          <p className="text-xs text-slate-500 mt-1">Try resetting the subcategory, data type, or score filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {pagination?.items.map((listing) => (
            <Link
              key={listing.id}
              to={`/marketplace/${listing.id}`}
              className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-md hover:border-indigo-300 transition-all flex flex-col justify-between"
            >
              <div className="p-6">
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
                    {listing.subcategory && (
                      <span className="text-xs font-medium text-slate-500 truncate max-w-[120px]">
                        {listing.subcategory.name}
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

                <div className="flex flex-wrap gap-1 mb-2">
                  {listing.tags.slice(0, 3).map((tag, idx) => (
                    <span key={idx} className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>

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
  );
};
