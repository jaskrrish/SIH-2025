import { authUtils } from './auth';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URI || 'http://127.0.0.1:8000/api';

export const API_ENDPOINTS = {
    // Auth endpoints
    AUTH: {
        REGISTER: `${API_BASE_URL}/auth/register`,
        LOGIN: `${API_BASE_URL}/auth/login`,
        ME: `${API_BASE_URL}/auth/me`,
    },
    
    // Email account endpoints
    EMAIL_ACCOUNTS: {
        LIST: `${API_BASE_URL}/email-accounts/`,
        CONNECT: `${API_BASE_URL}/email-accounts/connect`,
        DELETE: (id: number) => `${API_BASE_URL}/email-accounts/${id}`,
    },
    
    // Mail endpoints
    MAIL: {
        SYNC: (accountId: number) => `${API_BASE_URL}/mail/sync/${accountId}`,
        LIST: `${API_BASE_URL}/mail/`,
        SEND: `${API_BASE_URL}/mail/send`,
        DETAIL: (id: number) => `${API_BASE_URL}/mail/${id}`,
    },
    
    // KM endpoints (for future QKD integration)
    KM: {
        STATUS: `${API_BASE_URL}/km/status/`,
        GET_KEY: `${API_BASE_URL}/km/get_key/`,
        GET_KEY_WITH_ID: `${API_BASE_URL}/km/get_key_with_id/`,
    },
    
    // Attachment endpoints
    ATTACHMENTS: {
        DOWNLOAD: (id: number) => `${API_BASE_URL}/mail/attachments/${id}`,
    }
};

