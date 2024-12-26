import React, { useState, useEffect, useRef, useContext } from 'react';
import { createPortal } from 'react-dom';
import { ThemeContext } from '../context/ThemeContext';
import { ThemeContextType } from '../types';

interface QRCodeModalProps {
  isOpen: boolean;
  onClose: () => void;
  shareLink: string;
  onSendEmail: (email: string) => Promise<void>;
  isLoading: boolean;
  documentId: string;
  onRegenerateLink: (documentId: string) => Promise<string>;
}

const QRCodeModal: React.FC<QRCodeModalProps> = ({
  isOpen,
  onClose,
  shareLink,
  onSendEmail,
  isLoading,
  documentId,
  onRegenerateLink
}) => {
  const { theme } = useContext(ThemeContext) as ThemeContextType;
  const [email, setEmail] = useState('');
  const [copied, setCopied] = useState(false);
  const [sent, setSent] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleOutsideClick);
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, [onClose]);

  const handleCopy = async () => {
    try {
      // First regenerate a new link
      const newLink = await onRegenerateLink(documentId);
      // Then copy the new link
      await navigator.clipboard.writeText(newLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000); // Reset after 2 seconds
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleSendEmail = async () => {
    try {
      // First regenerate a new link
      const newLink = await onRegenerateLink(documentId);
      // Then send the email with the new link
      await onSendEmail(email);
      setEmail('');
      setSent(true);
      setTimeout(() => setSent(false), 2000); // Reset after 2 seconds
    } catch (err) {
      console.error('Failed to send email:', err);
    }
  };

  const themeStyles = {
    button: {
      padding: '10px',
      backgroundColor: 'transparent',
      color: theme === 'dark' ? '#FFFFFF' : '#212121',
      border: theme === 'dark' ? '1px solid #FFFFFF' : '1px solid #212121',
      borderRadius: '4px',
      cursor: 'pointer',
      fontSize: '16px',
      width: '80%',
      marginTop: '15px',
      margin: '0 auto',
      transition: 'opacity 0.3s ease',
    },
    input: {
      padding: '10px',
      fontSize: '16px',
      borderRadius: '4px',
      border: theme === 'dark' ? '1px solid #555' : '1px solid #ccc',
      backgroundColor: theme === 'dark' ? '#333' : '#fff',
      color: theme === 'dark' ? '#F5F5F5' : '#333',
      width: '100%',
      marginBottom: '10px',
    },
    modalContainer: {
      background: theme === 'dark' ? '#1A1A1A' : '#ffffff',
      color: theme === 'dark' ? '#F5F5F5' : '#333333',
      textAlign: 'center' as const,
      width: '40%',
      maxWidth: '400px'
    }
  };

  if (!isOpen) return null;

  return createPortal(
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-container"
        style={themeStyles.modalContainer}
        ref={modalRef}
        onClick={e => e.stopPropagation()}
      >
        <div className="modal-content">
          <h2 style={{ marginBottom: '20px' }}>Share Document Access</h2>
          <div className="modal-section">
            <p style={{ marginBottom: '10px' }}>Share Link:</p>
            <input
              value={shareLink}
              readOnly
              style={themeStyles.input}
            />
            <button
              onClick={handleCopy}
              style={{
                ...themeStyles.button,
                marginTop: '10px',
                opacity: copied ? 0.6 : 1,
              }}
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <div className="modal-section">
            <p style={{ marginBottom: '10px' }}>Send via Email:</p>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter email address"
              style={themeStyles.input}
            />
            <button
              onClick={handleSendEmail}
              disabled={!email || isLoading}
              style={{
                ...themeStyles.button,
                cursor: (!email || isLoading) ? 'not-allowed' : 'pointer',
                marginBottom: '10px',
                marginTop: '10px',
                opacity: sent ? 0.6 : (!email || isLoading ? 0.5 : 1),
              }}
            >
              {sent ? 'Sent!' : 'Send'}
            </button>
          </div>
          <button
            onClick={onClose}
            style={themeStyles.button}
          >
            Close
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default QRCodeModal;
