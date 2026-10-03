import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { mockPaymentsApi } from '../../api/client';
import { MockCheckoutInfo } from '../../types';
import { 
  CreditCard, ShieldCheck, AlertTriangle, CheckCircle2, 
  XCircle, ArrowLeft, Loader2, Lock, DollarSign, Sparkles 
} from 'lucide-react';

export const MockCheckoutPage: React.FC = () => {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();

  const [checkoutInfo, setCheckoutInfo] = useState<MockCheckoutInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState('');
  const [actionStatus, setActionStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!orderId) return;
    const fetchCheckout = async () => {
      try {
        const data = await mockPaymentsApi.getCheckoutDetails(Number(orderId));
        setCheckoutInfo(data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load checkout details');
      } finally {
        setLoading(false);
      }
    };
    fetchCheckout();
  }, [orderId]);

  const handleSimulate = async (result: 'paid' | 'failed' | 'cancelled') => {
    if (!orderId) return;
    setProcessing(true);
    setError('');
    setActionStatus(null);

    try {
      const order = await mockPaymentsApi.simulatePayment(Number(orderId), result);
      if (result === 'paid') {
        setActionStatus('Payment successful! Redirecting to your licensed purchases...');
        setTimeout(() => {
          navigate('/purchases');
        }, 1200);
      } else if (result === 'failed') {
        setError('Simulation: Payment was declined or card processing failed.');
        setCheckoutInfo((prev) => prev ? { ...prev, status: 'failed' } : null);
      } else if (result === 'cancelled') {
        setActionStatus('Checkout cancelled.');
        setTimeout(() => {
          navigate(`/marketplace/${checkoutInfo?.listing_id || ''}`);
        }, 1000);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Simulation request failed');
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 text-indigo-600 animate-spin mb-2" />
        <p className="text-slate-500 text-sm">Initializing secure mock checkout session...</p>
      </div>
    );
  }

  if (error && !checkoutInfo) {
    return (
      <div className="max-w-md mx-auto my-12 p-6 bg-white rounded-2xl border border-red-200 shadow-sm text-center">
        <AlertTriangle className="h-10 w-10 text-red-500 mx-auto mb-3" />
        <h2 className="text-lg font-bold text-slate-900">Checkout Error</h2>
        <p className="text-sm text-slate-600 mt-1">{error}</p>
        <Link to="/marketplace" className="mt-4 inline-block text-sm text-indigo-600 font-semibold">
          Return to Marketplace
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-10 sm:px-6">
      {/* TEST MODE BANNER */}
      <div className="bg-amber-500 text-slate-950 p-4 rounded-2xl shadow-sm mb-6 flex items-start space-x-3 border border-amber-600">
        <Sparkles className="h-6 w-6 mt-0.5 flex-shrink-0 text-slate-950" />
        <div>
          <div className="font-black text-sm uppercase tracking-wider">
            TEST MODE — Simulated Payment Gateway
          </div>
          <p className="text-xs text-amber-950 font-medium mt-0.5">
            No real credit cards or bank transfers are charged. This sandbox simulates the 80/20 revenue split, double-entry ledger settlement, and instant automated licensing for the marketplace MVP.
          </p>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CreditCard className="h-5 w-5 text-indigo-600" />
            <h1 className="text-lg font-bold text-slate-900">Complete Purchase</h1>
          </div>
          <span className="text-xs font-mono font-semibold text-slate-400">
            Order #{orderId}
          </span>
        </div>

        {/* Order Details Body */}
        <div className="p-6 space-y-6">
          {error && (
            <div className="bg-red-50 text-red-700 p-3.5 rounded-xl text-xs font-medium border border-red-200 flex items-center space-x-2">
              <XCircle className="h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {actionStatus && (
            <div className="bg-emerald-50 text-emerald-800 p-3.5 rounded-xl text-xs font-medium border border-emerald-200 flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
              <span>{actionStatus}</span>
            </div>
          )}

          {/* Dataset item summary */}
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200/80 flex items-center justify-between">
            <div className="space-y-1">
              <h2 className="text-sm font-bold text-slate-900">{checkoutInfo?.listing_title}</h2>
              <p className="text-xs text-slate-500">
                Contributor: <span className="font-medium text-slate-700">{checkoutInfo?.contributor_name}</span>
              </p>
              <div className="flex items-center space-x-2 text-[11px] text-slate-500">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                <span>Non-exclusive Commercial License (v1.0)</span>
              </div>
            </div>

            <div className="text-right">
              <span className="text-xs text-slate-400 block">Total Due</span>
              <span className="text-2xl font-black text-slate-900 font-mono">
                ${((checkoutInfo?.amount_paise || 0) / 100).toFixed(2)}
              </span>
            </div>
          </div>

          {/* 80/20 Transparent Settlement Breakdown */}
          <div className="bg-indigo-50/50 p-4 rounded-xl border border-indigo-100 text-xs space-y-2">
            <h3 className="font-bold text-indigo-950 flex items-center space-x-1.5">
              <Lock className="h-3.5 w-3.5 text-indigo-600" />
              <span>Automated Double-Entry Settlement Split</span>
            </h3>
            <div className="flex justify-between text-slate-600">
              <span>Contributor Share (80%):</span>
              <span className="font-mono font-semibold text-slate-800">
                ${(((checkoutInfo?.amount_paise || 0) * 0.80) / 100).toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Marketplace Platform Fee (20%):</span>
              <span className="font-mono font-semibold text-slate-800">
                ${(((checkoutInfo?.amount_paise || 0) * 0.20) / 100).toFixed(2)}
              </span>
            </div>
          </div>

          {/* Simulation Controls */}
          <div className="space-y-3 pt-2">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
              Simulate Payment Action
            </label>

            <button
              disabled={processing}
              onClick={() => handleSimulate('paid')}
              className="w-full py-3.5 px-4 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-bold rounded-xl shadow flex items-center justify-center space-x-2 transition-colors"
            >
              {processing ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <>
                  <CheckCircle2 className="h-5 w-5" />
                  <span>Simulate Successful Payment (${((checkoutInfo?.amount_paise || 0) / 100).toFixed(2)})</span>
                </>
              )}
            </button>

            <div className="grid grid-cols-2 gap-3">
              <button
                disabled={processing}
                onClick={() => handleSimulate('failed')}
                className="py-2.5 px-3 bg-red-50 hover:bg-red-100 disabled:opacity-50 text-red-700 font-semibold rounded-xl border border-red-200 text-xs flex items-center justify-center space-x-1.5 transition-colors"
              >
                <XCircle className="h-4 w-4" />
                <span>Simulate Decline / Fail</span>
              </button>

              <button
                disabled={processing}
                onClick={() => handleSimulate('cancelled')}
                className="py-2.5 px-3 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-700 font-semibold rounded-xl border border-slate-200 text-xs flex items-center justify-center space-x-1.5 transition-colors"
              >
                <ArrowLeft className="h-4 w-4" />
                <span>Cancel Order</span>
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 text-center">
          <p className="text-[11px] text-slate-400">
            Encrypted sandbox session • Provider ref: <span className="font-mono text-slate-600">{checkoutInfo?.provider_ref}</span>
          </p>
        </div>
      </div>
    </div>
  );
};
