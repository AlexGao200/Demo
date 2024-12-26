import React, { useEffect, useRef } from 'react';
import '../../styles/Modal.css';

interface FilterModalProps {
  title: string;
  children: React.ReactNode;
  onAbort: () => void;
}

const FilterModal: React.FC<FilterModalProps> = ({ title, children, onAbort }) => {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
        onAbort();
      }
    };

    document.addEventListener('mousedown', handleOutsideClick);

    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, [onAbort]);

  return (
    <div className="modal-overlay">
      <div className="modal-container" ref={modalRef}>
        <div className="modal-content">
          <h2 className="text-xl font-bold mb-4">{title}</h2>
          {children}
        </div>
      </div>
    </div>
  );
};

export default FilterModal;
