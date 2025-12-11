import { Routes, Route, Navigate, useNavigate, useParams } from 'react-router-dom';
import { useEffect, useState, lazy, Suspense } from 'react';
import { authUtils, type UserData } from './lib/auth';

// Lazy load page components for code-splitting
const Auth = lazy(() => import('./pages/Auth'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Mailbox = lazy(() => import('./pages/Mailbox'));
const KeyMonitor = lazy(() => import('./pages/KeyMonitor'));

interface EmailAccount {
    id: string;
    email: string;
    provider: string;
    unreadCount?: number;
}

interface AccountDto {
    id: number | string;
    email: string;
    provider: string;
}

const getErrorMessage = (err: unknown) =>
    err instanceof Error ? err.message : 'Failed to load account';

// Protected Route Component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
    const isAuthenticated = authUtils.isAuthenticated();
    
    if (!isAuthenticated) {
        return <Navigate to="/auth" replace />;
    }
    
    return <>{children}</>;
}

// Auth Route Component (redirect to dashboard if already logged in)
function AuthRoute({ children }: { children: React.ReactNode }) {
    const isAuthenticated = authUtils.isAuthenticated();
    
    if (isAuthenticated) {
        return <Navigate to="/dashboard" replace />;
    }
    
    return <>{children}</>;
}

// Auth Page Wrapper
function AuthPage() {
    const navigate = useNavigate();
    
    const handleLogin = (user: UserData) => {
        // Token is already stored by Auth component
        // Just store user data and navigate
        authUtils.setUser(user);
        navigate('/dashboard');
    };
    
    return <Auth onLogin={handleLogin} />;
}

// Dashboard Page Wrapper
function DashboardPage() {
    const navigate = useNavigate();
    const userData = authUtils.getUser();
    
    if (!userData) {
        return <Navigate to="/auth" replace />;
    }
    
    const handleLogout = () => {
        authUtils.clearAuth();
        navigate('/auth');
    };
    
    const handleSelectAccount = (account: EmailAccount) => {
        navigate(`/mailbox/${account.id}`);
    };

    const handleOpenKeys = () => {
        navigate('/keys');
    };
    
    return (
        <Dashboard 
            userData={userData}
            onSelectAccount={handleSelectAccount}
            onLogout={handleLogout}
            onOpenKeys={handleOpenKeys}
        />
    );
}

// Mailbox Page Wrapper
function MailboxPage() {
    const navigate = useNavigate();
    const { accountId } = useParams<{ accountId: string }>();
    const [account, setAccount] = useState<EmailAccount | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    
    useEffect(() => {
        async function fetchAccount() {
            if (!accountId) return;
            
            try {
                setLoading(true);
                
                // Handle QuteMail account specially (not a real email account)
                if (accountId === 'qutemail') {
                    const userData = authUtils.getUser();
                    if (userData) {
                        setAccount({
                            id: 'qutemail',
                            email: userData.email,
                            provider: 'qutemail',
                            unreadCount: 0
                        });
                        setLoading(false);
                        return;
                    }
                }
                
                // Import api dynamically to avoid circular dependencies
                const { api } = await import('./lib/api');
                const accounts: AccountDto[] = await api.listEmailAccounts();
                const foundAccount = accounts.find((acc) => acc.id.toString() === accountId);
                
                if (foundAccount) {
                    setAccount({
                        id: foundAccount.id.toString(),
                        email: foundAccount.email,
                        provider: foundAccount.provider,
                        unreadCount: 0
                    });
                } else {
                    setError('Account not found');
                }
            } catch (err: unknown) {
                console.error('Failed to fetch account:', err);
                setError(getErrorMessage(err));
            } finally {
                setLoading(false);
            }
        }
        
        fetchAccount();
    }, [accountId]);
    
    const handleBack = () => {
        navigate('/dashboard');
    };
    
    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto mb-4"></div>
                    <p className="text-gray-600">Loading account...</p>
                </div>
            </div>
        );
    }
    
    if (error || !account) {
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="text-center">
                    <p className="text-red-600 mb-4">{error || 'Account not found'}</p>
                    <button 
                        onClick={() => navigate('/dashboard')}
                        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                        Back to Dashboard
                    </button>
                </div>
            </div>
        );
    }
    
    return (
        <Mailbox 
            account={account}
            onBack={handleBack}
        />
    );
}

