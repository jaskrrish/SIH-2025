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
    async syncEmails(accountId: number) {
        const response = await fetch(API_ENDPOINTS.MAIL.SYNC(accountId), {
            headers: authUtils.getAuthHeaders()
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to sync emails');
        }
        
        return response.json();
    },
    
    async listEmails(accountId?: number, limit = 50) {
        const params = new URLSearchParams();
        if (accountId) params.append('account_id', accountId.toString());
        params.append('limit', limit.toString());
        
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
    
    async sendEmail(accountId: number, toEmails: string[], subject: string, bodyText: string, bodyHtml?: string, securityLevel: 'regular' | 'aes' | 'qkd' | 'qrng_pqc' = 'regular') {
        const response = await fetch(API_ENDPOINTS.MAIL.SEND, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...authUtils.getAuthHeaders()
            },
            body: JSON.stringify({
                account_id: accountId,
                to_emails: toEmails,
                subject,
                body_text: bodyText,
                body_html: bodyHtml,
                security_level: securityLevel
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to send email');
        }
        
        return response.json();
    }
};

export default API_BASE_URL;
