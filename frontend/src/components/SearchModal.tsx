import React, { useState } from 'react';

// Define the prop types for SearchModal
interface SearchModalProps {
  onClose: () => void;
  onSearch: (searchTerm: string) => void;
}

const SearchModal: React.FC<SearchModalProps> = ({ onClose, onSearch }) => {
  const [searchTerm, setSearchTerm] = useState<string>('');

  const handleSearch = () => {
    onSearch(searchTerm);
    onClose(); // Close the modal after searching
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        zIndex: 2000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          backgroundColor: 'white',
          padding: '20px',
          borderRadius: '8px',
          boxShadow: '0 2px 10px rgba(0, 0, 0, 0.1)',
          zIndex: 1001,
          minWidth: '400px',
        }}
        onClick={(e) => e.stopPropagation()} // Prevent closing when clicking inside the modal
      >
        <button
          style={{
            position: 'absolute',
            top: '10px',
            right: '-18px',
            background: 'none',
            border: 'none',
            fontSize: '18px',
            cursor: 'pointer',
          }}
          onClick={onClose}
        >
          X
        </button>
        <h2 style={{ marginTop: '0', fontSize: '20px', fontWeight: '500', color: '#000' }}>
          Search Documents
        </h2>
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Enter text to search..."
          style={{
            width: '100%',
            padding: '10px',
            borderRadius: '4px',
            border: '1px solid #ccc',
            fontSize: '14px',
            marginBottom: '20px',
          }}
        />
        <button
          onClick={handleSearch}
          style={{
            padding: '10px',
            backgroundColor: '#ffffff',
            border: '0.1px solid #212121',
            borderRadius: '4px',
            color: '#181818',
            fontSize: '16px',
            cursor: 'pointer',
            display: 'block',
            margin: '10px auto',
          }}
        >
          Search
        </button>
      </div>
    </div>
  );
};

export default SearchModal;