// Key Monitor Page Wrapper (per mailbox)
function KeyMonitorPage() {
    const navigate = useNavigate();
    const { accountId } = useParams<{ accountId: string }>();
    const [account, setAccount] = useState<EmailAccount | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        async function fetchAccount() {
            if (!accountId) return;
            try {
                setLoading(true);
                // Handle QuteMail account specially
                if (accountId === 'qutemail') {
                    const userData = authUtils.getUser();
                    if (userData) {
                        setAccount({
                            id: 'qutemail',
                            email: userData.email,
                            provider: 'qutemail',
                            unreadCount: 0,
                        });
                        setLoading(false);
                        return;
                    }
                }

                const { api } = await import('./lib/api');
                const accounts: AccountDto[] = await api.listEmailAccounts();
                const found = accounts.find((acc) => acc.id.toString() === accountId);
                if (found) {
                    setAccount({
                        id: found.id.toString(),
                        email: found.email,
                        provider: found.provider,
                        unreadCount: 0,
                    });
                } else {
                    setError('Account not found');
                }
            } catch (err: unknown) {
                console.error('Failed to fetch account:', err);
                setError(getErrorMessage(err));
            } finally {
                setLoading(false);
            }
        }
        fetchAccount();
    }, [accountId]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto mb-4"></div>
                    <p className="text-gray-600">Loading account...</p>
                </div>
            </div>
        );
    }

    if (error || !account) {
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="text-center">
                    <p className="text-red-600 mb-4">{error || 'Account not found'}</p>
                    <button
                        onClick={() => navigate('/dashboard')}
                        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                        Back to Dashboard
                    </button>
                </div>
            </div>
        );
    }

    return (
        <KeyMonitor
            email={account.email}
            backTo={`/mailbox/${account.id}`}
            label={account.email}
        />
    );
}

// Key Monitor for current user (fallback)
function MyKeysPage() {
    const user = authUtils.getUser();

    if (!user) {
        return <Navigate to="/auth" replace />;
    }

    return (
        <KeyMonitor
            email={user.email}
            backTo="/dashboard"
            label={user.email}
        />
    );
}

export default function Router() {
    return (
        <Suspense fallback={
            <div className="flex items-center justify-center h-screen">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto mb-4"></div>
                    <p className="text-gray-600">Loading...</p>
                </div>
            </div>
        }>
            <Routes>
                {/* Auth Route */}
                <Route 
                    path="/auth" 
                    element={
                        <AuthRoute>
                            <AuthPage />
                        </AuthRoute>
                    } 
                />
                
                {/* Dashboard Route */}
                <Route 
                    path="/dashboard" 
                    element={
                        <ProtectedRoute>
                            <DashboardPage />
                        </ProtectedRoute>
                    } 
                />
                
                {/* Mailbox Route */}
                <Route 
                    path="/mailbox/:accountId" 
                    element={
                        <ProtectedRoute>
                            <MailboxPage />
                        </ProtectedRoute>
                    } 
                />

                {/* Key Monitor per mailbox */}
                <Route
                    path="/mailbox/:accountId/keys"
                    element={
                        <ProtectedRoute>
                            <KeyMonitorPage />
                        </ProtectedRoute>
                    }
                />

                {/* Key monitor for logged-in user (fallback) */}
                <Route
                    path="/keys"
                    element={
                        <ProtectedRoute>
                            <MyKeysPage />
                        </ProtectedRoute>
                    }
                />

                {/* Default Route */}
                <Route 
                    path="*" 
                    element={<Navigate to="/auth" replace />} 
                />
            </Routes>
        </Suspense>
    );
}
