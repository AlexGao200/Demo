import React, { useState, useEffect, useContext } from 'react';
import axiosInstance from '../axiosInstance';
import { ThemeContext } from '../context/ThemeContext';
import { ThemeContextType } from '../types';

// Define the interface for user action
interface UserAction {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  action_type: string;
  document_title?: string; // Document title might be optional
  document_url?: string; // Document URL might be optional
  index_name?: string; // Optional field for index name
  timestamp: string;
}

const UserActionsLog: React.FC = () => {
  const [actions, setActions] = useState<UserAction[]>([]);
  const [error, setError] = useState<string>('');
  const { theme } = useContext(ThemeContext) as ThemeContextType; // Access theme from ThemeContext

  useEffect(() => {
    const fetchActions = async () => {
      try {
        const response = await axiosInstance.get('/organization/user_actions');
        if (response.data.actions) { // Adjust to match the backend response format
          setActions(response.data.actions);
        } else if (response.data.message) {
          setError(response.data.message);
        } else {
          setError('Unexpected response format.');
        }
      } catch (err) {
        setError('Failed to fetch user actions.');
      }
    };

    fetchActions();
  }, []);

  // Utility function to shorten URLs
  const shortenUrl = (url: string, maxLength: number = 30) => {
    if (url.length <= maxLength) return url;
    return `${url.slice(0, maxLength)}...`;
  };

  // Utility function to convert index name to human-readable database names
  const getDatabaseLabel = (index_name: string | undefined) => {
    if (!index_name) return 'N/A';
    if (index_name.startsWith('org')) {
      return 'Private Organizational';
    } else {
      return 'Public Organizational';
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
    urlCell: {
      maxWidth: '150px',
      whiteSpace: 'nowrap',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      borderBottom: theme === 'dark' ? '1px solid #555' : '1px solid #ccc', // Ensuring border is applied here
    },
    link: {
      color: theme === 'dark' ? '#F5F5F5' : '#0066cc',
      textDecoration: 'none', // Remove the underline from the URL link
    },
  };

  return (
    <div style={themeStyles.container}>
      <h2 style={themeStyles.header}>User Actions Log</h2>
      {error && <p style={themeStyles.error}>{error}</p>}
      {actions.length > 0 ? (
        <div style={themeStyles.tableWrapper}>
          <table style={themeStyles.table}>
            <thead style={themeStyles.thead}>
              <tr>
                <th style={themeStyles.th}>Username</th>
                <th style={themeStyles.th}>First Name</th>
                <th style={themeStyles.th}>Last Name</th>
                <th style={themeStyles.th}>Action Type</th>
                <th style={themeStyles.th}>Document Title</th>
                <th style={themeStyles.th}>Document URL</th>
                <th style={themeStyles.th}>Database</th>
                <th style={themeStyles.th}>Date</th>
              </tr>
            </thead>
            <tbody>
              {actions.map((action, index) => (
                <tr key={index}>
                  <td style={themeStyles.td}>{action.username}</td>
                  <td style={themeStyles.td}>{action.first_name}</td>
                  <td style={themeStyles.td}>{action.last_name}</td>
                  <td style={themeStyles.td}>{action.action_type}</td>
                  <td style={themeStyles.td}>{action.document_title || 'N/A'}</td>
                  <td style={themeStyles.urlCell}>
                    {action.document_url ? (
                      <a href={action.document_url} target="_blank" rel="noopener noreferrer" style={themeStyles.link}>
                        {shortenUrl(action.document_url)}
                      </a>
                    ) : (
                      'N/A'
                    )}
                  </td>
                  <td style={themeStyles.td}>{getDatabaseLabel(action.index_name)}</td>
                  <td style={themeStyles.td}>{new Date(action.timestamp).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : !error && <p>No user actions available.</p>}
    </div>
  );
};

export default UserActionsLog;
