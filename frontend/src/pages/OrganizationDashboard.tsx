import React, { useEffect, useState, useContext } from 'react';
import { useParams, Navigate } from 'react-router-dom';
import axiosInstance from '../axiosInstance';
import { ThemeContext } from '../context/ThemeContext';
import MessageCount from '../components/MessageCount';
import ChangePermissions from '../components/ChangePermissions';
import InviteUser from '../components/AdminInvite';
import UserActionsLog from '../components/UserActionLog';
import PendingRequest from '../components/PendingRequest';  // Import PendingRequest component
import AppHeader from '../components/AppHeader';
import ManageUserSubscription from '../components/OrgUserSubscription';
import '../styles/OrganizationDashboard.css';
import { OrganizationMember, OrganizationDashboardParams, ThemeContextType } from '../types';

const OrganizationDashboard: React.FC = () => {
  const { organizationId } = useParams<OrganizationDashboardParams>();
  const { theme } = useContext(ThemeContext) as ThemeContextType;
  const [organizationName, setOrganizationName] = useState<string>('');
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [showChangePermissions, setShowChangePermissions] = useState<boolean>(false);
  const [showInviteUser, setShowInviteUser] = useState<boolean>(false);
  const [showManageSubscription, setShowManageSubscription] = useState<boolean>(false);

  const toggleChangePermissions = () => setShowChangePermissions(!showChangePermissions);
  const toggleInviteUser = () => setShowInviteUser(!showInviteUser);
  const toggleManageSubscription = () => setShowManageSubscription(!showManageSubscription);

  useEffect(() => {
    const fetchOrganizationDetails = async () => {
      if (!organizationId) return;
      try {
        const response = await axiosInstance.get(`/organization/${organizationId}`);
        const capitalizedOrgName = response.data.name
          .split(' ')
          .map((word: string) => word.charAt(0).toUpperCase() + word.slice(1))
          .join(' ');
        setOrganizationName(capitalizedOrgName);
        setMembers(response.data.members);
      } catch (err) {
        console.error('Failed to fetch organization details:', err);
      }
    };

    fetchOrganizationDetails();
  }, [organizationId]);

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
      width: '38%'
    },
  };

  if (!organizationId) {
    return <Navigate to="/organizations" replace />;
  }

  return (
    <div className={`organization-dashboard ${theme}`}>
      <AppHeader />

      <h2 className="dashboard-title">{organizationName} Dashboard</h2>

      <div className="message-count">
        <MessageCount organizationName={organizationName} />
      </div>

      {/* PendingRequest Component */}
      <div className="pending-requests">
        <PendingRequest organizationId={organizationId} /> {/* Added PendingRequest */}
      </div>

      <div className="user-actions-log">
        <UserActionsLog />
      </div>

      <div className="top-buttons">
        <button onClick={toggleChangePermissions}>Change Permissions</button>
        <button onClick={toggleInviteUser}>Invite User</button>
        <button onClick={toggleManageSubscription}>Manage Subscriptions</button>
      </div>

      {showChangePermissions && (
        <div style={styles.modalOverlay} onClick={toggleChangePermissions}>
          <div style={styles.modalPopup} onClick={(e) => e.stopPropagation()}>
            <ChangePermissions />
          </div>
        </div>
      )}

      {showInviteUser && (
        <div style={styles.modalOverlay} onClick={toggleInviteUser}>
          <div style={styles.modalPopup} onClick={(e) => e.stopPropagation()}>
            <InviteUser organizationId={organizationId} />
          </div>
        </div>
      )}

      {showManageSubscription && (
        <div style={styles.modalOverlay} onClick={toggleManageSubscription}>
          <div style={styles.modalPopup} onClick={(e) => e.stopPropagation()}>
            <ManageUserSubscription orgUuid={organizationId} members={members} />
          </div>
        </div>
      )}
    </div>
  );
};

export default OrganizationDashboard;
