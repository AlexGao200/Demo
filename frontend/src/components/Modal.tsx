import React from 'react';
import '../styles/Modal.css';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  message?: string;
  children?: React.ReactNode;
  isDarkMode?: boolean;
}

const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  message,
  children,
  isDarkMode = false
}) => {
  if (!isOpen) return null;

  const darkModeClass = isDarkMode ? 'dark-mode' : '';

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className={`modal-content ${darkModeClass}`}
        onClick={(e) => e.stopPropagation()}
      >
        {message && (
          <p className={`modal-message ${darkModeClass}`}>{message}</p>
        )}
        {children}
      </div>
    </div>
  );
};

export default Modal;
