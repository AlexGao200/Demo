import React, { useState, useEffect, useContext } from 'react';
import { useParams } from 'react-router-dom';
import axiosInstance from '../axiosInstance';
import { ThemeContext } from '../context/ThemeContext';
import { ThemeContextType } from '../types';

interface PendingRequest {
  requestId: string;
  userEmail: string;
  organizationName: string;
}

const ApproveRequest: React.FC = () => {
  const { organizationId } = useParams<{ organizationId: string }>(); // Retrieve organizationId from URL
  const [pendingRequests, setPendingRequests] = useState<PendingRequest[]>([]);
  const [message, setMessage] = useState<string>('');
  const [membershipType, setMembershipType] = useState<'paid' | 'free'>('free'); // New state to track membership type
  const { theme } = useContext(ThemeContext) as ThemeContextType; // Access theme from ThemeContext

  useEffect(() => {
    const fetchPendingRequests = async () => {
      if (!organizationId) {
        console.error("organizationId is undefined");
        return;
      }
      try {
        const response = await axiosInstance.get(`/organization/pending-requests/${organizationId}`);
        const pendingRequestsData = response.data.pending_requests.map((req: any) => ({
          requestId: req.request_id,
          userEmail: req.user_email,
          organizationName: req.organization_name || '',
        }));
        setPendingRequests(pendingRequestsData);
      } catch (error) {
        console.error('Error fetching pending requests:', error);
      }
    };
    fetchPendingRequests();
  }, [organizationId]);

  const handleApprove = async (requestId: string) => {
    try {
      const response = await axiosInstance.post('/organization/approve-request', {
        request_id: requestId,
        approve: true,
        membershipType, // Send membershipType to backend
        organization_id: organizationId,  // Pass the organization ID here
      });
      setMessage(response.data.message);
      setPendingRequests(pendingRequests.filter(req => req.requestId !== requestId));
    } catch (error) {
      console.error('Error approving request:', error);
      setMessage('Error approving request');
    }
  };

  const handleDecline = async (requestId: string) => {
    try {
      const response = await axiosInstance.post('/organization/approve-request', {
        request_id: requestId,
        approve: false,
        organization_id: organizationId,  // Pass the organization ID here
      });
      setMessage(response.data.message);
      setPendingRequests(pendingRequests.filter(req => req.requestId !== requestId));
    } catch (error) {
      console.error('Error declining request:', error);
      setMessage('Error declining request');
    }
  };

  // Theme-specific styles
  const themeStyles = {
    container: {
      padding: '20px',
      backgroundColor: theme === 'dark' ? '#1A1A1A' : '#F5F5F5',
      color: theme === 'dark' ? '#F5F5F5' : '#333',
      borderRadius: '8px',
      boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
      marginBottom: '20px',
    },
    header: {
      fontSize: '24px',
      marginBottom: '20px',
    },
    error: {
      color: 'red',
      marginBottom: '15px',
    },
    tableWrapper: {
      maxHeight: '250px', // Set the height for the table body scrolling
      overflowY: 'auto', // Enable vertical scrolling only for the table body
      border: `1px solid ${theme === 'dark' ? '#555' : '#ccc'}`, // Add a border around the table
    },
    table: {
      width: '100%',
      borderCollapse: 'collapse' as const,
    },
    thead: {
      backgroundColor: theme === 'dark' ? '#333' : '#f2f2f2',
    },
    th: {
      borderBottom: theme === 'dark' ? '1px solid #555' : '1px solid #ccc',
      padding: '8px',
      textAlign: 'left' as const,
      backgroundColor: theme === 'dark' ? '#333' : '#f2f2f2',
    },
    td: {
      borderBottom: theme === 'dark' ? '1px solid #555' : '1px solid #ccc',
      padding: '8px',
      whiteSpace: 'nowrap',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
    },
    button: {
      padding: '10px',
      backgroundColor: theme === 'dark' ? '#333' : '#f2f2f2',
      color: theme === 'dark' ? '#F5F5F5' : '#000',
      borderRadius: '4px',
      border: '1px solid #666',
      cursor: 'pointer',
      margin: '5px',
    },
  };

  return (
    <div style={themeStyles.container}>
      <h3 style={themeStyles.header}>Pending Requests</h3>
      {message && <p style={themeStyles.error}>{message}</p>}
      {pendingRequests.length === 0 ? (
        <p>No pending requests</p>
      ) : (
        <div style={themeStyles.tableWrapper}>
          <table style={themeStyles.table}>
            <thead style={themeStyles.thead}>
              <tr>
                <th style={themeStyles.th}>User Email</th>
                <th style={themeStyles.th}>Organization</th>
                <th style={themeStyles.th}>Membership Type</th>
                <th style={themeStyles.th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {pendingRequests.map(req => (
                <tr key={req.requestId}>
                  <td style={themeStyles.td}>{req.userEmail}</td>
                  <td style={themeStyles.td}>{req.organizationName}</td>
                  <td style={themeStyles.td}>
                    <label>
                      <input
                        type="radio"
                        name={`membershipType-${req.requestId}`}
                        value="free"
                        checked={membershipType === 'free'}
                        onChange={() => setMembershipType('free')}
                      /> Free
                    </label>
                    <label>
                      <input
                        type="radio"
                        name={`membershipType-${req.requestId}`}
                        value="paid"
                        checked={membershipType === 'paid'}
                        onChange={() => setMembershipType('paid')}
                      /> Paid
                    </label>
                  </td>
                  <td style={themeStyles.td}>
                    <button style={themeStyles.button} onClick={() => handleApprove(req.requestId)}>Approve</button>
                    <button style={themeStyles.button} onClick={() => handleDecline(req.requestId)}>Decline</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ApproveRequest;
