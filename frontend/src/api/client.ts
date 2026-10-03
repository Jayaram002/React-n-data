import axios from 'axios';
import { TokenResponse, User, CategoryTree, Upload, ListingPagination, ListingDetail } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to attach Access Token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor to handle 401 & token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      
      if (refreshToken) {
        try {
          const res = await axios.post<TokenResponse>(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          
          localStorage.setItem('access_token', res.data.access_token);
          localStorage.setItem('refresh_token', res.data.refresh_token);
          
          originalRequest.headers.Authorization = `Bearer ${res.data.access_token}`;
          return apiClient(originalRequest);
        } catch (refreshErr) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
          return Promise.reject(refreshErr);
        }
      } else {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      }
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  register: async (payload: any) => {
    const res = await apiClient.post<User>('/auth/register', payload);
    return res.data;
  },
  login: async (payload: any) => {
    const res = await apiClient.post<TokenResponse>('/auth/login', payload);
    return res.data;
  },
  getMe: async () => {
    const res = await apiClient.get<User>('/auth/me');
    return res.data;
  },
};

export const categoriesApi = {
  getCategories: async () => {
    const res = await apiClient.get<CategoryTree[]>('/categories');
    return res.data;
  },
};

export const uploadsApi = {
  uploadDataset: async (formData: FormData, onProgress?: (percent: number) => void) => {
    const res = await apiClient.post<Upload>('/uploads', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    });
    return res.data;
  },
  getMyUploads: async () => {
    const res = await apiClient.get<Upload[]>('/uploads/mine');
    return res.data;
  },
  getUpload: async (id: number) => {
    const res = await apiClient.get<Upload>(`/uploads/${id}`);
    return res.data;
  },
  getPreviewUrl: (id: number) => {
    const token = localStorage.getItem('access_token');
    return `${API_BASE_URL}/uploads/${id}/preview?token=${token || ''}`;
  },
  getPreviewData: async (id: number) => {
    const res = await apiClient.get(`/uploads/${id}/preview`);
    return res.data;
  },
  getAnalysis: async (id: number) => {
    const res = await apiClient.get(`/uploads/${id}/analysis`);
    return res.data;
  },
  updatePrice: async (id: number, pricePaise: number) => {
    const res = await apiClient.patch<Upload>(`/uploads/${id}/price`, { price_paise: pricePaise });
    return res.data;
  },
  requestCategoryChange: async (id: number, categoryId: number, subcategoryId?: number) => {
    const res = await apiClient.patch<Upload>(`/uploads/${id}/category`, {
      category_id: categoryId,
      subcategory_id: subcategoryId,
    });
    return res.data;
  },
  publishUpload: async (id: number) => {
    const res = await apiClient.post<Upload>(`/uploads/${id}/publish`);
    return res.data;
  },
  unpublishUpload: async (id: number) => {
    const res = await apiClient.post<Upload>(`/uploads/${id}/unpublish`);
    return res.data;
  },
};

export const listingsApi = {
  browseListings: async (params?: any) => {
    const res = await apiClient.get<ListingPagination>('/listings/browse', { params });
    return res.data;
  },
  getCategoryListings: async (slug: string, params?: any) => {
    const res = await apiClient.get<ListingPagination>(`/categories/${slug}/listings`, { params });
    return res.data;
  },
  getListing: async (id: number) => {
    const res = await apiClient.get<ListingDetail>(`/listings/${id}`);
    return res.data;
  },
  getPreviewUrl: (listingId: number) => {
    return `${API_BASE_URL}/listings/${listingId}/preview`;
  },
  getPreviewData: async (listingId: number) => {
    const res = await apiClient.get(`/listings/${listingId}/preview`);
    return res.data;
  },
};

