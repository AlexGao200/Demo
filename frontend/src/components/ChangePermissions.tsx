import React, { useState, useContext, useEffect, FormEvent } from 'react';
import axiosInstance from '../axiosInstance';
import { UserContext } from '../context/UserContext';
import { ThemeContext } from '../context/ThemeContext';
import { useParams } from 'react-router-dom';
import { UserContextType, ThemeContextType } from '../types';
import { handleApiError, ApiError } from '../utils/errorHandling';

const ChangePermissions: React.FC = () => {
  const { user } = useContext(UserContext) as UserContextType;
  const { theme } = useContext(ThemeContext) as ThemeContextType;
  const { organizationId } = useParams<{ organizationId: string }>();

  const [username, setUsername] = useState<string>('');
  const [newPermission, setNewPermission] = useState<'viewer' | 'editor'>('viewer');
  const [message, setMessage] = useState<string>('');
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    console.log('User context:', user);
    console.log('Organization ID from URL:', organizationId);
  }, [user, organizationId]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    console.log('Form submission values:', { username, newPermission });

    if (!username || !newPermission || !organizationId) {
      setError({ message: 'All fields are required.' });
      return;
    }

    try {
      const response = await axiosInstance.post('/organization/change_permissions', {
        organization_id: organizationId,
        username: username,
        new_permission: newPermission,
      });

      if (response.status === 200) {
        setMessage(response.data.message);
        setError(null);
        setUsername('');
        setNewPermission('viewer');
      } else {
        setError({ message: 'Failed to change permissions.' });
      }
    } catch (err: unknown) {
      const apiError = handleApiError(err);
      setError(apiError);
      setMessage('');
    }
  };

  // Theme-specific styles with z-index adjustment
  const themeStyles = {
    container: {
      padding: '20px',
      maxWidth: '600px',
      margin: '0 auto',
      backgroundColor: theme === 'dark' ? '#1A1A1A' : '#F5F5F5',
      color: theme === 'dark' ? '#F5F5F5' : '#333',
      borderRadius: '8px',
      boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
      position: 'relative', // Ensure positioning for z-index
      zIndex: 10, // Higher z-index to ensure it appears above other elements
    },
    header: {
      fontSize: '22px',
      marginBottom: '20px',
    },
    message: {
      color: 'green',
      marginBottom: '15px',
    },
    error: {
      color: 'red',
      marginBottom: '15px',
    },
    form: {
      display: 'flex',
      flexDirection: 'column' as const,
    },
    inputGroup: {
      marginBottom: '15px',
      display: 'flex',
      flexDirection: 'column' as const, // Labels remain on top
      alignItems: 'flex-start', // Left-align the input elements and labels
    },
    label: {
      marginBottom: '5px',
      fontWeight: 'bold',
    },
    input: {
      padding: '10px',
      fontSize: '16px',
      borderRadius: '4px',
      border: theme === 'dark' ? '1px solid #555' : '1px solid #ccc',
      width: '95%',
      backgroundColor: theme === 'dark' ? '#333' : '#fff',
      color: theme === 'dark' ? '#F5F5F5' : '#333',
    },
    button: {
      padding: '10px',
      backgroundColor: 'transparent', // Set button background color to transparent
      color: theme === 'dark' ? '#BB0000' : '#212121', // Use the color for the text instead
      border: theme === 'dark' ? '1px solid #BB0000' : '1px solid #212121', // Optional border to maintain button shape
      borderRadius: '4px',
      cursor: 'pointer',
      fontSize: '16px',
      width: '80%',
      marginTop: '15px',
      margin: '0 auto', // Center the button
      zIndex: 10, // Ensure button is on top
    },
  };

  return (
    <div style={themeStyles.container}>
      <h2 style={themeStyles.header}>Change User Permissions</h2>
      {message && <p style={themeStyles.message}>{message}</p>}
      {error && (
        <div style={themeStyles.error}>
          <p>{error.message}</p>
          {error.details && <p>{error.details}</p>}
        </div>
      )}
      <form onSubmit={handleSubmit} style={themeStyles.form}>
        <div style={themeStyles.inputGroup}>
          <label style={themeStyles.label}>Username:</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={themeStyles.input}
            required
          />
        </div>
        <div style={themeStyles.inputGroup}>
          <label style={themeStyles.label}>New Permission:</label>
          <select
            value={newPermission}
            onChange={(e) => setNewPermission(e.target.value as 'viewer' | 'editor')}
            style={themeStyles.input}
            required
          >
            <option value="viewer">Viewer</option>
            <option value="editor">Editor</option>
          </select>
        </div>
        <button type="submit" style={themeStyles.button}>Change Permissions</button>
      </form>
    </div>
  );
};

export default ChangePermissions;
