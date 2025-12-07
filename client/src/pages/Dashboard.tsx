import { useState, useEffect } from 'react';
import { ShieldCheck, Plus, Mail, ChevronRight, Settings, LogOut, Check, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { api } from '@/lib/api';

interface EmailAccountData {
    id: string;
    email: string;
    provider: 'gmail' | 'outlook' | 'yahoo' | 'qutemail' | 'custom';
    unreadCount: number;
}

interface DashboardProps {
    userData: { username: string; email: string };
    onSelectAccount: (account: EmailAccountData) => void;
    onLogout: () => void;
}

type ProviderType = 'gmail' | 'outlook' | 'yahoo' | 'custom';

interface Provider {
    id: ProviderType;
    name: string;
    icon: string;
    placeholder: string;
    helpLink?: string;
}

const EMAIL_PROVIDERS: Provider[] = [
    {
        id: 'gmail',
        name: 'Gmail',
        icon: '📧',
        placeholder: 'your-email@gmail.com',
        helpLink: 'https://myaccount.google.com/apppasswords'
    },
    {
        id: 'outlook',
        name: 'Outlook',
        icon: '📨',
        placeholder: 'your-email@outlook.com',
        helpLink: 'https://account.live.com/proofs/AppPassword'
    },
    {
        id: 'yahoo',
        name: 'Yahoo Mail',
        icon: '💌',
        placeholder: 'your-email@yahoo.com',
        helpLink: 'https://login.yahoo.com/account/security'
    },
    {
        id: 'custom',
        name: 'Custom IMAP',
        icon: '⚙️',
        placeholder: 'your-email@custom.com'
    }
];

export default function Dashboard({ userData, onSelectAccount, onLogout }: DashboardProps) {
    const [emailAccounts, setEmailAccounts] = useState<EmailAccountData[]>([
        {
            id: 'qutemail',
            email: userData.email,
            provider: 'qutemail',
            unreadCount: 0
        }
    ]);
    const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
    const [selectedProvider, setSelectedProvider] = useState<ProviderType | null>(null);
    const [emailAddress, setEmailAddress] = useState('');
    const [appPassword, setAppPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [fetchingAccounts, setFetchingAccounts] = useState(true);

    // Fetch connected email accounts on mount
    useEffect(() => {
        fetchEmailAccounts();
    }, []);

    const fetchEmailAccounts = async () => {
        try {
            setFetchingAccounts(true);
            const accounts = await api.listEmailAccounts();
            
            // Map backend accounts to frontend format
            const mappedAccounts = accounts.map((acc: any) => ({
                id: acc.id.toString(),
                email: acc.email,
                provider: acc.provider as 'gmail' | 'outlook' | 'yahoo' | 'custom',
                unreadCount: 0 // TODO: Get unread count from backend
            }));
            
            // Add QuteMail account at the beginning
            setEmailAccounts([
                {
                    id: 'qutemail',
                    email: userData.email,
                    provider: 'qutemail',
                    unreadCount: 0
                },
                ...mappedAccounts
            ]);
        } catch (err: any) {
            console.error('Failed to fetch accounts:', err);
        } finally {
            setFetchingAccounts(false);
        }
    };

    const handleAddEmail = async (e: React.FormEvent) => {
        e.preventDefault();
        
        if (!selectedProvider) return;
        
        setLoading(true);
        setError('');
        
        try {
            // Connect account via API
            const newAccount = await api.connectEmailAccount(
                selectedProvider,
                emailAddress,
                appPassword
            );
            
            // Add to local state
            setEmailAccounts([
                ...emailAccounts,
                {
                    id: newAccount.id.toString(),
                    email: newAccount.email,
                    provider: newAccount.provider as 'gmail' | 'outlook' | 'yahoo' | 'custom',
                    unreadCount: 0
                }
            ]);
            
            // Reset form and close dialog
            setIsAddDialogOpen(false);
            setSelectedProvider(null);
            setEmailAddress('');
            setAppPassword('');
        } catch (err: any) {
            setError(err.message || 'Failed to connect account. Please check your credentials.');
            console.error('Failed to connect account:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleDialogClose = (open: boolean) => {
        setIsAddDialogOpen(open);
        if (!open) {
            setSelectedProvider(null);
            setEmailAddress('');
            setAppPassword('');
            setError('');
        }
    };

    return (
        <div className="min-h-screen w-full bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
            {/* Header */}
            <div className="border-b border-gray-200 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-xl bg-[#032848] flex items-center justify-center">
                            <ShieldCheck className="h-6 w-6 text-[#f4711b]" />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold text-gray-900">QuteMail</h1>
                            <p className="text-xs text-gray-500">Welcome, {userData.username}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        <Button variant="ghost" size="sm" className="gap-2">
                            <Settings className="h-4 w-4" />
                            Settings
                        </Button>
                        <Button variant="ghost" size="sm" className="gap-2 text-red-600 hover:text-red-700 hover:bg-red-50" onClick={onLogout}>
                            <LogOut className="h-4 w-4" />
                            Logout
                        </Button>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="max-w-7xl mx-auto px-6 py-12">
                <div className="mb-8">
                    <h2 className="text-3xl font-bold text-gray-900 mb-2">Your Email Accounts</h2>
                    <p className="text-gray-600">Manage and access all your email accounts in one secure place</p>
                </div>

                {/* Email Accounts Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
                    {fetchingAccounts ? (
                        <div className="col-span-full flex items-center justify-center py-12">
                            <Loader2 className="h-8 w-8 animate-spin text-[#f4711b]" />
                        </div>
                    ) : (
                        <>
                            {emailAccounts.map((account) => (
                                <Card 
                                    key={account.id}
                                    className="cursor-pointer hover:shadow-lg transition-all border-2 hover:border-[#f4711b]/30 group"
                                    onClick={() => onSelectAccount(account)}
                                >
                                    <CardHeader className="pb-3">
                                        <div className="flex items-center justify-between">
                                            <div className="h-12 w-12 rounded-xl bg-[#032848] flex items-center justify-center group-hover:scale-110 transition-transform">
                                                <Mail className="h-6 w-6 text-[#f4711b]" />
                                            </div>
                                            {account.unreadCount > 0 && (
                                                <span className="px-2.5 py-0.5 rounded-full bg-[#f4711b] text-white text-xs font-semibold">
                                                    {account.unreadCount}
                                                </span>
                                            )}
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        <h3 className="font-semibold text-gray-900 mb-1 truncate">{account.email}</h3>
                                        <div className="flex items-center justify-between">
                                            <span className="text-sm text-gray-500 capitalize">{account.provider}</span>
                                            <ChevronRight className="h-4 w-4 text-gray-400 group-hover:text-[#f4711b] group-hover:translate-x-1 transition-all" />
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}

                            {/* Add Account Card */}
                            <Dialog open={isAddDialogOpen} onOpenChange={handleDialogClose}>
                                <DialogTrigger asChild>
                                    <Card className="cursor-pointer hover:shadow-lg transition-all border-2 border-dashed border-gray-300 hover:border-[#f4711b] group">
                                        <CardContent className="flex flex-col items-center justify-center h-full min-h-[180px] text-center">
                                            <div className="h-12 w-12 rounded-xl bg-gray-100 group-hover:bg-[#f4711b]/10 flex items-center justify-center mb-3 group-hover:scale-110 transition-all">
                                                <Plus className="h-6 w-6 text-gray-400 group-hover:text-[#f4711b]" />
                                            </div>
                                            <h3 className="font-semibold text-gray-900 mb-1">Connect Email Account</h3>
                                            <p className="text-sm text-gray-500">Gmail, Outlook, Yahoo, or Custom IMAP</p>
                                        </CardContent>
                                    </Card>
                                </DialogTrigger>
                                <DialogContent className="sm:max-w-xl">
                                    <DialogHeader>
                                        <DialogTitle>Connect External Email Account</DialogTitle>
                                    </DialogHeader>
                                    
                                    {!selectedProvider ? (
                                        // Provider Selection View
                                        <div className="space-y-3 mt-4">
                                            <p className="text-sm text-gray-600 mb-4">Choose your email provider:</p>
                                            <div className="grid grid-cols-2 gap-3">
                                                {EMAIL_PROVIDERS.map((provider) => (
                                                    <button
                                                        key={provider.id}
                                                        onClick={() => setSelectedProvider(provider.id)}
                                                        className="p-4 rounded-xl border-2 border-gray-200 hover:border-[#f4711b] hover:bg-[#f4711b]/5 transition-all text-left group"
                                                    >
                                                        <div className="text-3xl mb-2">{provider.icon}</div>
                                                        <h4 className="font-semibold text-gray-900 group-hover:text-[#f4711b] transition-colors">
                                                            {provider.name}
                                                        </h4>
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    ) : (
                                        // Email & Password Form
                                        <form onSubmit={handleAddEmail} className="space-y-4 mt-4">
                                            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                                                <span className="text-2xl">
                                                    {EMAIL_PROVIDERS.find(p => p.id === selectedProvider)?.icon}
                                                </span>
                                                <div className="flex-1">
                                                    <p className="text-sm font-semibold text-gray-900">
                                                        {EMAIL_PROVIDERS.find(p => p.id === selectedProvider)?.name}
                                                    </p>
                                                </div>
                                                <button
                                                    type="button"
                                                    onClick={() => setSelectedProvider(null)}
                                                    className="text-sm text-[#f4711b] hover:text-[#f4711b]/80 font-medium"
                                                >
                                                    Change
                                                </button>
                                            </div>

                                            <div className="space-y-2">
                                                <Label htmlFor="email-address">Email Address</Label>
                                                <Input
                                                    id="email-address"
                                                    type="email"
                                                    placeholder={EMAIL_PROVIDERS.find(p => p.id === selectedProvider)?.placeholder}
                                                    value={emailAddress}
                                                    onChange={(e) => setEmailAddress(e.target.value)}
                                                    required
                                                />
                                            </div>
                                            
                                            <div className="space-y-2">
                                                <Label htmlFor="app-password">App Password</Label>
                                                <Input
                                                    id="app-password"
                                                    type="password"
                                                    placeholder="xxxx xxxx xxxx xxxx"
                                                    value={appPassword}
                                                    onChange={(e) => setAppPassword(e.target.value)}
                                                    required
                                                />
                                                {EMAIL_PROVIDERS.find(p => p.id === selectedProvider)?.helpLink && (
                                                    <p className="text-xs text-gray-500">
                                                        Generate an app password from your{' '}
                                                        <a 
                                                            href={EMAIL_PROVIDERS.find(p => p.id === selectedProvider)?.helpLink}
                                                            target="_blank" 
                                                            rel="noopener noreferrer"
                                                            className="text-[#f4711b] hover:underline font-medium"
                                                        >
                                                            account security settings
                                                        </a>
                                                    </p>
                                                )}
                                            </div>

                                            {/* Error Message */}
                                            {error && (
                                                <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                                                    <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                                                </div>
                                            )}

                                            <div className="flex gap-3 pt-4">
                                                <Button
                                                    type="button"
                                                    variant="outline"
                                                    className="flex-1"
                                                    onClick={() => handleDialogClose(false)}
                                                >
                                                    Cancel
                                                </Button>
                                                <Button
                                                    type="submit"
                                                    disabled={loading}
                                                    className="flex-1 bg-[#f4711b] hover:bg-[#f4711b]/90 disabled:opacity-50"
                                                >
                                                    {loading ? (
                                                        <>
                                                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                                            Connecting...
                                                        </>
                                                    ) : (
                                                        <>
                                                            <Check className="h-4 w-4 mr-2" />
                                                            Connect Account
                                                        </>
                                                    )}
                                                </Button>
                                            </div>
                                        </form>
                                    )}
                                </DialogContent>
                            </Dialog>
                        </>
                    )}
                </div>

                {/* Info Banner */}
                <Card className="bg-[#032848] border-[#032848]">
                    <CardContent className="p-6">
                        <div className="flex items-start gap-4">
                            <div className="h-10 w-10 rounded-lg bg-[#f4711b]/20 flex items-center justify-center shrink-0">
                                <ShieldCheck className="h-5 w-5 text-[#f4711b]" />
                            </div>
                            <div>
                                <h3 className="text-white font-semibold mb-1">Quantum Encryption Active</h3>
                                <p className="text-white/80 text-sm">
                                    All emails sent through QuteMail are encrypted using Quantum Key Distribution (QKD) technology, 
                                    providing unbreakable security for your communications.
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
