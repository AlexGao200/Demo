import React, { useEffect, useState, useContext } from 'react';
import axiosInstance from '../axiosInstance';
import { useNavigate } from 'react-router-dom';
import { ThemeContext } from '../context/ThemeContext';
import '../styles/PreDashboard.css';
import { Organization, ThemeContextType } from '../types';
import { ApiError, handleApiError } from '../utils/errorHandling';

const PreDashboard: React.FC = () => {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [error, setError] = useState<ApiError | null>(null);
  const navigate = useNavigate();
  const { theme } = useContext(ThemeContext) as ThemeContextType;

  useEffect(() => {
    const fetchOrganizations = async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        setError({ message: 'Token is missing. Please log in again.' });
        navigate('/login');
        return;
      }

      try {
        const decodedToken = JSON.parse(atob(token.split('.')[1]));
        const userIdFromToken = decodedToken.user_id;
        console.log('Decoded user_id from token:', userIdFromToken);

        const storedUserId = localStorage.getItem('user_id');
        if (storedUserId !== userIdFromToken) {
          localStorage.setItem('user_id', userIdFromToken);
        }

        const response = await axiosInstance.get(`/user/${userIdFromToken}/organizations`);
        setOrganizations(response.data.organizations);
      } catch (error) {
        const apiError = handleApiError(error);
        setError(apiError);
        console.error('Error fetching organizations:', apiError);
      }
    };

    fetchOrganizations();
  }, [navigate]);

  const handleOrganizationClick = async (orgId: string) => {
    try {
      const response = await axiosInstance.post('/organization/check_admin_access', {
        organization_id: orgId,
      });

      if (response.data.message === 'Access granted') {
        navigate(response.data.dashboard_url);
      } else {
        setError({ message: 'Access denied', details: response.data.message });
      }
    } catch (error) {
      const apiError = handleApiError(error);
      setError(apiError);
      console.error('Error checking organization access:', apiError);
    }
  };

  return (
    <div className={`pre-dashboard-container ${theme}`}>
      <h1 className="pre-dashboard-title">Select Your Organization</h1>
      {error && (
        <div className="pre-dashboard-error">
          <p>{error.message}</p>
          {error.details && <p>{error.details}</p>}
        </div>
      )}
      <ul className="pre-dashboard-list">
        {organizations.map((org) => (
          <li
            key={org.id}
            onClick={() => handleOrganizationClick(org.id)}
            className="pre-dashboard-item"
          >
            {org.name}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default PreDashboard;
