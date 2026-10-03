import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { earningsApi, payoutsApi, formatErrorMessage } from '../../api/client';
import { ContributorEarningsSummary, PayoutRequest } from '../../types';
import { 
  DollarSign, Clock, ArrowUpRight, ArrowDownLeft, ShieldCheck, 
  CheckCircle2, XCircle, AlertTriangle, Building, Send, Loader2, RefreshCw, Sparkles 
} from 'lucide-react';

export const ContributorEarningsPage: React.FC = () => {
  const [summary, setSummary] = useState<ContributorEarningsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [submittingPayout, setSubmittingPayout] = useState(false);
  const [payoutForm, setPayoutForm] = useState({
    amount: '',
    method: 'bank_transfer',
    accountNumber: '',
    ifsc: '',
    upiId: '',
  });
  const [formError, setFormError] = useState('');
  const [releasing, setReleasing] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const fetchEarnings = async () => {
    try {
      setLoading(true);
      const data = await earningsApi.getMyEarnings();
      setSummary(data);
    } catch (err: any) {
      setError('Failed to fetch contributor earnings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEarnings();
  }, []);

  const handleReleasePending = async () => {
    try {
      setReleasing(true);
      const res = await earningsApi.releasePending();
      setActionSuccess(res.detail || 'Pending funds released to available balance!');
      await fetchEarnings();
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      alert('Failed to release pending funds');
    } finally {
      setReleasing(false);
    }
  };

  const handlePayoutSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');

    const numAmount = parseFloat(payoutForm.amount);
    if (isNaN(numAmount) || numAmount < 10) {
      setFormError('Minimum payout amount is $10.00');
      return;
    }

    const amountPaise = Math.round(numAmount * 100);
    const availablePaise = summary?.wallet.available_balance_paise || 0;

    if (amountPaise > availablePaise) {
      setFormError(`Amount exceeds your available balance of $${(availablePaise / 100).toFixed(2)}`);
      return;
    }

    let destination = '';
    if (payoutForm.method === 'bank_transfer') {
      if (!payoutForm.accountNumber || !payoutForm.ifsc) {
        setFormError('Account number and IFSC/Routing code are required');
        return;
      }
      destination = `A/C: ${payoutForm.accountNumber} (IFSC: ${payoutForm.ifsc.toUpperCase()})`;
    } else {
      if (!payoutForm.upiId) {
        setFormError('UPI ID is required');
        return;
      }
      destination = `UPI: ${payoutForm.upiId}`;
    }

    try {
      setSubmittingPayout(true);
      await payoutsApi.requestPayout({
        amount_paise: amountPaise,
        method: payoutForm.method,
        destination,
      });
      setModalOpen(false);
      setPayoutForm({ amount: '', method: 'bank_transfer', accountNumber: '', ifsc: '', upiId: '' });
      setActionSuccess(`Payout request for $${numAmount.toFixed(2)} submitted successfully!`);
      await fetchEarnings();
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      setFormError(formatErrorMessage(err, 'Failed to submit payout request'));
    } finally {
      setSubmittingPayout(false);
    }
  };

  const handleSimulatePayoutAction = async (payoutId: number, action: 'complete' | 'reject') => {
    try {
      await payoutsApi.processPayout(payoutId, action);
      setActionSuccess(`Payout #${payoutId} marked as ${action === 'complete' ? 'COMPLETED' : 'REJECTED (Refunded)'}`);
      await fetchEarnings();
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      alert(formatErrorMessage(err, 'Failed to process payout'));
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 text-indigo-600 animate-spin mb-2" />
        <p className="text-slate-500 text-sm">Loading financial balances and ledger entries...</p>
      </div>
    );
  }

  const wallet = summary?.wallet;
  const availablePaise = wallet?.available_balance_paise || 0;
  const pendingPaise = wallet?.pending_balance_paise || 0;
  const lifetimeEarnings = summary?.lifetime_earnings_paise || 0;
  const lifetimeWithdrawn = summary?.lifetime_withdrawn_paise || 0;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
            <DollarSign className="h-7 w-7 text-emerald-600" />
            <span>Contributor Earnings & Payouts</span>
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Real-time double-entry ledger settlement (80% Contributor / 20% Marketplace split).
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {pendingPaise > 0 && (
            <button
              disabled={releasing}
              onClick={handleReleasePending}
              className="inline-flex items-center space-x-1.5 bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-300 font-medium text-xs px-3.5 py-2 rounded-xl transition-colors shadow-sm"
              title="Dispute window simulation in MVP"
            >
              {releasing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5 text-amber-600" />}
              <span>Simulate Release Pending Funds</span>
            </button>
          )}

          <button
            onClick={() => setModalOpen(true)}
            disabled={availablePaise < 1000}
            className="inline-flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-bold text-sm px-4 py-2 rounded-xl shadow-sm transition-colors"
          >
            <Send className="h-4 w-4" />
            <span>Request Payout</span>
          </button>
        </div>
      </div>

      {actionSuccess && (
        <div className="bg-emerald-50 text-emerald-800 p-4 rounded-xl text-sm font-medium border border-emerald-200 flex items-center space-x-2">
          <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-xl text-sm font-medium border border-red-200">
          {error}
        </div>
      )}

      {/* 4 Financial Balance Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Available for Payout */}
        <div className="bg-gradient-to-br from-emerald-600 to-teal-700 text-white p-6 rounded-2xl shadow-md space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-bold text-emerald-100 tracking-wider">Available to Withdraw</span>
            <CheckCircle2 className="h-5 w-5 text-emerald-200" />
          </div>
          <div className="text-3xl font-black font-mono">
            ${(availablePaise / 100).toFixed(2)}
          </div>
          <p className="text-xs text-emerald-100">Cleared funds ready for bank/UPI payout.</p>
        </div>

        {/* Pending Clearance */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-bold text-slate-500 tracking-wider">Pending Clearance</span>
            <Clock className="h-5 w-5 text-amber-500" />
          </div>
          <div className="text-3xl font-black text-slate-900 font-mono">
            ${(pendingPaise / 100).toFixed(2)}
          </div>
          <p className="text-xs text-slate-500">Subject to dispute window settlement.</p>
        </div>

        {/* Lifetime Earnings */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-bold text-slate-500 tracking-wider">Lifetime Net Earnings</span>
            <ArrowUpRight className="h-5 w-5 text-indigo-500" />
          </div>
          <div className="text-3xl font-black text-slate-900 font-mono">
            ${(lifetimeEarnings / 100).toFixed(2)}
          </div>
          <p className="text-xs text-slate-500">Total 80% revenue from {summary?.sales_count || 0} dataset sales.</p>
        </div>

        {/* Total Withdrawn */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-bold text-slate-500 tracking-wider">Total Withdrawn</span>
            <Building className="h-5 w-5 text-slate-400" />
          </div>
          <div className="text-3xl font-black text-slate-900 font-mono">
            ${(lifetimeWithdrawn / 100).toFixed(2)}
          </div>
          <p className="text-xs text-slate-500">Disbursed to your payout destinations.</p>
        </div>
      </div>

      {/* Main Content Grid: Recent Sales & Payout History */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Side: Sales Ledger */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <ArrowUpRight className="h-4 w-4 text-emerald-600" />
              <span>Dataset Sales & Revenue Ledger</span>
            </h2>
            <span className="text-xs font-semibold text-slate-400 font-mono">
              {summary?.recent_sales.length || 0} sales
            </span>
          </div>

          <div className="divide-y divide-slate-100">
            {summary?.recent_sales.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs">
                No dataset sales recorded yet. Once agencies license your published data, your 80% revenue share will appear here.
              </div>
            ) : (
              summary?.recent_sales.map((sale) => (
                <div key={sale.order_id} className="p-4 hover:bg-slate-50/50 flex items-center justify-between text-xs">
                  <div className="space-y-1">
                    <p className="font-bold text-slate-900">{sale.dataset_title}</p>
                    <div className="flex items-center space-x-2 text-slate-500">
                      <span>Order #{sale.order_id}</span>
                      <span>•</span>
                      <span>Buyer: {sale.buyer_email}</span>
                      <span>•</span>
                      <span>{new Date(sale.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>

                  <div className="text-right space-y-0.5">
                    <span className="font-bold text-emerald-600 font-mono text-sm block">
                      +${(sale.contributor_share_paise / 100).toFixed(2)}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      80% of ${(sale.total_amount_paise / 100).toFixed(2)}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Side: Payout Requests History */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <Building className="h-4 w-4 text-indigo-600" />
              <span>Payout Requests</span>
            </h2>
            <span className="text-xs font-semibold text-slate-400 font-mono">
              {summary?.payout_requests.length || 0} requests
            </span>
          </div>

          <div className="divide-y divide-slate-100">
            {summary?.payout_requests.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs">
                No payout requests made yet. When you have available balance, click "Request Payout" above.
              </div>
            ) : (
              summary?.payout_requests.map((payout) => (
                <div key={payout.id} className="p-4 hover:bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-slate-900">Payout #{payout.id}</span>
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          payout.status === 'completed'
                            ? 'bg-emerald-100 text-emerald-800'
                            : payout.status === 'rejected'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {payout.status.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-slate-600 text-[11px] font-mono">{payout.destination}</p>
                    <p className="text-slate-400 text-[10px]">{new Date(payout.created_at).toLocaleString()}</p>
                  </div>

                  <div className="flex items-center justify-between sm:justify-end space-x-3">
                    <span className="font-mono font-bold text-slate-900 text-sm">
                      ${(payout.amount_paise / 100).toFixed(2)}
                    </span>

                    {/* Simulation buttons in MVP */}
                    {payout.status === 'requested' && (
                      <div className="flex items-center space-x-1.5">
                        <button
                          onClick={() => handleSimulatePayoutAction(payout.id, 'complete')}
                          className="px-2 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-[10px] font-bold rounded border border-emerald-200 transition-colors"
                          title="Simulate bank disbursement"
                        >
                          Mark Paid
                        </button>
                        <button
                          onClick={() => handleSimulatePayoutAction(payout.id, 'reject')}
                          className="px-2 py-1 bg-red-50 hover:bg-red-100 text-red-700 text-[10px] font-bold rounded border border-red-200 transition-colors"
                          title="Simulate rejection & refund"
                        >
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* REQUEST PAYOUT MODAL */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-6">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-lg font-bold text-slate-900 flex items-center space-x-2">
                <Send className="h-5 w-5 text-emerald-600" />
                <span>Withdraw Available Earnings</span>
              </h3>
              <button
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="bg-red-50 text-red-700 p-3 rounded-xl text-xs font-medium border border-red-200">
                {formError}
              </div>
            )}

            <form onSubmit={handlePayoutSubmit} className="space-y-4 text-xs">
              {/* Amount input */}
              <div>
                <label className="font-bold text-slate-700 block mb-1">
                  Payout Amount (USD) <span className="text-slate-400 font-normal">(Max: ${(availablePaise / 100).toFixed(2)})</span>
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-2.5 text-slate-400 font-bold">$</span>
                  <input
                    type="number"
                    step="0.01"
                    min="10"
                    max={(availablePaise / 100).toString()}
                    value={payoutForm.amount}
                    onChange={(e) => setPayoutForm({ ...payoutForm, amount: e.target.value })}
                    placeholder="100.00"
                    required
                    className="w-full pl-8 pr-16 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => setPayoutForm({ ...payoutForm, amount: (availablePaise / 100).toFixed(2) })}
                    className="absolute right-2 top-1.5 px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-[10px] rounded-lg transition-colors"
                  >
                    MAX
                  </button>
                </div>
              </div>

              {/* Method choice */}
              <div>
                <label className="font-bold text-slate-700 block mb-1">Payout Channel</label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setPayoutForm({ ...payoutForm, method: 'bank_transfer' })}
                    className={`py-2 px-3 rounded-xl border font-bold text-center transition-colors ${
                      payoutForm.method === 'bank_transfer'
                        ? 'border-emerald-600 bg-emerald-50 text-emerald-800'
                        : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    Direct Bank Transfer
                  </button>
                  <button
                    type="button"
                    onClick={() => setPayoutForm({ ...payoutForm, method: 'upi' })}
                    className={`py-2 px-3 rounded-xl border font-bold text-center transition-colors ${
                      payoutForm.method === 'upi'
                        ? 'border-emerald-600 bg-emerald-50 text-emerald-800'
                        : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    Instant UPI
                  </button>
                </div>
              </div>

              {/* Destination inputs */}
              {payoutForm.method === 'bank_transfer' ? (
                <div className="space-y-3 pt-1">
                  <div>
                    <label className="font-bold text-slate-700 block mb-1">Bank Account Number</label>
                    <input
                      type="text"
                      value={payoutForm.accountNumber}
                      onChange={(e) => setPayoutForm({ ...payoutForm, accountNumber: e.target.value })}
                      placeholder="e.g. 501004829102"
                      required
                      className="w-full px-3 py-2 rounded-xl border border-slate-200 font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                  <div>
                    <label className="font-bold text-slate-700 block mb-1">IFSC / Routing Code</label>
                    <input
                      type="text"
                      value={payoutForm.ifsc}
                      onChange={(e) => setPayoutForm({ ...payoutForm, ifsc: e.target.value })}
                      placeholder="e.g. HDFC0001234"
                      required
                      className="w-full px-3 py-2 rounded-xl border border-slate-200 font-mono uppercase focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                </div>
              ) : (
                <div className="pt-1">
                  <label className="font-bold text-slate-700 block mb-1">VPA / UPI ID</label>
                  <input
                    type="text"
                    value={payoutForm.upiId}
                    onChange={(e) => setPayoutForm({ ...payoutForm, upiId: e.target.value })}
                    placeholder="e.g. yourname@okhdfcbank"
                    required
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              )}

              <div className="pt-4 flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 text-slate-600 font-bold hover:bg-slate-100 rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingPayout}
                  className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-bold rounded-xl shadow flex items-center space-x-2 transition-colors"
                >
                  {submittingPayout ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  <span>Confirm Payout</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
