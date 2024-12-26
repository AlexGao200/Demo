import React, { useState, useEffect } from 'react';
import { useUserContext } from '../UserContext';
import axiosInstance from '../axiosInstance';

const OrganizationDropdown: React.FC = () => {
  const { user, setSelectedOrganization, selectedOrganization } = useUserContext();
  const [organizations, setOrganizations] = useState<{ id: string, name: string }[]>([]);

  useEffect(() => {
    // Fetch user's organizations on component mount
    const fetchOrganizations = async () => {
      if (user && user.user_id) {
        try {
          const response = await axiosInstance.get(`/user/${user.user_id}/organizations`);
          setOrganizations(response.data.organizations);
        } catch (error) {
          console.error('Error fetching organizations:', error);
        }
      }
    };

    fetchOrganizations();
  }, [user]);

  // Handle organization selection
  const handleSelectOrganization = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedOrgId = event.target.value;
    setSelectedOrganization(selectedOrgId);  // Update context with selected organization
  };

  return (
    <div>
      <label htmlFor="organizationDropdown">Select Organization:</label>
      <select
        id="organizationDropdown"
        value={selectedOrganization || ''}
        onChange={handleSelectOrganization}
      >
        <option value="" disabled>Select an organization</option>
        {organizations.map(org => (
          <option key={org.id} value={org.id}>
            {org.name}
          </option>
        ))}
      </select>
    </div>
  );
};

export default OrganizationDropdown;
