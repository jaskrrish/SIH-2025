import React, { useState } from 'react';
import { EncryptedText } from "@/components/ui/encrypted-text";
import {
  Inbox,
  Send,
  FileText,
  Trash2,
  ShieldCheck,
  Plus,
  Search,
  Star,
  Menu,
  MoreVertical,
  Reply,
  X,
  Paperclip,
  Lock
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import AccessibilityTools from './components/AccessibilityTools';

// Utility for tailwind class merging
function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// --- Types ---
interface Email {
  id: string;
  sender: string;
  subject: string;
  preview: string;
  time: string;
  read: boolean;
  isQuantum: boolean;
  folder: 'inbox' | 'sent' | 'drafts' | 'trash';
  body: React.ReactNode;
}

// --- Mock Data ---
const MOCK_EMAILS: Email[] = [
  {
    id: '1',
    sender: 'Alice Chen',
    subject: 'Project QuteMail Update',
    preview: 'The quantum key distribution module is ready for testing...',
    time: '10:30 AM',
    read: false,
    isQuantum: true,
    folder: 'inbox',
    body: <EncryptedText text="Hi Bob,

I wanted to give you a quick update on the QuteMail project. The quantum key distribution (QKD) module is finally ready for initial testing. We've successfully integrated the ETSI GS QKD 014 protocol.

Could you review the latest commit?

Best,
Alice"
      encryptedClassName="text-neutral-500"
      revealedClassName="dark:text-white text-black"
      revealDelayMs={5} /> 
  },
  {
    id: '2',
    sender: 'Space Agency HQ',
    subject: 'Mission Critical: Launch Sequence',
    preview: 'Confidential: The launch sequence codes have been updated...',
    time: 'Yesterday',
    read: true,
    isQuantum: true,
    folder: 'inbox',
    body: <EncryptedText text="Commander,

The launch sequence codes for the upcoming mission have been updated. Please find the encrypted attachment.

Ensure you are using a quantum-secure terminal to decrypt this message.

Regards,
HQ"
encryptedClassName = "text-neutral-500"
revealedClassName = "dark:text-white text-black"
revealDelayMs = {5} /> 
  },
  {
    id: '3',
    sender: 'Marketing Team',
    subject: 'Newsletter Draft',
    preview: 'Here is the draft for the monthly newsletter...',
    time: 'Nov 22',
    read: true,
    isQuantum: false,
    folder: 'inbox',
    body: `Hi Team,

Please review the attached draft for our monthly newsletter. We are focusing on the new security features this month.

Thanks,
Sarah`
  }
];

function App() {
  const [selectedFolder, setSelectedFolder] = useState<'inbox' | 'sent' | 'drafts' | 'trash'>('inbox');
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(MOCK_EMAILS[0]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isComposeOpen, setIsComposeOpen] = useState(false);
  const [encryptionMethod, setEncryptionMethod] = useState<'aes' | 'quantum'>('quantum');

  const filteredEmails = MOCK_EMAILS.filter(email => email.folder === selectedFolder);

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
                    className="flex-1 p-2 border-b border-gray-200 focus:border-isro-blue outline-none transition-colors"
                    placeholder="recipient@example.com"
                  />
                </div>
                <div className="flex items-center gap-3">
                  <label className="w-16 text-sm font-medium text-gray-500">Subject</label>
                  <input
                    type="text"
                    className="flex-1 p-2 border-b border-gray-200 focus:border-isro-blue outline-none transition-colors"
                    placeholder="Subject"
                  />
                </div>

                {/* Encryption Selection */}
                <div className="space-y-3">
                  <label className="text-sm font-medium text-gray-500">Encryption Method</label>
                  <div className="grid grid-cols-2 gap-4">
                    <button
                      onClick={() => setEncryptionMethod('aes')}
                      className={cn(
                        "p-4 rounded-xl border text-left transition-all relative overflow-hidden",
                        encryptionMethod === 'aes'
                          ? "bg-blue-50 border-blue-200 ring-1 ring-blue-500"
                          : "bg-white border-gray-200 hover:border-gray-300"
                      )}
                    >
                      <div className="flex items-center gap-3 mb-2">
                        <div className={cn("p-2 rounded-lg", encryptionMethod === 'aes' ? "bg-blue-100 text-blue-600" : "bg-gray-100 text-gray-500")}>
                          <Lock className="h-5 w-5" />
                        </div>
                        <span className={cn("font-semibold", encryptionMethod === 'aes' ? "text-blue-900" : "text-gray-700")}>Standard AES</span>
                      </div>
                      <p className="text-xs text-gray-500">Standard 256-bit encryption. Secure for general purpose.</p>
                      {encryptionMethod === 'aes' && (
                        <div className="absolute top-3 right-3 h-2 w-2 rounded-full bg-blue-500" />
                      )}
                    </button>

                    <button
                      onClick={() => setEncryptionMethod('quantum')}
                      className={cn(
                        "p-4 rounded-xl border text-left transition-all relative overflow-hidden",
                        encryptionMethod === 'quantum'
                          ? "bg-emerald-50 border-emerald-200 ring-1 ring-emerald-500"
                          : "bg-white border-gray-200 hover:border-gray-300"
                      )}
                    >
                      <div className="flex items-center gap-3 mb-2">
                        <div className={cn("p-2 rounded-lg", encryptionMethod === 'quantum' ? "bg-isro-blue/10 text-isro-blue" : "bg-gray-100 text-gray-500")}>
                          <ShieldCheck className="h-5 w-5" />
                        </div>
                        <span className={cn("font-semibold", encryptionMethod === 'quantum' ? "text-isro-blue" : "text-gray-700")}>Quantum Secure</span>
                      </div>
                      <p className="text-xs text-gray-500">Unbreakable QKD encryption. For mission-critical data.</p>
                      {encryptionMethod === 'quantum' && (
                        <div className="absolute top-3 right-3 h-2 w-2 rounded-full bg-emerald-500" />
                      )}
                    </button>
                  </div>
                </div>

                <textarea
                  className="w-full h-64 p-4 bg-gray-50 rounded-lg border-transparent focus:bg-white focus:ring-2 focus:ring-isro-blue focus:border-transparent resize-none outline-none text-gray-700"
                  placeholder="Write your message here..."
                ></textarea>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-gray-100 flex justify-between items-center bg-gray-50">
              <div className="flex gap-2">
                <button className="p-2 hover:bg-gray-200 rounded-lg text-gray-500 transition-colors">
                  <Paperclip className="h-5 w-5" />
                </button>
                <button className="p-2 hover:bg-gray-200 rounded-lg text-gray-500 transition-colors">
                  <Lock className="h-5 w-5" />
                </button>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setIsComposeOpen(false)}
                  className="px-4 py-2 text-gray-600 font-medium hover:bg-gray-200 rounded-lg transition-colors"
                >
                  Discard
                </button>
                <button
                  onClick={() => setIsComposeOpen(false)}
                  className={cn(
                    "px-6 py-2 text-white font-medium rounded-lg shadow-lg flex items-center gap-2 transition-all",
                    encryptionMethod === 'quantum'
                      ? "bg-isro-orange hover:opacity-90 shadow-isro-orange/20"
                      : "bg-blue-600 hover:bg-blue-700 shadow-blue-600/20"
                  )}
                >
                  <span>{encryptionMethod === 'quantum' ? 'Send Quantum Secure' : 'Send with AES'}</span>
                  <Send className="h-4 w-4" />
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
            onClick={() => setIsComposeOpen(true)}
            className={cn(
              "flex items-center gap-3 w-full bg-isro-orange hover:opacity-90 text-white p-3 rounded-xl transition-all shadow-lg shadow-isro-orange/20 mb-6",
              !sidebarOpen && "justify-center px-0"
            )}>
            <Plus className="h-5 w-5" />
            {sidebarOpen && <span className="font-medium">Compose</span>}
          </button>

          <nav className="space-y-1">
            <SidebarItem
              icon={<Inbox />}
              label="Inbox"
              active={selectedFolder === 'inbox'}
              collapsed={!sidebarOpen}
              onClick={() => setSelectedFolder('inbox')}
              count={2}
            />
            <SidebarItem
              icon={<Send />}
              label="Sent"
              active={selectedFolder === 'sent'}
              collapsed={!sidebarOpen}
              onClick={() => setSelectedFolder('sent')}
            />
            <SidebarItem
              icon={<FileText />}
              label="Drafts"
              active={selectedFolder === 'drafts'}
              collapsed={!sidebarOpen}
              onClick={() => setSelectedFolder('drafts')}
            />
            <SidebarItem
              icon={<Trash2 />}
              label="Trash"
              active={selectedFolder === 'trash'}
              collapsed={!sidebarOpen}
              onClick={() => setSelectedFolder('trash')}
            />
          </nav>
        </div>

        <div className="mt-auto p-4 border-t border-slate-800">
          <div className={cn("flex items-center gap-3", !sidebarOpen && "justify-center")}>
            <div className="h-8 w-8 rounded-full bg-indigo-500 flex items-center justify-center text-white font-bold text-xs">
              JM
            </div>
            {sidebarOpen && (
              <div className="flex-1 overflow-hidden">
                <p className="text-sm font-medium text-white truncate">Jayna Mukesh</p>
                <p className="text-xs text-slate-500 truncate">jayna@qute.mail</p>
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
          {filteredEmails.map(email => (
            <div
              key={email.id}
              onClick={() => setSelectedEmail(email)}
              className={cn(
                "p-4 border-b border-gray-50 cursor-pointer hover:bg-gray-50 transition-colors",
                selectedEmail?.id === email.id && "bg-isro-blue/10 border-l-4 border-l-isro-blue"
              )}
            >
              <div className="flex justify-between items-start mb-1">
                <h3 className={cn("font-medium text-sm truncate pr-2", !email.read && "font-bold text-gray-900")}>
                  {email.sender}
                </h3>
                <span className="text-xs text-gray-400 whitespace-nowrap">{email.time}</span>
              </div>
              <div className="flex items-center gap-2 mb-1">
                <h4 className={cn("text-sm truncate text-gray-700", !email.read && "font-semibold")}>
                  {email.subject}
                </h4>
                {email.isQuantum && (
                  <ShieldCheck className="h-3 w-3 text-isro-blue shrink-0" />
                )}
              </div>
              <p className="text-xs text-gray-500 line-clamp-2">
                {email.preview}
              </p>
            </div>
          ))}
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
                  <h1 className="text-2xl font-bold text-gray-900 truncate">{selectedEmail.subject}</h1>
                  {selectedEmail.isQuantum && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-isro-blue/10 text-isro-blue border-isro-blue/20">
                      <ShieldCheck className="h-3 w-3" />
                      Quantum Secured
                    </span>
                  )}
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-bold">
                      {selectedEmail.sender[0]}
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">{selectedEmail.sender}</p>
                      <p className="text-sm text-gray-500">to me</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-gray-400">
                    <span className="text-sm mr-2">{selectedEmail.time}</span>
                    <button className="p-2 hover:bg-gray-100 rounded-full transition-colors">
                      <Star className="h-5 w-5" />
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
                {selectedEmail.body}
              </div>

              {selectedEmail.isQuantum && (
                <div className="mt-12 p-4 bg-slate-50 rounded-lg border border-slate-200 flex items-start gap-3">
                  <ShieldCheck className="h-5 w-5 text-isro-blue mt-0.5" />
                  <div>
                    <h4 className="text-sm font-semibold text-slate-900">Quantum Encrypted Message</h4>
                    <p className="text-xs text-slate-600 mt-1">
                      This message was secured using ETSI GS QKD 014 protocol.
                      Keys were generated via Quantum Key Distribution.
                    </p>
                    <div className="mt-2 flex gap-4 text-xs text-slate-500 font-mono">
                      <span>Key ID: QK-9928-XJ</span>
                      <span>Alg: AES-256-GCM</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Reply Box */}
            <div className="p-6 border-t border-gray-100 bg-gray-50">
              <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm cursor-text">
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

function SidebarItem({ icon, label, active, collapsed, onClick, count }: any) {
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
      {React.cloneElement(icon as React.ReactElement<any>, {
        className: cn("h-5 w-5 transition-colors", active ? "text-isro-orange" : "group-hover:text-slate-200")
      })}      {!collapsed && (
        <>
          <span className="flex-1 text-left">{label}</span>
          {count && (
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

export default App;