export const ordersApi = {
  createOrder: async (listingId: number) => {
    const res = await apiClient.post<any>('/orders', { listing_id: listingId });
    return res.data;
  },
  getMyOrders: async () => {
    const res = await apiClient.get<any[]>('/orders/mine');
    return res.data;
  },
  getOrder: async (id: number) => {
    const res = await apiClient.get<any>(`/orders/${id}`);
    return res.data;
  },
  getDownloadUrl: (orderId: number) => {
    return `${API_BASE_URL}/orders/${orderId}/download`;
  },
  downloadFile: async (orderId: number, filename?: string) => {
    const res = await apiClient.get(`/orders/${orderId}/download`, {
      responseType: 'blob',
    });
    const blob = new Blob([res.data]);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename || `dataset_order_${orderId}.bin`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
};

export const mockPaymentsApi = {
  getCheckoutDetails: async (orderId: number) => {
    const res = await apiClient.get<any>(`/mock/orders/${orderId}/checkout`);
    return res.data;
  },
  simulatePayment: async (orderId: number, result: 'paid' | 'failed' | 'cancelled') => {
    const res = await apiClient.post<any>(`/mock/orders/${orderId}/simulate`, { result });
    return res.data;
  },
};

export const earningsApi = {
  getMyEarnings: async () => {
    const res = await apiClient.get<any>('/earnings/me');
    return res.data;
  },
  getMyWallet: async () => {
    const res = await apiClient.get<any>('/earnings/wallet');
    return res.data;
  },
  releasePending: async () => {
    const res = await apiClient.post<any>('/earnings/release-pending');
    return res.data;
  },
};

export const payoutsApi = {
  requestPayout: async (payload: { amount_paise: number; method: string; destination: string }) => {
    const res = await apiClient.post<any>('/payouts/request', payload);
    return res.data;
  },
  getMyPayouts: async () => {
    const res = await apiClient.get<any[]>('/payouts/mine');
    return res.data;
  },
  processPayout: async (payoutId: number, action: 'complete' | 'reject', reason?: string) => {
    const res = await apiClient.post<any>(`/payouts/${payoutId}/process`, { action, reason });
    return res.data;
  },
};

export const adminApi = {
  getModerationQueue: async () => {
    const res = await apiClient.get<any[]>('/admin/moderation/queue');
    return res.data;
  },
  executeModerationAction: async (uploadId: number, payload: { action: string; category_id?: number; subcategory_id?: number; reason?: string }) => {
    const res = await apiClient.post<any>(`/admin/moderation/uploads/${uploadId}/action`, payload);
    return res.data;
  },
  resolveFlag: async (flagId: number, payload: { action: 'resolve' | 'dismiss'; notes?: string }) => {
    const res = await apiClient.post<any>(`/admin/flags/${flagId}/resolve`, payload);
    return res.data;
  },
  createCategory: async (payload: { name: string; slug: string; base_price_paise: number; active?: boolean }) => {
    const res = await apiClient.post<any>('/admin/taxonomy/categories', payload);
    return res.data;
  },
  updateCategory: async (id: number, payload: { name?: string; slug?: string; base_price_paise?: number; active?: boolean }) => {
    const res = await apiClient.patch<any>(`/admin/taxonomy/categories/${id}`, payload);
    return res.data;
  },
  createSubcategory: async (payload: { parent_id: number; name: string; slug: string; base_price_paise?: number; active?: boolean }) => {
    const res = await apiClient.post<any>('/admin/taxonomy/subcategories', payload);
    return res.data;
  },
  updateSubcategory: async (id: number, payload: { name?: string; slug?: string; base_price_paise?: number; active?: boolean }) => {
    const res = await apiClient.patch<any>(`/admin/taxonomy/subcategories/${id}`, payload);
    return res.data;
  },
  getAnalytics: async () => {
    const res = await apiClient.get<any>('/admin/analytics');
    return res.data;
  },
  getAuditLogs: async (params?: { page?: number; limit?: number; action?: string; entity?: string }) => {
    const res = await apiClient.get<any>('/admin/audit-logs', { params });
    return res.data;
  },
};



