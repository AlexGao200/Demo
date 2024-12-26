import React, { useState, useEffect } from 'react';
import { useUserContext } from '../context/UserContext';
import { Organization } from '../types';


interface DefaultOrgProps {
  organizations: Organization[];
  currentOrgId: string | null;
}

const DefaultOrg: React.FC<DefaultOrgProps> = ({ organizations, currentOrgId }) => {
  const { setSelectedOrganization } = useUserContext();
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(currentOrgId);

  useEffect(() => {
    setSelectedOrgId(currentOrgId);
  }, [currentOrgId]);

  const handleOrgChange = async (event: React.ChangeEvent<HTMLSelectElement>) => {
    const newOrgId = event.target.value;
    setSelectedOrgId(newOrgId);

    try {
      console.log(`Changing organization to: ${newOrgId}`);
      await setSelectedOrganization(newOrgId);
      console.log('Organization changed successfully');
    } catch (error) {
      console.error('Error changing organization:', error);
      // Optionally, you can add user-friendly error handling here
      // e.g., display an error message to the user
    }
  };

  return (
    <div>
      <label htmlFor="default-org-select">Select Default Organization:</label>
      <select
        id="default-org-select"
        value={selectedOrgId || ''}
        onChange={handleOrgChange}
      >
        <option value="" disabled>Select an organization</option>
        {organizations.map((org) => (
          <option key={org.id} value={org.id}>
            {org.name}
          </option>
        ))}
      </select>
    </div>
  );
};

export default DefaultOrg;
