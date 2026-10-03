import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ordersApi, formatErrorMessage } from '../../api/client';
import { Order } from '../../types';
import { 
  ShoppingBag, Download, ShieldCheck, CheckCircle2, Clock, 
  XCircle, ArrowRight, Loader2, Database, FileText, Image as ImageIcon, ExternalLink 
} from 'lucide-react';

export const PurchasesPage: React.FC = () => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [error, setError] = useState('');

  const fetchOrders = async () => {
    try {
      setLoading(true);
      const data = await ordersApi.getMyOrders();
      setOrders(data);
    } catch (err: any) {
      setError('Failed to fetch your purchases');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, []);

  const handleDownload = async (orderId: number, title?: string, dataType?: string) => {
    try {
      setDownloadingId(orderId);
      const ext = dataType === 'image' ? 'png' : 'csv';
      const cleanTitle = (title || 'dataset').toLowerCase().replace(/[^a-z0-9]/g, '_');
      const filename = `${cleanTitle}_order_${orderId}.${ext}`;
      await ordersApi.downloadFile(orderId, filename);
    } catch (err: any) {
      alert(formatErrorMessage(err, 'Download failed. Ensure your order is paid and authorized.'));
    } finally {
      setDownloadingId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'paid':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
            <CheckCircle2 className="h-3.5 w-3.5 mr-1" /> Licensed & Paid
          </span>
        );
      case 'awaiting_payment':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
            <Clock className="h-3.5 w-3.5 mr-1" /> Awaiting Payment
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800">
            <XCircle className="h-3.5 w-3.5 mr-1" /> Payment Failed
          </span>
        );
      case 'cancelled':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
            Cancelled
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 text-indigo-600 animate-spin mb-2" />
        <p className="text-slate-500 text-sm">Loading your licensed purchases & orders...</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
            <ShoppingBag className="h-6 w-6 text-indigo-600" />
            <span>My Licensed Datasets & Purchases</span>
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Access licensed raw datasets, commercial license grants, and verifiable audit records.
          </p>
        </div>
        <Link
          to="/marketplace"
          className="inline-flex items-center space-x-2 text-sm font-semibold text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 px-4 py-2 rounded-xl transition-colors self-start sm:self-auto"
        >
          <span>Browse Marketplace</span>
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-xl border border-red-200 text-sm">
          {error}
        </div>
      )}

      {orders.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-sm">
          <Database className="h-12 w-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-800">No purchases found</h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto mt-1 mb-6">
            You haven't purchased any dataset licenses yet. Explore our AI-curated domain marketplace to find high-trust data.
          </p>
          <Link
            to="/marketplace"
            className="inline-flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm px-5 py-2.5 rounded-xl shadow-sm transition-colors"
          >
            <span>Explore Marketplace</span>
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map((order) => {
            const listing = order.listing;
            return (
              <div
                key={order.id}
                className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
              >
                {/* Left side: dataset info */}
                <div className="space-y-2 flex-grow">
                  <div className="flex flex-wrap items-center gap-2">
                    {getStatusBadge(order.status)}
                    <span className="text-xs font-mono text-slate-400">Order #{order.id}</span>
                    <span className="text-xs text-slate-400">• {new Date(order.created_at).toLocaleDateString()}</span>
                  </div>

                  <div>
                    <h3 className="text-base font-bold text-slate-900 hover:text-indigo-600 transition-colors">
                      {listing ? (
                        <Link to={`/marketplace/${listing.id}`}>{listing.title}</Link>
                      ) : (
                        `Listing #${order.listing_id}`
                      )}
                    </h3>
                    <div className="flex items-center space-x-3 text-xs text-slate-500 mt-1">
                      {listing?.data_type === 'image' ? (
                        <span className="flex items-center text-indigo-600 font-medium">
                          <ImageIcon className="h-3.5 w-3.5 mr-1" /> Image
                        </span>
                      ) : (
                        <span className="flex items-center text-emerald-600 font-medium">
                          <FileText className="h-3.5 w-3.5 mr-1" /> Tabular
                        </span>
                      )}
                      {listing?.category && <span>Category: {listing.category.name}</span>}
                      {listing?.contributor && (
                        <span>Contributor: <strong>{listing.contributor.display_name}</strong></span>
                      )}
                    </div>
                  </div>

                  {/* License Info */}
                  {order.license && (
                    <div className="inline-flex items-center space-x-1.5 bg-indigo-50 text-indigo-800 px-2.5 py-1 rounded-lg text-xs font-medium border border-indigo-100">
                      <ShieldCheck className="h-3.5 w-3.5 text-indigo-600" />
                      <span>Commercial License #{order.license.id} (Terms v{order.license.terms_version})</span>
                    </div>
                  )}
                </div>

                {/* Right side: price and action buttons */}
                <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 self-stretch md:self-auto justify-between border-t md:border-t-0 pt-3 md:pt-0 border-slate-100">
                  <div className="text-left md:text-right pr-4">
                    <span className="text-xs text-slate-400 block">Amount Paid</span>
                    <span className="text-lg font-black text-slate-900 font-mono">
                      ${(order.amount_paise / 100).toFixed(2)}
                    </span>
                  </div>

                  {order.status === 'paid' && (
                    <button
                      disabled={downloadingId === order.id}
                      onClick={() => handleDownload(order.id, listing?.title, listing?.data_type)}
                      className="w-full sm:w-auto px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-sm flex items-center justify-center space-x-2 transition-colors"
                    >
                      {downloadingId === order.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Download className="h-4 w-4" />
                      )}
                      <span>Download Dataset</span>
                    </button>
                  )}

                  {order.status === 'awaiting_payment' && (
                    <Link
                      to={`/mock-checkout/${order.id}`}
                      className="w-full sm:w-auto px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-sm flex items-center justify-center space-x-1.5 transition-colors"
                    >
                      <span>Pay Now</span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  )}

                  {order.status === 'failed' && (
                    <Link
                      to={`/mock-checkout/${order.id}`}
                      className="w-full sm:w-auto px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-xl border border-slate-300 flex items-center justify-center space-x-1.5 transition-colors"
                    >
                      <span>Retry Checkout</span>
                    </Link>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
