import { apiClient } from '../../api/client';
import {
  ConsentDocument,
  ConsentRecord,
  TakedownRequest,
  DeletionRequest,
  DataExport,
  ConsentReport
} from './types';

export const consentApi = {
  // Documents
  getActiveDocuments: async (): Promise<ConsentDocument[]> => {
    const res = await apiClient.get<ConsentDocument[]>('/consent/documents/active');
    return res.data;
  },

  getDocumentByPurpose: async (purposeCode: string): Promise<ConsentDocument> => {
    const res = await apiClient.get<ConsentDocument>(`/consent/documents/${purposeCode}`);
    return res.data;
  },

  createDocumentVersion: async (payload: {
    purpose_code: string;
    version: string;
    title: string;
    body_markdown: string;
  }): Promise<ConsentDocument> => {
    const res = await apiClient.post<ConsentDocument>('/consent/documents', payload);
    return res.data;
  },

  // Records
  getUploadConsentRecords: async (uploadId: number): Promise<ConsentRecord[]> => {
    const res = await apiClient.get<ConsentRecord[]>(`/consent/uploads/${uploadId}/records`);
    return res.data;
  },

  // Withdrawal
  withdrawUploadConsent: async (
    uploadId: number,
    purposeCode: string
  ): Promise<{ status: string; purpose_code: string; record_id: number; effects: Record<string, any> }> => {
    const res = await apiClient.post(`/uploads/${uploadId}/consent/withdraw`, {
      purpose_code: purposeCode,
    });
    return res.data;
  },

  // Reacceptance
  reacceptConsent: async (payload: {
    terms_accepted: boolean;
    privacy_accepted: boolean;
  }) => {
    const res = await apiClient.post('/auth/reaccept-consent', payload);
    return res.data;
  },

  // Takedowns (Public)
  submitTakedownRequest: async (payload: {
    upload_id: number;
    claimant_name: string;
    claimant_email: string;
    reason: string;
    details: string;
  }): Promise<TakedownRequest> => {
    const res = await apiClient.post<TakedownRequest>('/consent/takedown-requests', payload);
    return res.data;
  },

  // Data Rights (Data Principal)
  exportUserData: async (): Promise<DataExport> => {
    const res = await apiClient.get<DataExport>('/consent/me/data-export');
    return res.data;
  },

  requestAccountDeletion: async (reason?: string): Promise<DeletionRequest> => {
    const res = await apiClient.post<DeletionRequest>('/consent/me/deletion-request', { reason });
    return res.data;
  },

  // Admin
  getConsentReport: async (): Promise<ConsentReport> => {
    const res = await apiClient.get<ConsentReport>('/consent/admin/report');
    return res.data;
  },

  getAdminTakedowns: async (): Promise<TakedownRequest[]> => {
    const res = await apiClient.get<TakedownRequest[]>('/consent/admin/takedowns');
    return res.data;
  },

  actionAdminTakedown: async (
    takedownId: number,
    action: string,
    adminNotes?: string
  ) => {
    const res = await apiClient.post(`/consent/admin/takedowns/${takedownId}/action`, null, {
      params: { action, admin_notes: adminNotes },
    });
    return res.data;
  },

  getAdminDeletions: async (): Promise<DeletionRequest[]> => {
    const res = await apiClient.get<DeletionRequest[]>('/consent/admin/deletions');
    return res.data;
  },

  approveAdminDeletion: async (deletionId: number, adminNotes?: string): Promise<DeletionRequest> => {
    const res = await apiClient.post<DeletionRequest>(
      `/consent/admin/deletions/${deletionId}/approve`,
      null,
      { params: { admin_notes: adminNotes } }
    );
    return res.data;
  },
};
