import React, { useState } from 'react';
import { useUserContext } from '../context/UserContext';
import Modal from '../components/Modal';
import QRCodeModal from '../components/QRCodeModal';
import { DashboardGridItemProps } from '../types';
import { useQRCode } from '../hooks/useQRCode';
import dataTransferIcon from '../assets/images/data-transfer.png';

const DashboardGridItem: React.FC<DashboardGridItemProps & { isDarkMode?: boolean }> = ({ doc, onDocumentClick, onDelete, onDownload, isDarkMode = false }) => {
  const { user } = useUserContext();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMessage, setModalMessage] = useState<string>('');
  const [isQRModalOpen, setIsQRModalOpen] = useState(false);

  const {
    generateQRCode,
    sendQRCodeEmail,
    regenerateAndGetLink,
    isLoading,
    shareLink,
  } = useQRCode({
    onSuccess: () => setIsQRModalOpen(true),
  });

  const organizationName = doc.organization || 'Unknown Organization';
  const fileVisibilityCapitalized = doc.file_visibility
    ? doc.file_visibility.charAt(0).toUpperCase() + doc.file_visibility.slice(1).toLowerCase()
    : 'Unknown';

  const handleDownloadClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    if (user?.subscription_status === 'inactive' && !user?.is_admin) {
      setModalMessage('Please renew your subscription to download this document.');
      setIsModalOpen(true);
      return;
    }
    onDownload(event);
  };

  const handleCreateQRCode = async () => {
    try {
      await generateQRCode([doc.id]);
    } catch (err) {
      console.error('QR code generation failed:', err);
    }
  };

  const handleSendEmail = async (email: string) => {
    try {
      await sendQRCodeEmail(email, shareLink, doc.title);
      setIsQRModalOpen(false);
      setModalMessage('Email sent successfully!');
      setIsModalOpen(true);
    } catch (err) {
      console.error('Email sending failed:', err);
    }
  };

  const handleRegenerateLink = async (documentId: string) => {
    try {
      return await regenerateAndGetLink([documentId]);
    } catch (err) {
      console.error('Failed to regenerate link:', err);
      throw err;
    }
  };

  return (
    <>
      <div className="documentItem" style={{ position: 'relative' }}>
        <button
          onClick={handleCreateQRCode}
          style={{
            position: 'absolute',
            top: '12px',
            right: '12px',
            padding: 0,
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            width: '30px',
            height: '30px',
            zIndex: 1
          }}
          title="Generate QR Code"
        >
          <img
            src={dataTransferIcon}
            alt="Share"
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'contain',
              marginTop: '2px',
              marginLeft: '-8px',
              display: 'block',
              filter: isDarkMode
                ? 'brightness(0) saturate(100%) invert(100%) sepia(0%) saturate(0%) hue-rotate(0deg) brightness(100%) contrast(100%)'
                : 'none',
              opacity: isDarkMode ? '0.87' : '1'
            }}
          />
        </button>

        <p style={{
          margin: '0',
          width: '100%',
          textAlign: 'center',
          padding: '12px 36px',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis'
        }} className="documentTitle">
          {doc.title || 'Untitled Document'}
        </p>

        <div className="documentMeta">
          <p className="organizationName">{organizationName}</p>
          <p className="fileVisibility">{fileVisibilityCapitalized}</p>
        </div>
        <img src={doc.thumbnail_urls[0]} alt={doc.title} className="documentPreview" />
        <div className="buttonContainer">
          <button onClick={() => onDocumentClick(doc)} className="documentButton viewButton">
            View Document
          </button>
          <div className="buttonContainerBottom">
            <button onClick={handleDownloadClick} className="documentButton downloadButton">
              Download
            </button>
            <button onClick={() => onDelete()} className="documentButton deleteButton">
              Delete
            </button>
          </div>
        </div>
      </div>

      <QRCodeModal
        isOpen={isQRModalOpen}
        onClose={() => setIsQRModalOpen(false)}
        shareLink={shareLink}
        onSendEmail={handleSendEmail}
        isLoading={isLoading}
        documentId={doc.id}
        onRegenerateLink={handleRegenerateLink}
      />

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        message={modalMessage}
      />
    </>
  );
};

export default DashboardGridItem;
