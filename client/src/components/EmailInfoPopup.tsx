import React from 'react';
import { X, Mail, User, Clock, Shield, FileText } from 'lucide-react';

interface EmailInfoPopupProps {
  isOpen: boolean;
  onClose: () => void;
  email: {
    subject?: string;
    envelope?: {
      from?: string;
      to?: string;
      cc?: string;
      bcc?: string;
      reply_to?: string;
      date?: string;
      message_id?: string;
    };
    headers?: Record<string, string | string[]>;
    security_level?: string;
    is_encrypted?: boolean;
  };
}

const EmailInfoPopup: React.FC<EmailInfoPopupProps> = ({ isOpen, onClose, email }) => {
  if (!isOpen) return null;

  const { envelope = {}, headers = {}, security_level, is_encrypted } = email;

  // Security level display
  const getSecurityBadge = () => {
    if (!is_encrypted || security_level === 'regular') {
      return (
        <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-600">
          Not Encrypted
        </span>
      );
    }

    const securityLabels: Record<string, { label: string; color: string }> = {
      aes: { label: 'AES-256-GCM', color: 'bg-blue-100 text-blue-700' },
      qkd: { label: 'QKD + AES', color: 'bg-emerald-100 text-emerald-700' },
      qkd_pqc: { label: 'QKD + PQC', color: 'bg-indigo-100 text-indigo-700' },
      qs_otp: { label: 'Quantum OTP', color: 'bg-purple-100 text-purple-700' },
    };

    const security = securityLabels[security_level || ''] || { label: security_level, color: 'bg-gray-100 text-gray-600' };

    return (
      <span className={`px-2 py-1 text-xs rounded-full ${security.color}`}>
        🔒 {security.label}
      </span>
    );
  };

  // Render header value (handle arrays)
  const renderHeaderValue = (value: string | string[]) => {
    if (Array.isArray(value)) {
      return value.map((v, i) => (
        <div key={i} className="text-sm text-gray-600 mb-1">
          {v}
        </div>
      ));
    }
    return <div className="text-sm text-gray-600">{value}</div>;
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-50 transition-opacity"
        onClick={onClose}
      />

      {/* Popup */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
        <div
          className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[85vh] overflow-hidden pointer-events-auto transform transition-all"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-isro-blue to-blue-600 text-white px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white/20 rounded-lg">
                <FileText className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold">Email Information</h2>
                <p className="text-sm text-blue-100">Headers & Envelope Details</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-lg transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="overflow-y-auto max-h-[calc(85vh-80px)]">
            {/* Envelope Section */}
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center gap-2 mb-4">
                <Mail className="h-5 w-5 text-isro-blue" />
                <h3 className="text-base font-semibold text-gray-900">Envelope Details</h3>
              </div>

              <div className="space-y-3">
                {envelope.from && (
                  <div className="flex">
                    <div className="w-32 text-sm font-medium text-gray-500">From:</div>
                    <div className="flex-1 text-sm text-gray-900 font-mono break-all">
                      {envelope.from}
                    </div>
                  </div>
                )}

                {envelope.to && (
                  <div className="flex">
                    <div className="w-32 text-sm font-medium text-gray-500">To:</div>
                    <div className="flex-1 text-sm text-gray-900 font-mono break-all">
                      {envelope.to}
                    </div>
                  </div>
                )}

                {envelope.cc && (
                  <div className="flex">
                    <div className="w-32 text-sm font-medium text-gray-500">CC:</div>
                    <div className="flex-1 text-sm text-gray-900 font-mono break-all">
                      {envelope.cc}
                    </div>
                  </div>
                )}

                {envelope.bcc && (
                  <div className="flex">
                    <div className="w-32 text-sm font-medium text-gray-500">BCC:</div>
                    <div className="flex-1 text-sm text-gray-900 font-mono break-all">
                      {envelope.bcc}
                    </div>
                  </div>
                )}

                {envelope.reply_to && (
                  <div className="flex">
                    <div className="w-32 text-sm font-medium text-gray-500">Reply-To:</div>
                    <div className="flex-1 text-sm text-gray-900 font-mono break-all">
                      {envelope.reply_to}
                    </div>
                  </div>
                )}

                {envelope.date && (
                  <div className="flex">
                    <div className="w-32 text-sm font-medium text-gray-500">Date:</div>
                    <div className="flex-1 text-sm text-gray-900 font-mono">
                      {envelope.date}
                    </div>
                  </div>
                )}

                {envelope.message_id && (
                  <div className="flex">
                    <div className="w-32 text-sm font-medium text-gray-500">Message-ID:</div>
                    <div className="flex-1 text-sm text-gray-900 font-mono break-all">
                      {envelope.message_id}
                    </div>
                  </div>
                )}

                {envelope.subject && (
                  <div className="flex">
                    <div className="w-32 text-sm font-medium text-gray-500">Subject:</div>
                    <div className="flex-1 text-sm text-gray-900 font-mono break-all">
                      {envelope.subject}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Security Section */}
            <div className="p-6 border-b border-gray-200 bg-gray-50">
              <div className="flex items-center gap-2 mb-3">
                <Shield className="h-5 w-5 text-isro-blue" />
                <h3 className="text-base font-semibold text-gray-900">Security</h3>
              </div>
              <div className="flex items-center gap-2">
                {getSecurityBadge()}
              </div>
            </div>

            {/* Headers Section */}
            <div className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <FileText className="h-5 w-5 text-isro-blue" />
                <h3 className="text-base font-semibold text-gray-900">All Headers</h3>
              </div>

              <div className="space-y-2 font-mono text-xs">
                {Object.keys(headers).length > 0 ? (
                  Object.entries(headers).map(([key, value]) => (
                    <div
                      key={key}
                      className="flex border-b border-gray-100 pb-2 hover:bg-gray-50 px-2 rounded"
                    >
                      <div className="w-1/3 text-gray-700 font-semibold break-all pr-2">
                        {key}:
                      </div>
                      <div className="w-2/3 text-gray-600 break-all">
                        {renderHeaderValue(value)}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-gray-500 italic">No headers available</div>
                )}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-isro-blue text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default EmailInfoPopup;
