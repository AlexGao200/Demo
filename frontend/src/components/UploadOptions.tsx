import React from 'react';
import PersonalUpload from './PersonalUpload';
import OrganizationalUpload from './OrganizationalUpload';
import PublicUpload from './PublicUpload';

// Define the prop types for the UploadOptions component
interface UploadOptionsProps {
  onUploadComplete: (success: boolean) => void; // Only called when an upload completes successfully
  onSelectUpload: (uploadType: string) => void; // Ensure onSelectUpload is passed as a prop
}

const UploadOptions: React.FC<UploadOptionsProps> = ({ onUploadComplete, onSelectUpload }) => {
  // A separate function to close the modal without triggering the success state
  const handleClose = () => {
    onSelectUpload(''); // Reset the upload selection when closing the modal
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
      onClick={handleClose}
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

        <h3 style={{ marginTop: '0', fontSize: '20px', fontWeight: '500', color: '#000', textAlign: 'center' }}>
          Select Upload Option
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <button
            style={{
              width: '100%',
              padding: '10px',
              backgroundColor: '#ffffff',
              border: '0.1px solid #212121',
              borderRadius: '4px',
              color: '#181818',
              fontSize: '16px',
              cursor: 'pointer',
              marginTop: '10px',
            }}
            onClick={() => onSelectUpload('personal')} // Pass 'personal' as the upload type
          >
            Personal Upload
          </button>
          <button
            style={{
              width: '100%',
              padding: '10px',
              backgroundColor: '#ffffff',
              border: '0.1px solid #212121',
              borderRadius: '4px',
              color: '#181818',
              fontSize: '16px',
              cursor: 'pointer',
              marginTop: '10px',
            }}
            onClick={() => onSelectUpload('organizational')} // Pass 'organizational' as the upload type
          >
            Organizational Upload
          </button>
          <button
            style={{
              width: '100%',
              padding: '10px',
              backgroundColor: '#ffffff',
              border: '0.1px solid #212121',
              borderRadius: '4px',
              color: '#181818',
              fontSize: '16px',
              cursor: 'pointer',
              marginTop: '10px',
            }}
            onClick={() => onSelectUpload('public')} // Pass 'public' as the upload type
          >
            Public Upload
          </button>
        </div>
      </div>
    </div>
  );
};

export default UploadOptions;
