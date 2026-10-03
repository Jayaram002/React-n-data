import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { CategoriesView } from './pages/CategoriesView';
import { ContributorDashboard } from './pages/contributor/Dashboard';
import { ContributorUpload } from './pages/contributor/Upload';
import { ContributorUploadDetail } from './pages/contributor/UploadDetail';
import { ContributorEarningsPage } from './pages/contributor/Earnings';
import { MarketplaceHome } from './pages/agency/MarketplaceHome';
import { CategoryBrowse } from './pages/agency/CategoryBrowse';
import { ListingDetailPage } from './pages/agency/ListingDetail';
import { MockCheckoutPage } from './pages/agency/MockCheckout';
import { PurchasesPage } from './pages/agency/Purchases';
import { AdminModerationPage } from './pages/admin/Moderation';
import { AdminTaxonomyPage } from './pages/admin/Taxonomy';
import { AdminAnalyticsPage } from './pages/admin/Analytics';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router>
          <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
            <Navbar />
            <main className="flex-grow">
              <Routes>
                {/* Public & Marketplace routes */}
                <Route path="/" element={<Dashboard />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/categories" element={<CategoriesView />} />
                <Route path="/marketplace" element={<MarketplaceHome />} />
                <Route path="/marketplace/category/:slug" element={<CategoryBrowse />} />
                <Route path="/marketplace/:listingId" element={<ListingDetailPage />} />

                {/* Contributor routes */}
                <Route element={<ProtectedRoute allowedRoles={['contributor', 'admin']} />}>
                  <Route path="/contributor/dashboard" element={<ContributorDashboard />} />
                  <Route path="/contributor/upload" element={<ContributorUpload />} />
                  <Route path="/contributor/uploads/:id" element={<ContributorUploadDetail />} />
                  <Route path="/contributor/earnings" element={<ContributorEarningsPage />} />
                </Route>

                {/* Authenticated Buyer / Agency / Contributor / Admin checkout & purchases */}
                <Route element={<ProtectedRoute allowedRoles={['agency', 'contributor', 'admin']} />}>
                  <Route path="/mock-checkout/:orderId" element={<MockCheckoutPage />} />
                  <Route path="/purchases" element={<PurchasesPage />} />
                </Route>

                {/* Admin routes */}
                <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
                  <Route path="/admin/moderation" element={<AdminModerationPage />} />
                  <Route path="/admin/taxonomy" element={<AdminTaxonomyPage />} />
                  <Route path="/admin/analytics" element={<AdminAnalyticsPage />} />
                </Route>
              </Routes>
            </main>
          </div>
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;

