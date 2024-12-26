import React, { useEffect, useRef } from 'react';
import '../styles/PDFModal.css';

interface PDFModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

const PDFModal: React.FC<PDFModalProps> = ({ isOpen, onClose, children }) => {
  const modalRef = useRef<HTMLDivElement | null>(null);

  // Close the modal when clicking outside of it
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
        onClose(); // Close the modal if clicked outside
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    } else {
      document.removeEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="pdf-modal-overlay">
      <div className="pdf-modal-content" ref={modalRef}>
        {children}
      </div>
    </div>
  );
};

export default PDFModal;
