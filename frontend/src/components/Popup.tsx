import React from 'react';
import '../styles/Popup.css';

interface PopupProps {
  content: React.ReactNode;
  onClose: () => void;
}

const Popup: React.FC<PopupProps> = ({ content, onClose }) => {
  return (
    <div className="popup-overlay" onClick={onClose}>
      <div className="popup-content" onClick={(e: React.MouseEvent<HTMLDivElement>) => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose}>&times;</button>
        <div className="popup-body">
          {content}
        </div>
      </div>
    </div>
  );
};

export default Popup;
