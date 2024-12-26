import React, { useState, useEffect } from 'react';
import axiosInstance from '../axiosInstance';

interface Organization {
  name: string;  // Updated to represent the organization_name field
}

interface GuestFilterProps {
  selectedIndices: string[];  // This will now store the selected organization names
  handleIndexChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  setShowFilterOptions: (show: boolean) => void;
}

const GuestFilter: React.FC<GuestFilterProps> = ({ selectedIndices, handleIndexChange, setShowFilterOptions }) => {
  const [organizations, setOrganizations] = useState<Organization[]>([]);  // Stores the list of organizations

  // Fetch the list of organizations with public documents on mount
  useEffect(() => {
    const fetchOrganizationsWithPublicUploads = async () => {
      try {
        const response = await axiosInstance.get('/get_public_organizations');
        const publicOrganizations = response.data.organizations;
        setOrganizations(publicOrganizations.map((org: any) => ({
          name: org.organization_name,  // No need for index, we're filtering by organization_name
        })));
      } catch (error) {
        console.error('Error fetching organizations with public uploads:', error);
      }
    };

    fetchOrganizationsWithPublicUploads();
  }, []);

  const onOrganizationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleIndexChange(e);  // Pass the change event to the parent for handling
  };

  const currentTheme = localStorage.getItem('theme') || 'light';

  const filterStyles: { [key: string]: React.CSSProperties } = {
    container: {
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      zIndex: 2000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    },
    popup: {
      position: 'relative',
      backgroundColor: currentTheme === 'dark' ? '#444444' : '#fff',
      color: currentTheme === 'dark' ? '#f5f5f5' : '#000',
      padding: '20px',
      borderRadius: '8px',
      boxShadow: '0 2px 10px rgba(0, 0, 0, 0.1)',
      zIndex: 1001,
      minWidth: '300px',
      maxWidth: '80%',
      maxHeight: '90%',
      overflowY: 'auto',
    },
    closeButton: {
      position: 'absolute',
      top: '10px',
      right: '10px',
      background: 'none',
      border: 'none',
      fontSize: '18px',
      cursor: 'pointer',
      color: currentTheme === 'dark' ? '#f5f5f5' : '#000',
    },
    header: {
      marginTop: '0',
      fontSize: '20px',
      fontWeight: 500,
      textAlign: 'center',
      color: currentTheme === 'dark' ? '#f5f5f5' : '#000',
    },
  };

  return (
    <div
      style={filterStyles.container}
      onClick={() => setShowFilterOptions(false)}
    >
      <div
        style={filterStyles.popup}
        onClick={(e: React.MouseEvent<HTMLDivElement>) => e.stopPropagation()}
      >
        <button
          style={filterStyles.closeButton}
          onClick={() => setShowFilterOptions(false)}
        >
          X
        </button>
        <h3 style={filterStyles.header}>
          Filter Public Documents by Organization
        </h3>

        {organizations.length > 0 ? (
          <div className="organization-list">
            {organizations.map((org) => (
              <label key={org.name} style={{ display: 'block', marginTop: '10px' }}>
                <input
                  type="checkbox"
                  value={org.name}  // Use organization name for filtering
                  checked={selectedIndices.includes(org.name)}
                  onChange={onOrganizationChange}
                />
                {org.name}
              </label>
            ))}
          </div>
        ) : (
          <p>No organizations found with public uploads.</p>
        )}
      </div>
    </div>
  );
};

export default GuestFilter;