// API Helper Functions
export const api = {
    // Auth
    async register(username: string, name: string, password: string, confirmPassword: string) {
        const response = await fetch(API_ENDPOINTS.AUTH.REGISTER, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, name, password, confirm_password: confirmPassword })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Registration failed');
        }
        
        return response.json();
    },
    
    async login(username: string, password: string) {
        const response = await fetch(API_ENDPOINTS.AUTH.LOGIN, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Login failed');
        }
        
        return response.json();
    },
    
    async getMe() {
        const response = await fetch(API_ENDPOINTS.AUTH.ME, {
            headers: authUtils.getAuthHeaders()
        });
        
        if (!response.ok) throw new Error('Failed to get user info');
        return response.json();
    },
    
    // Email Accounts
    async connectEmailAccount(provider: string, email: string, appPassword: string) {
        const response = await fetch(API_ENDPOINTS.EMAIL_ACCOUNTS.CONNECT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...authUtils.getAuthHeaders()
            },
            body: JSON.stringify({ provider, email, app_password: appPassword })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to connect account');
        }
        
        return response.json();
    },
    
    async listEmailAccounts() {
        const response = await fetch(API_ENDPOINTS.EMAIL_ACCOUNTS.LIST, {
            headers: authUtils.getAuthHeaders()
        });
        
        if (!response.ok) throw new Error('Failed to fetch accounts');
        return response.json();
    },
    
    async deleteEmailAccount(accountId: number) {
        const response = await fetch(API_ENDPOINTS.EMAIL_ACCOUNTS.DELETE(accountId), {
            method: 'DELETE',
            headers: authUtils.getAuthHeaders()
        });
        
        if (!response.ok) throw new Error('Failed to delete account');
        return response.json();
    },
    
    // Mail
    async syncEmails(accountId: number, options?: { limit?: number }) {
        const params = new URLSearchParams();
        if (options?.limit) params.append('limit', options.limit.toString());

        const url = params.toString()
            ? `${API_ENDPOINTS.MAIL.SYNC(accountId)}?${params.toString()}`
            : API_ENDPOINTS.MAIL.SYNC(accountId);

        const response = await fetch(url, {
            headers: authUtils.getAuthHeaders()
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to sync emails');
        }
        
        return response.json();
    },
    
    async listEmails(accountId?: number, limit = 50, since?: string) {
        const params = new URLSearchParams();
        if (accountId) params.append('account_id', accountId.toString());
        params.append('limit', limit.toString());
        if (since) params.append('since', since);
        
        const response = await fetch(`${API_ENDPOINTS.MAIL.LIST}?${params}`, {
            headers: authUtils.getAuthHeaders()
        });
        
        if (!response.ok) throw new Error('Failed to fetch emails');
        return response.json();
    },
    
    async getEmail(emailId: number) {
        const response = await fetch(API_ENDPOINTS.MAIL.DETAIL(emailId), {
            headers: authUtils.getAuthHeaders()
        });
        
        if (!response.ok) throw new Error('Failed to fetch email');
        return response.json();
    },
    
    async sendEmail(accountId: number, toEmails: string[], subject: string, bodyText: string, bodyHtml?: string, securityLevel: 'regular' | 'aes' | 'qs_otp' | 'qkd' | 'qrng_pqc' = 'regular', attachments?: File[]) {
        // Use FormData for file uploads
        const formData = new FormData();
        formData.append('account_id', accountId.toString());
        formData.append('to_emails', JSON.stringify(toEmails));
        formData.append('subject', subject);
        formData.append('body_text', bodyText);
        if (bodyHtml) {
            formData.append('body_html', bodyHtml);
        }
        formData.append('security_level', securityLevel);
        
        // Add attachments if provided
        if (attachments && attachments.length > 0) {
            attachments.forEach(file => {
                formData.append('attachments', file);
            });
        }
        
        // Get auth headers but exclude Content-Type for FormData (browser will set it with boundary)
        const authHeaders: HeadersInit = {};
        const token = authUtils.getToken();
        if (token) {
            authHeaders['Authorization'] = `Bearer ${token}`;
        }
        
        const response = await fetch(API_ENDPOINTS.MAIL.SEND, {
            method: 'POST',
            headers: authHeaders, // Don't set Content-Type - browser will set it with boundary for multipart/form-data
            body: formData
        });
        
        if (!response.ok) {
            let errorMessage = 'Failed to send email';
            try {
                const error = await response.json();
                // Handle DRF validation errors
                if (error.to_emails) {
                    errorMessage = `Validation error: ${JSON.stringify(error.to_emails)}`;
                } else if (error.account_id) {
                    errorMessage = `Validation error: ${JSON.stringify(error.account_id)}`;
                } else if (error.subject) {
                    errorMessage = `Validation error: ${JSON.stringify(error.subject)}`;
                } else if (error.body_text) {
                    errorMessage = `Validation error: ${JSON.stringify(error.body_text)}`;
                } else if (error.security_level) {
                    errorMessage = `Validation error: ${JSON.stringify(error.security_level)}`;
                } else if (error.error) {
                    errorMessage = error.error;
                } else if (typeof error === 'string') {
                    errorMessage = error;
                } else {
                    errorMessage = JSON.stringify(error);
                }
            } catch (e) {
                errorMessage = `Server error: ${response.status} ${response.statusText}`;
            }
            throw new Error(errorMessage);
        }
        
        return response.json();
    },
    
    // Attachments
    async downloadAttachment(attachmentId: number, filename?: string) {
        const response = await fetch(API_ENDPOINTS.ATTACHMENTS.DOWNLOAD(attachmentId), {
            headers: authUtils.getAuthHeaders()
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to download attachment');
        }
        
        // Use provided filename, or extract from Content-Disposition header
        let downloadFilename = filename || 'attachment';
        if (!filename) {
            const contentDisposition = response.headers.get('Content-Disposition');
            if (contentDisposition) {
                // Try to get filename from filename* (UTF-8 encoded) first - this is the standard way
                const filenameStarMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/);
                if (filenameStarMatch) {
                    try {
                        downloadFilename = decodeURIComponent(filenameStarMatch[1]);
                    } catch (e) {
                        // If decoding fails, try regular filename
                        const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
                        if (filenameMatch) {
                            downloadFilename = filenameMatch[1];
                        }
                    }
                } else {
                    // Fallback to regular filename (with quotes)
                    const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
                    if (filenameMatch) {
                        downloadFilename = filenameMatch[1];
                    } else {
                        // Try without quotes
                        const filenameMatchNoQuotes = contentDisposition.match(/filename=([^;]+)/);
                        if (filenameMatchNoQuotes) {
                            downloadFilename = filenameMatchNoQuotes[1].trim();
                        }
                    }
                }
            }
        }
        
        // Create blob and download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = downloadFilename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }
};

export default API_BASE_URL;
