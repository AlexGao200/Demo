import React from 'react';
import { ModalProps } from '../../types/DocumentTypes'; // Import ModalProps from DocumentTypes

const Modal: React.FC<ModalProps> = ({ isOpen, onClose, message, children }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        {/* Display optional message if provided */}
        {message && <p>{message}</p>}
        {children} {/* Render children passed to the modal */}
      </div>
      <style jsx>{`
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background-color: rgba(0, 0, 0, 0.5);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 1000;
        }

        .modal-container {
          background-color: white;
          padding: 20px;
          border-radius: 8px;
          max-width: 400px;
          width: 100%;
          max-height: 80vh;
          overflow-y: auto;
        }
      `}</style>
    </div>
  );
};

export default Modal;
