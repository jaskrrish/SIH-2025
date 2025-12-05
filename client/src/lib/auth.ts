// Authentication utilities and token management

const TOKEN_KEY = 'qutemail_auth_token';
const USER_KEY = 'qutemail_user_data';

export interface UserData {
    username: string;
    email: string;
    name?: string;
}

export const authUtils = {
    // Token management
    setToken: (token: string) => {
        localStorage.setItem(TOKEN_KEY, token);
    },
    
    getToken: (): string | null => {
        return localStorage.getItem(TOKEN_KEY);
    },
    
    removeToken: () => {
        localStorage.removeItem(TOKEN_KEY);
    },
    
    // User data management
    setUser: (user: UserData) => {
        localStorage.setItem(USER_KEY, JSON.stringify(user));
    },
    
    getUser: (): UserData | null => {
        const userData = localStorage.getItem(USER_KEY);
        return userData ? JSON.parse(userData) : null;
    },
    
    removeUser: () => {
        localStorage.removeItem(USER_KEY);
    },
    
    // Check if user is authenticated
    isAuthenticated: (): boolean => {
        return !!localStorage.getItem(TOKEN_KEY);
    },
    
    // Clear all auth data
    clearAuth: () => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
    },
    
    // Get auth headers for API requests
    getAuthHeaders: (): HeadersInit => {
        const token = authUtils.getToken();
        return {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
        };
    }
};
