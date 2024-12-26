import React from 'react';
import '../../styles/landingpage/ModalCarousel.css';

interface ArticleSection {
  type: 'image' | 'text';
  content: string;
  caption?: string;
  imageStyle?: React.CSSProperties;
}

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  className?: string;
  modalContent?: ArticleSection[];
  title?: string;
}

const ModalCarousel: React.FC<ModalProps> = ({ isOpen, onClose, className, modalContent, title }) => {
  if (!isOpen) return null;

  const baseClassName = className || 'small-carousel';

  const handleContentClick = (e: React.MouseEvent) => {
    e.stopPropagation();
  };

  return (
    <div className={`${baseClassName}-modal-overlay`} onClick={onClose}>
      <div
        className={`${baseClassName}-modal-content`}
        onClick={handleContentClick}
      >
        <h2 className={`${baseClassName}-modal-message`}>{title || "Modal Title"}</h2>
        <div className={`${baseClassName}-modal-body`}>
          <div className="article-layout">
            {modalContent?.map((section, index) => (
              <div key={index} className="article-section">
                {section.type === 'image' ? (
                  <div className="article-image-container">
                    <div className="image-wrapper">
                      <img
                        src={section.content}
                        alt={section.caption || ''}
                        style={section.imageStyle}
                      />
                    </div>
                    {section.caption && (
                      <p className="image-caption">{section.caption}</p>
                    )}
                  </div>
                ) : (
                  <p className="article-text">{section.content}</p>
                )}
              </div>
            ))}
          </div>
        </div>
        <button
          className={`${baseClassName}-close-button`}
          onClick={onClose}
          aria-label="Close modal"
        >
          ✕
        </button>
      </div>
    </div>
  );
};

export default ModalCarousel;
