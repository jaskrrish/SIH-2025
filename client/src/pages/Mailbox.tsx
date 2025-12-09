import { useState, useEffect } from 'react';
import { ArrowLeft, RefreshCw, ShieldCheck, Plus, Search, Star, Menu, MoreVertical, Reply, X, Paperclip, Lock, Inbox, Send as SendIcon, FileText, Trash2, Download } from 'lucide-react';
import { EncryptedText } from "@/components/ui/encrypted-text";
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { api } from '@/lib/api';
import AccessibilityTools from '@/components/AccessibilityTools';

// Utility for tailwind class merging
function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface MailboxProps {
    account: {
        id: string;
        email: string;
        provider: string;
    };
    onBack: () => void;
}

interface Attachment {
  filename: string;
  content_type: string;
  size: number;
  data: string;  // Base64 encoded attachment data
  is_encrypted: boolean;
  security_level: string;
}

interface Email {
  id: number;
  message_id: string;
  from_email: string;
  from_name: string;
  to_emails: string[];
  subject: string;
  body_text: string;
  body_html: string;
  sent_at: string;
  is_read: boolean;
  is_starred: boolean;
  is_encrypted: boolean;
  security_level?: string;
  attachments?: Attachment[];
}

export default function Mailbox({ account, onBack }: MailboxProps) {
  const [emails, setEmails] = useState<Email[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState('');
  const [lastSynced, setLastSynced] = useState<Date | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isComposeOpen, setIsComposeOpen] = useState(false);
  const [selectedFolder, setSelectedFolder] = useState<'inbox' | 'sent' | 'drafts' | 'trash'>('inbox');
  const [encryptionMethod, setEncryptionMethod] = useState<'regular' | 'aes' | 'qs_otp' | 'qkd' | 'qkd_pqc'>('qkd');
  
  // Compose form state
  const [composeTo, setComposeTo] = useState('');
  const [composeSubject, setComposeSubject] = useState('');
  const [composeBody, setComposeBody] = useState('');
  const [sending, setSending] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  // Check if account is configured for email operations
  const isAccountConfigured = () => {
    if (account.id === 'qutemail' && account.email !== 'aalan@qutemail.tech') {
      return false;
    }
    return true;
  };

  // Fetch emails on mount
  useEffect(() => {
    // Skip loading for unconfigured qutemail accounts
    if (account.id === 'qutemail' && account.email !== 'aalan@qutemail.tech') {
      setLoading(false);
      return;
    }
    loadEmails();
  }, [account.id]);

  const loadEmails = async () => {
    // Skip loading for unconfigured qutemail accounts
    if (account.id === 'qutemail' && account.email !== 'aalan@qutemail.tech') {
      return;
    }
    
    try {
      setLoading(true);
      setError('');
      const data = await api.listEmails(parseInt(account.id));
      setEmails(data);
      if (data.length > 0 && !selectedEmail) {
        setSelectedEmail(data[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load emails');
    } finally {
      setLoading(false);
    }
  };

  const handleEmailClick = async (email: Email) => {
    // If email already has body content, just select it
    if (email.body_text) {
      setSelectedEmail(email);
      return;
    }
    
    // Otherwise, fetch full email content from API
    try {
      const fullEmail = await api.getEmail(email.id);
      setSelectedEmail(fullEmail);
      
      // Update the email in the list with full content
      setEmails(prev => prev.map(e => e.id === fullEmail.id ? fullEmail : e));
    } catch (err: any) {
      console.error('Failed to fetch email:', err);
      setError('Failed to load email content');
    }
  };

  const handleSync = async () => {
    if (account.id === 'qutemail') {
      // Check if this is a configured QuTeMail account (only aalan@qutemail.tech)
      if (account.email !== 'aalan@qutemail.tech') {
        alert('QuTeMail accounts are not yet configured for email services. Only aalan@qutemail.tech is currently operational. Please connect external email accounts (Gmail, Outlook, etc.) to send and receive emails.');
        return;
      }
    }
    
    try {
      setSyncing(true);
      setError('');
      await api.syncEmails(parseInt(account.id));
      await loadEmails();
      setLastSynced(new Date());
    } catch (err: any) {
      setError(err.message || 'Failed to sync emails');
    } finally {
      setSyncing(false);
    }
  };

  const handleSendEmail = async () => {
    if (!composeTo || !composeSubject || !composeBody) {
      alert('Please fill in all fields');
      return;
    }

    // Check if QuTeMail account is configured before sending
    if (account.id === 'qutemail' && account.email !== 'aalan@qutemail.tech') {
      alert('QuTeMail accounts are not yet configured for email services. Only aalan@qutemail.tech is currently operational. Please connect external email accounts (Gmail, Outlook, etc.) to send and receive emails.');
      return;
    }

    try {
      setSending(true);
      await api.sendEmail(
        parseInt(account.id),
        [composeTo],
        composeSubject,
        composeBody,
        undefined,
        encryptionMethod,
        selectedFiles.length > 0 ? selectedFiles : undefined
      );
      
      // Close compose and refresh emails
      setIsComposeOpen(false);
      setComposeTo('');
      setComposeSubject('');
      setComposeBody('');
      setSelectedFiles([]);
      await handleSync();
    } catch (err: any) {
      alert(err.message || 'Failed to send email');
    } finally {
      setSending(false);
    }
  };

  const filteredEmails = emails.filter(() => {
    // For now, all emails go to inbox - we'll add folder support later
    if (selectedFolder === 'inbox') return true;
    return false;
  });

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) {
      return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
    } else if (days === 1) {
      return 'Yesterday';
    } else if (days < 7) {
      return date.toLocaleDateString('en-US', { weekday: 'short' });
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
  };

  return (
    <div className="flex h-screen w-full bg-gray-50 text-gray-900 font-sans overflow-hidden relative">
      <AccessibilityTools />

      {/* --- Compose Modal --- */}
      {isComposeOpen && (
        <div className="absolute inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in duration-200">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-slate-50">
              <h2 className="text-lg font-semibold text-gray-800">New Message</h2>
              <button
                onClick={() => setIsComposeOpen(false)}
                className="p-2 hover:bg-gray-200 rounded-full transition-colors text-gray-500"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 flex-1 overflow-y-auto">
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <label className="w-16 text-sm font-medium text-gray-500">To</label>
                  <input
                    type="email"
                    value={composeTo}
                    onChange={(e) => setComposeTo(e.target.value)}
                    className="flex-1 p-2 border-b border-gray-200 focus:border-isro-blue outline-none transition-colors"
                    placeholder="recipient@example.com"
                  />
                </div>
                <div className="flex items-center gap-3">
                  <label className="w-16 text-sm font-medium text-gray-500">Subject</label>
                  <input
                    type="text"
                    value={composeSubject}
                    onChange={(e) => setComposeSubject(e.target.value)}
                    className="flex-1 p-2 border-b border-gray-200 focus:border-isro-blue outline-none transition-colors"
                    placeholder="Subject"
                  />
                </div>

                {/* Encryption Selection */}
                <div className="space-y-3">
                  <label className="text-sm font-medium text-gray-500">Security Level</label>
                  <div className="grid grid-cols-2 gap-3">
                    {/* Regular - No Encryption */}
                    <button
                      onClick={() => setEncryptionMethod('regular')}
                      className={cn(
                        "p-3 rounded-xl border text-left transition-all relative overflow-hidden",
                        encryptionMethod === 'regular'
                          ? "bg-gray-50 border-gray-300 ring-1 ring-gray-400"
                          : "bg-white border-gray-200 hover:border-gray-300"
                      )}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <div className={cn("p-1.5 rounded-lg", encryptionMethod === 'regular' ? "bg-gray-200 text-gray-600" : "bg-gray-100 text-gray-400")}>
                          <SendIcon className="h-4 w-4" />
                        </div>
                        <span className={cn("font-semibold text-sm", encryptionMethod === 'regular' ? "text-gray-900" : "text-gray-600")}>Regular</span>
                      </div>
                      <p className="text-xs text-gray-500">No encryption</p>
                      {encryptionMethod === 'regular' && (
                        <div className="absolute top-2 right-2 h-2 w-2 rounded-full bg-gray-500" />
                      )}
                    </button>

                    {/* Standard AES */}
                    <button
                      onClick={() => setEncryptionMethod('aes')}
                      className={cn(
                        "p-3 rounded-xl border text-left transition-all relative overflow-hidden",
                        encryptionMethod === 'aes'
                          ? "bg-blue-50 border-blue-200 ring-1 ring-blue-500"
                          : "bg-white border-gray-200 hover:border-gray-300"
                      )}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <div className={cn("p-1.5 rounded-lg", encryptionMethod === 'aes' ? "bg-blue-100 text-blue-600" : "bg-gray-100 text-gray-400")}>
                          <Lock className="h-4 w-4" />
                        </div>
                        <span className={cn("font-semibold text-sm", encryptionMethod === 'aes' ? "text-blue-900" : "text-gray-600")}>Standard AES</span>
                      </div>
                      <p className="text-xs text-gray-500">AES-256-GCM encryption</p>
                      {encryptionMethod === 'aes' && (
                        <div className="absolute top-2 right-2 h-2 w-2 rounded-full bg-blue-500" />
                      )}
                    </button>

                    {/* Quantum Secure OTP */}
                    <button
                      onClick={() => setEncryptionMethod('qs_otp')}
                      className={cn(
                        "p-3 rounded-xl border text-left transition-all relative overflow-hidden",
                        encryptionMethod === 'qs_otp'
                          ? "bg-purple-50 border-purple-200 ring-1 ring-purple-500"
                          : "bg-white border-gray-200 hover:border-gray-300"
                      )}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <div className={cn("p-1.5 rounded-lg", encryptionMethod === 'qs_otp' ? "bg-purple-100 text-purple-600" : "bg-gray-100 text-gray-400")}>
                          <ShieldCheck className="h-4 w-4" />
                        </div>
                        <span className={cn("font-semibold text-sm", encryptionMethod === 'qs_otp' ? "text-purple-900" : "text-gray-600")}>Quantum OTP</span>
                      </div>
                      <p className="text-xs text-gray-500">QKD one-time pad</p>
                      {encryptionMethod === 'qs_otp' && (
                        <div className="absolute top-2 right-2 h-2 w-2 rounded-full bg-purple-500" />
                      )}
                    </button>

                    {/* QKD + AES */}
                    <button
                      onClick={() => setEncryptionMethod('qkd')}
                      className={cn(
                        "p-3 rounded-xl border text-left transition-all relative overflow-hidden",
                        encryptionMethod === 'qkd'
                          ? "bg-emerald-50 border-emerald-200 ring-1 ring-emerald-500"
                          : "bg-white border-gray-200 hover:border-gray-300"
                      )}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <div className={cn("p-1.5 rounded-lg", encryptionMethod === 'qkd' ? "bg-isro-blue/10 text-isro-blue" : "bg-gray-100 text-gray-400")}>
                          <ShieldCheck className="h-4 w-4" />
                        </div>
                        <span className={cn("font-semibold text-sm", encryptionMethod === 'qkd' ? "text-isro-blue" : "text-gray-600")}>QKD + AES</span>
                      </div>
                      <p className="text-xs text-gray-500">BB84 quantum keys</p>
                      {encryptionMethod === 'qkd' && (
                        <div className="absolute top-2 right-2 h-2 w-2 rounded-full bg-emerald-500" />
                      )}
                    </button>

                    {/* QKD + PQC */}
                    <button
                      onClick={() => setEncryptionMethod('qkd_pqc')}
                      className={cn(
                        "p-3 rounded-xl border text-left transition-all relative overflow-hidden",
                        encryptionMethod === 'qkd_pqc'
                          ? "bg-indigo-50 border-indigo-200 ring-1 ring-indigo-500"
                          : "bg-white border-gray-200 hover:border-gray-300"
                      )}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <div className={cn("p-1.5 rounded-lg", encryptionMethod === 'qkd_pqc' ? "bg-indigo-100 text-indigo-600" : "bg-gray-100 text-gray-400")}>
                          <ShieldCheck className="h-4 w-4" />
                        </div>
                        <span className={cn("font-semibold text-sm", encryptionMethod === 'qkd_pqc' ? "text-indigo-900" : "text-gray-600")}>QKD + PQC</span>
                      </div>
                      <p className="text-xs text-gray-500">Post-quantum secure</p>
                      {encryptionMethod === 'qkd_pqc' && (
                        <div className="absolute top-2 right-2 h-2 w-2 rounded-full bg-indigo-500" />
                      )}
                    </button>
                  </div>
                </div>

                <textarea
                  value={composeBody}
                  onChange={(e) => setComposeBody(e.target.value)}
                  className="w-full h-64 p-4 bg-gray-50 rounded-lg border-transparent focus:bg-white focus:ring-2 focus:ring-isro-blue focus:border-transparent resize-none outline-none text-gray-700"
                  placeholder="Write your message here..."
                ></textarea>

                {/* File Input (Hidden) */}
                <input
                  type="file"
                  id="attachment-input"
                  multiple
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files) {
                      setSelectedFiles(Array.from(e.target.files));
                    }
                  }}
                />

                {/* Selected Files Display */}
                {selectedFiles.length > 0 && (
                  <div className="mt-4 space-y-2">
                    <p className="text-sm font-medium text-gray-700">Attachments ({selectedFiles.length}):</p>
                    <div className="space-y-2 max-h-32 overflow-y-auto">
                      {selectedFiles.map((file, index) => (
                        <div key={index} className="flex items-center justify-between p-2 bg-gray-100 rounded-lg">
                          <div className="flex items-center gap-2 flex-1 min-w-0">
                            <Paperclip className="h-4 w-4 text-gray-500 shrink-0" />
                            <span className="text-sm text-gray-700 truncate">{file.name}</span>
                            <span className="text-xs text-gray-500 shrink-0">
                              ({(file.size / 1024).toFixed(1)} KB)
                            </span>
                          </div>
                          <button
                            onClick={() => {
                              const newFiles = selectedFiles.filter((_, i) => i !== index);
                              setSelectedFiles(newFiles);
                              // Reset file input
                              const fileInput = document.getElementById('attachment-input') as HTMLInputElement;
                              if (fileInput) fileInput.value = '';
                            }}
                            className="p-1 hover:bg-gray-200 rounded text-gray-500 transition-colors"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-gray-100 flex justify-between items-center bg-gray-50">
              <div className="flex gap-2">
                <label
                  htmlFor="attachment-input"
                  className="p-2 hover:bg-gray-200 rounded-lg text-gray-500 transition-colors cursor-pointer"
                >
                  <Paperclip className="h-5 w-5" />
                </label>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setIsComposeOpen(false);
                    setComposeTo('');
                    setComposeSubject('');
                    setComposeBody('');
                    setSelectedFiles([]);
                    const fileInput = document.getElementById('attachment-input') as HTMLInputElement;
                    if (fileInput) fileInput.value = '';
                  }}
                  className="px-4 py-2 text-gray-600 font-medium hover:bg-gray-200 rounded-lg transition-colors"
                  disabled={sending}
                >
                  Discard
                </button>
                <button
                  onClick={handleSendEmail}
                  disabled={sending}
                  className={cn(
                    "px-6 py-2 text-white font-medium rounded-lg shadow-lg flex items-center gap-2 transition-all",
                    encryptionMethod === 'qkd' || encryptionMethod === 'qs_otp'
                      ? "bg-isro-orange hover:opacity-90 shadow-isro-orange/20"
                      : "bg-blue-600 hover:bg-blue-700 shadow-blue-600/20",
                    sending && "opacity-50 cursor-not-allowed"
                  )}
                >
                  <span>{sending ? 'Sending...' : (encryptionMethod === 'qkd' || encryptionMethod === 'qs_otp' ? 'Send Quantum Secure' : 'Send Normal')}</span>
                  <SendIcon className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* --- Sidebar --- */}
      <div className={cn(
        "flex flex-col bg-[#032848] text-slate-300 transition-all duration-300 ease-in-out",
        sidebarOpen ? "w-64" : "w-20"
      )}>
        <div className={cn("p-4 flex items-center", sidebarOpen ? "justify-between" : "justify-center")}>
          {sidebarOpen && (
            <div className="flex items-center gap-2 font-bold text-white">
              <ShieldCheck className="h-8 w-8 text-isro-orange" />
              <span className="text-xl tracking-tight">QuteMail</span>
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
          >
            <Menu className="h-5 w-5" />
          </button>
        </div>

        <div className="px-3 py-4">
          <button
            onClick={() => {
              if (!isAccountConfigured()) {
                alert('QuTeMail accounts are not yet configured for email services. Only aalan@qutemail.tech is currently operational. Please connect external email accounts (Gmail, Outlook, etc.) to send and receive emails.');
                return;
              }
              setIsComposeOpen(true);
            }}
            className={cn(
              "flex items-center gap-3 w-full bg-isro-orange hover:opacity-90 text-white p-3 rounded-xl transition-all shadow-lg shadow-isro-orange/20 mb-6",
              !sidebarOpen && "justify-center px-0"
            )}>
            <Plus className="h-5 w-5" />
            {sidebarOpen && <span className="font-medium">Compose</span>}
          </button>

          {/* Sync Button */}
          <button
            onClick={handleSync}
            disabled={syncing}
            className={cn(
              "flex items-center gap-3 w-full bg-slate-700 hover:bg-slate-600 text-white p-3 rounded-xl transition-all mb-4",
              !sidebarOpen && "justify-center px-0",
              syncing && "opacity-50 cursor-not-allowed"
            )}
          >
            <RefreshCw className={cn("h-5 w-5", syncing && "animate-spin")} />
            {sidebarOpen && <span className="font-medium">{syncing ? 'Syncing...' : 'Sync Emails'}</span>}
          </button>

          {/* Last Synced Time */}
          {sidebarOpen && lastSynced && (
            <div className="text-xs text-slate-500 px-3 mb-4">
              Last synced: {lastSynced.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
            </div>
          )}

          {/* Back to Dashboard */}
          <button
            onClick={onBack}
            className={cn(
              "flex items-center gap-3 w-full text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 p-3 rounded-lg transition-all mb-6",
              !sidebarOpen && "justify-center px-0"
            )}
          >
            <ArrowLeft className="h-5 w-5" />
            {sidebarOpen && <span>Back to Dashboard</span>}
          </button>

          <nav className="space-y-1">
            <SidebarItem
              icon={Inbox}
              label="Inbox"
              active={selectedFolder === 'inbox'}
              collapsed={!sidebarOpen}
              onClick={() => setSelectedFolder('inbox')}
              count={filteredEmails.filter(e => !e.is_read).length}
            />
            <SidebarItem
              icon={SendIcon}
              label="Sent"
              active={selectedFolder === 'sent'}
              collapsed={!sidebarOpen}
              onClick={() => setSelectedFolder('sent')}
            />
            <SidebarItem
              icon={FileText}
              label="Drafts"
              active={selectedFolder === 'drafts'}
              collapsed={!sidebarOpen}
              onClick={() => setSelectedFolder('drafts')}
            />
            <SidebarItem
              icon={Trash2}
              label="Trash"
              active={selectedFolder === 'trash'}
              collapsed={!sidebarOpen}
              onClick={() => setSelectedFolder('trash')}
            />
          </nav>
        </div>

        <div className="mt-auto p-4 border-t border-slate-800">
          <div className={cn("flex flex-col gap-2", !sidebarOpen && "items-center")}>
            {sidebarOpen && (
              <div className="text-xs text-slate-500">
                <div className="font-medium text-slate-400">{account.email}</div>
                <div className="text-slate-600">{account.provider}</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* --- Email List --- */}
      <div className="flex flex-col w-80 border-r border-gray-200 bg-white">
        <div className="p-4 border-b border-gray-100">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search emails..."
              className="w-full pl-9 pr-4 py-2 bg-gray-100 border-transparent focus:bg-white focus:ring-2 focus:ring-isro-blue focus:border-transparent rounded-lg text-sm transition-all"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-32 text-gray-400">
              <RefreshCw className="h-6 w-6 animate-spin" />
            </div>
          ) : error ? (
            <div className="p-4 text-sm text-red-600">{error}</div>
          ) : account.id === 'qutemail' ? (
            <div className="flex flex-col items-center justify-center p-8 text-center">
              <div className="h-16 w-16 bg-[#032848] rounded-full flex items-center justify-center mb-4">
                <ShieldCheck className="h-8 w-8 text-[#f4711b]" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">QuteMail Account</h3>
              <p className="text-sm text-gray-600 max-w-md mb-4">
                This is your quantum-secure QuteMail account. To send and receive emails, please connect an external email account (Gmail, Outlook, etc.) from the Dashboard.
              </p>
              <button
                onClick={() => window.history.back()}
                className="px-4 py-2 bg-[#f4711b] text-white rounded-lg hover:opacity-90"
              >
                Back to Dashboard
              </button>
            </div>
          ) : filteredEmails.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-gray-400">
              <Inbox className="h-8 w-8 mb-2" />
              <p className="text-sm">No emails yet</p>
              <button
                onClick={handleSync}
                className="mt-2 text-xs text-isro-blue hover:underline"
              >
                Sync now
              </button>
            </div>
          ) : (
            filteredEmails.map(email => (
              <div
                key={email.id}
                onClick={() => handleEmailClick(email)}
                className={cn(
                  "p-4 border-b border-gray-50 cursor-pointer hover:bg-gray-50 transition-colors",
                  selectedEmail?.id === email.id && "bg-isro-blue/10 border-l-4 border-l-isro-blue"
                )}
              >
                <div className="flex justify-between items-start mb-1">
                  <h3 className={cn("font-medium text-sm truncate pr-2", !email.is_read && "font-bold text-gray-900")}>
                    {email.from_name || email.from_email}
                  </h3>
                  <span className="text-xs text-gray-400 whitespace-nowrap">{formatTime(email.sent_at)}</span>
                </div>
                <div className="flex items-center gap-2 mb-1">
                  <h4 className={cn("text-sm truncate text-gray-700", !email.is_read && "font-semibold")}>
                    {email.subject || '(No subject)'}
                  </h4>
                  {email.is_encrypted && (
                    <ShieldCheck className={cn(
                      "h-3 w-3 shrink-0",
                      email.security_level === 'qs_otp' ? "text-purple-600" : "text-isro-blue"
                    )} />
                  )}
                </div>
                <p className="text-xs text-gray-500 line-clamp-2">
                  {email.is_encrypted 
                    ? "🔒 Encrypted message - click to decrypt and view" 
                    : (email.body_text?.substring(0, 100) || "(Click to view)")}
                </p>
              </div>
            ))
          )}
        </div>
      </div>

      {/* --- Reading Pane --- */}
      <div className="flex-1 flex flex-col bg-white min-w-0">
        {selectedEmail ? (
          <>
            {/* Header */}
            <div className="px-8 py-6 border-b border-gray-100 flex justify-between items-start">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-4">
                  <h1 className="text-2xl font-bold text-gray-900 truncate">{selectedEmail.subject || '(No subject)'}</h1>
                  {selectedEmail.is_encrypted && (
                    <span className={cn(
                      "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border",
                      selectedEmail.security_level === 'qs_otp' 
                        ? "bg-purple-50 text-purple-700 border-purple-200"
                        : selectedEmail.security_level === 'aes'
                        ? "bg-blue-50 text-blue-700 border-blue-200"
                        : "bg-emerald-50 text-emerald-700 border-emerald-200"
                    )}>
                      <ShieldCheck className="h-3 w-3" />
                      {selectedEmail.security_level === 'qs_otp' 
                        ? 'Quantum OTP'
                        : selectedEmail.security_level === 'aes'
                        ? 'AES Encrypted'
                        : 'QKD Encrypted'}
                    </span>
                  )}
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-bold">
                      {(selectedEmail.from_name || selectedEmail.from_email)[0]?.toUpperCase() || '?'}
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">{selectedEmail.from_name || selectedEmail.from_email}</p>
                      <p className="text-sm text-gray-500">
                        to {(() => {
                          const emails = selectedEmail.to_emails;
                          if (!emails) return 'Unknown';
                          if (Array.isArray(emails)) return emails.join(', ');
                          try {
                            return typeof emails === 'string' ? JSON.parse(emails).join(', ') : 'Unknown';
                          } catch {
                            return emails;
                          }
                        })()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-gray-400">
                    <span className="text-sm mr-2">{formatTime(selectedEmail.sent_at)}</span>
                    <button className="p-2 hover:bg-gray-100 rounded-full transition-colors">
                      <Star className={cn("h-5 w-5", selectedEmail.is_starred && "fill-yellow-400 text-yellow-400")} />
                    </button>
                    <button className="p-2 hover:bg-gray-100 rounded-full transition-colors">
                      <Reply className="h-5 w-5" />
                    </button>
                    <button className="p-2 hover:bg-gray-100 rounded-full transition-colors">
                      <MoreVertical className="h-5 w-5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-8">
              <div className="prose max-w-none text-gray-800 whitespace-pre-wrap font-normal leading-relaxed">
                {selectedEmail.is_encrypted ? (
                  <EncryptedText 
                    text={selectedEmail.body_text}
                    encryptedClassName="text-neutral-500"
                    revealedClassName="dark:text-white text-black"
                    revealDelayMs={50}
                  />
                ) : (
                  selectedEmail.body_text
                )}
              </div>

              {/* Attachments */}
              {selectedEmail.attachments && selectedEmail.attachments.length > 0 && (
                <div className="mt-8 p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <h4 className="text-sm font-semibold text-gray-900 mb-3">Attachments ({selectedEmail.attachments.length})</h4>
                  <div className="space-y-2">
                    {selectedEmail.attachments.map((attachment, index) => (
                      <div
                        key={`${attachment.filename}-${index}`}
                        className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200 hover:border-isro-blue transition-colors"
                      >
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <Paperclip className="h-5 w-5 text-gray-500 shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 truncate">{attachment.filename}</p>
                            <div className="flex items-center gap-2 mt-1">
                              <p className="text-xs text-gray-500">
                                {(attachment.size / 1024).toFixed(1)} KB
                              </p>
                              {attachment.is_encrypted && (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-isro-blue/10 text-isro-blue">
                                  <ShieldCheck className="h-3 w-3" />
                                  Encrypted
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <button
                          onClick={() => {
                            try {
                              // Attachment data is already embedded as base64
                              if (!attachment.data) {
                                alert('Attachment data not available');
                                return;
                              }
                              
                              // Convert base64 to blob and download
                              const byteCharacters = atob(attachment.data);
                              const byteNumbers = new Array(byteCharacters.length);
                              for (let i = 0; i < byteCharacters.length; i++) {
                                byteNumbers[i] = byteCharacters.charCodeAt(i);
                              }
                              const byteArray = new Uint8Array(byteNumbers);
                              const blob = new Blob([byteArray], { type: attachment.content_type });
                              
                              // Create download link
                              const url = window.URL.createObjectURL(blob);
                              const a = document.createElement('a');
                              a.href = url;
                              a.download = attachment.filename;
                              document.body.appendChild(a);
                              a.click();
                              window.URL.revokeObjectURL(url);
                              document.body.removeChild(a);
                            } catch (err: any) {
                              console.error('Download error:', err);
                              alert(err.message || 'Failed to download attachment');
                            }
                          }}
                          className="p-2 hover:bg-gray-100 rounded-lg text-gray-600 transition-colors"
                          title="Download attachment"
                        >
                          <Download className="h-5 w-5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedEmail.is_encrypted && (
                <div className={cn(
                  "mt-12 p-4 rounded-lg border flex items-start gap-3",
                  selectedEmail.security_level === 'qs_otp'
                    ? "bg-purple-50 border-purple-200"
                    : selectedEmail.security_level === 'aes'
                    ? "bg-blue-50 border-blue-200"
                    : "bg-emerald-50 border-emerald-200"
                )}>
                  <ShieldCheck className={cn(
                    "h-5 w-5 mt-0.5",
                    selectedEmail.security_level === 'qs_otp'
                      ? "text-purple-600"
                      : selectedEmail.security_level === 'aes'
                      ? "text-blue-600"
                      : "text-emerald-600"
                  )} />
                  <div>
                    <h4 className="text-sm font-semibold text-slate-900">
                      {selectedEmail.security_level === 'qs_otp'
                        ? 'Quantum One-Time Pad Encryption'
                        : selectedEmail.security_level === 'aes'
                        ? 'AES-256 Encryption'
                        : 'QKD + AES Encryption'}
                    </h4>
                    <p className="text-xs text-slate-600 mt-1">
                      {selectedEmail.security_level === 'qs_otp'
                        ? 'This message was secured using QKD-derived keys with bitwise XOR (true one-time pad). Mathematically unbreakable when properly implemented.'
                        : selectedEmail.security_level === 'aes'
                        ? 'This message was secured using industry-standard AES-256-GCM encryption with authenticated encryption.'
                        : 'This message was secured using quantum key distribution (BB84 protocol) combined with AES-256 encryption.'}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Reply Box */}
            <div className="p-6 border-t border-gray-100 bg-gray-50">
              <div 
                onClick={() => {
                  if (!isAccountConfigured()) {
                    alert('QuTeMail accounts are not yet configured for email services. Only aalan@qutemail.tech is currently operational. Please connect external email accounts (Gmail, Outlook, etc.) to send and receive emails.');
                    return;
                  }
                  setIsComposeOpen(true);
                }}
                className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm cursor-pointer hover:border-isro-blue transition-colors"
              >
                <p className="text-gray-400 text-sm">Click here to reply...</p>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
            <div className="h-16 w-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
              <Inbox className="h-8 w-8 text-gray-300" />
            </div>
            <p>Select an email to read</p>
          </div>
        )}
      </div>
    </div>
  );
}

function SidebarItem({ icon: Icon, label, active, collapsed, onClick, count }: any) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-3 w-full p-3 rounded-lg transition-all group relative",
        active
          ? "bg-slate-800 text-isro-orange font-medium"
          : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200",
        collapsed && "justify-center"
      )}
    >
      <Icon className={cn("h-5 w-5 transition-colors", active ? "text-isro-orange" : "group-hover:text-slate-200")} />
      {!collapsed && (
        <>
          <span className="flex-1 text-left">{label}</span>
          {count !== undefined && count > 0 && (
            <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">
              {count}
            </span>
          )}
        </>
      )}

      {collapsed && (
        <div className="absolute left-full ml-2 px-2 py-1 bg-slate-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50">
          {label}
        </div>
      )}
    </button>
  );
}
