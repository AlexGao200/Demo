import React, { useState, useEffect, useContext } from 'react';
import { useParams } from 'react-router-dom';
import axiosInstance from '../axiosInstance';
import { UserContext, UserContextType } from '../context/UserContext';
import { ThemeContext, ThemeContextType } from '../context/ThemeContext';
import AdminContractStatus from '../components/OrganizationContract';
import AppHeader from '../components/AppHeader'; // Assuming you have an AppHeader component
import '../styles/OrganizationDashboard.css'; // Reusing the same CSS file for styling

interface AdminDashboardParams {
  organizationId: string;
}

const AdminDashboard: React.FC = () => {
  const { organizationId } = useParams<AdminDashboardParams>();
  const { theme } = useContext(ThemeContext) as ThemeContextType;
  const [organizationName, setOrganizationName] = useState<string>('');



  const styles = {
    modalOverlay: {
      position: 'fixed' as const,
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      zIndex: 2000,
    },
    modalPopup: {
      position: 'fixed' as const,
      top: '50%',
      left: '50%',
      transform: 'translate(-50%, -50%)',
      backgroundColor: 'transparent',
      padding: '20px',
      borderRadius: '8px',
      zIndex: 3000,
    },
  };

  return (
    <div className={`organization-dashboard ${theme}`}>
      <AppHeader />

      <h2 className="dashboard-title"> Admin Dashboard</h2>

      {/* Contract status management */}
      <div className="manage-contract-status">
        <AdminContractStatus orgUuid={organizationId || ''} />
      </div>

      {/* Add additional sections for admin-specific actions here */}
    </div>
  );
};

export default AdminDashboard;
