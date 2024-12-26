import React, { useState, FormEvent, useContext } from 'react';
import { useParams } from 'react-router-dom'; // Import useParams to extract URL params
import axiosInstance from '../axiosInstance';
import { ThemeContext } from '../context/ThemeContext';
import GenerateRegistrationCode from './GenerateRegistrationCode';
import ErrorBoundary from './ErrorBoundary';
import { handleApiError, ApiError } from '../utils/errorHandling';
import { ThemeContextType } from '../types';

const InviteUser: React.FC = () => {
  // Get the organizationId from the URL parameters
  const { organizationId } = useParams<{ organizationId: string }>();
  const [email, setEmail] = useState<string>('');
  const [message, setMessage] = useState<string>('');
  const [error, setError] = useState<ApiError | null>(null);
  const { theme } = useContext(ThemeContext) as ThemeContextType;

  const handleInvite = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!organizationId) {
      setError({ message: 'Organization ID is missing from URL.' });
      return;
    }

    try {
      const response = await axiosInstance.post('/organization/invite', {
        email,
        organization_id: organizationId, // Send the organization_id from the URL to the backend
      });

      if (response && response.data) {
        setMessage(response.data.message);
      } else {
        throw new Error('Unexpected response format');
      }
    } catch (err: unknown) {
      const apiError = handleApiError(err);
      setError(apiError);
      setMessage(apiError.message);
    }
  };

  // Theme-specific styles
  const themeStyles = {
    container: {
      padding: '20px',
      backgroundColor: theme === 'dark' ? '#1A1A1A' : '#F5F5F5',
      color: theme === 'dark' ? '#F5F5F5' : '#333',
      borderRadius: '8px',
      maxWidth: '400px',
      margin: '0 auto',
    },
    header: {
      fontSize: '22px',
      marginBottom: '20px',
      width: '100%',
      textAlign: 'left' as const,
    },
    form: {
      display: 'flex',
      flexDirection: 'column' as const,
    },
    input: {
      padding: '10px',
      marginBottom: '10px',
      fontSize: '16px',
      borderRadius: '4px',
      border: theme === 'dark' ? '1px solid #555' : '1px solid #ccc',
      backgroundColor: theme === 'dark' ? '#333' : '#fff',
      color: theme === 'dark' ? '#F5F5F5' : '#333',
    },
    button: {
      padding: '10px',
      backgroundColor: 'transparent',
      color: theme === 'dark' ? '#BB0000' : '#212121',
      border: theme === 'dark' ? '1px solid #BB0000' : '1px solid #212121',
      borderRadius: '4px',
      cursor: 'pointer',
      fontSize: '16px',
      width: '80%',
      marginTop: '15px',
      margin: '0 auto',
    },
    message: {
      marginTop: '10px',
      color: theme === 'dark' ? '#F5F5F5' : '#333',
    },
    error: {
      marginTop: '10px',
      color: theme === 'dark' ? '#FF6B6B' : '#D32F2F',
    },
  };

  const ErrorFallback: React.FC<{ error: Error | ApiError }> = ({ error }) => (
    <div style={themeStyles.container}>
      <h3 style={themeStyles.header}>Oops! Something went wrong.</h3>
      <p>We're sorry for the inconvenience. Please try again or contact support if the problem persists.</p>
      <p style={themeStyles.error}>{error.message}</p>
      {'details' in error && error.details && (
        <details style={{ whiteSpace: 'pre-wrap', marginTop: '20px' }}>
          <summary>Error Details</summary>
          {error.details}
        </details>
      )}
    </div>
  );

  const componentContent = (
    <div style={themeStyles.container}>
      <h3 style={themeStyles.header}>Invite User to Organization</h3>
      <form onSubmit={handleInvite} style={themeStyles.form}>
        <input
          type="email"
          placeholder="User's Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          style={themeStyles.input}
        />
        <button type="submit" style={themeStyles.button}>Send Invitation</button>
      </form>
      {message && <p style={error ? themeStyles.error : themeStyles.message}>{message}</p>}

      <h3 style={themeStyles.header}>Generate Registration Code</h3>

      <div style={{ width: '100%' }}>
        <GenerateRegistrationCode organizationId={organizationId || ''} />
      </div>
    </div>
  );

  return (
    <ErrorBoundary fallback={<ErrorFallback error={new Error('An unexpected error occurred')} />}>
      {componentContent}
    </ErrorBoundary>
  );
};

export default InviteUser;
