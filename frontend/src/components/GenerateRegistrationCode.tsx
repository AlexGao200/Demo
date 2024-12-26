import React, { useState, FormEvent, useContext } from 'react';
import axiosInstance from '../axiosInstance';
import { ThemeContext } from '../context/ThemeContext';
import { handleApiError, ApiError } from '../utils/errorHandling';
import { ThemeContextType } from '../types';

interface GenerateRegistrationCodeProps {
  organizationId: string;
}

const GenerateRegistrationCode: React.FC<GenerateRegistrationCodeProps> = ({ organizationId }) => {
  const { theme } = useContext(ThemeContext) as ThemeContextType;
  const [membershipType, setMembershipType] = useState<string>('free'); // Set default to 'free'
  const [message, setMessage] = useState<string>('');
  const [registrationLink, setRegistrationLink] = useState<string>('');
  const [error, setError] = useState<ApiError | null>(null);

  const handleGenerateCode = async (e: FormEvent) => {
    e.preventDefault();

    if (!organizationId || !membershipType) {
      setError({ message: 'Organization ID and Membership Type are required.' });
      return;
    }

    try {
      const response = await axiosInstance.post('/organization/generate_registration_code', {
        organization_id: organizationId,
        membership_type: membershipType,
      });

      if (response.status === 201) {
        setMessage('Registration link generated:');
        setRegistrationLink(response.data.registration_link);
        setError(null);
      } else {
        throw new Error('Failed to generate registration link.');
      }
    } catch (err: unknown) {
      const apiError = handleApiError(err);
      setError(apiError);
      setMessage('');
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
      paddingLeft: '-10px',
    },
    form: {
      display: 'flex',
      flexDirection: 'column' as const,
    },
    select: {
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
    registrationLink: {
      marginTop: '10px',
      color: theme === 'dark' ? '#BB0000' : '#212121',
      textDecoration: 'underline',
      wordBreak: 'break-word' as const,
    },
    error: {
      color: 'red',
      marginTop: '10px',
    },
  };

  return (
    <div style={themeStyles.container}>
      <h3 style={themeStyles.header}>Generate Registration Code</h3>
      <form onSubmit={handleGenerateCode} style={themeStyles.form}>
        <select
          value={membershipType}
          onChange={(e) => setMembershipType(e.target.value)}
          style={themeStyles.select}
        >
          <option value="free">Regular Member</option> {/* Changed value to 'free' */}
          <option value="paid">Paid Member</option>
        </select>
        <button type="submit" style={themeStyles.button}>Generate Code</button>
      </form>
      {message && <p style={themeStyles.message}>{message}</p>}
      {registrationLink && (
        <a href={registrationLink} target="_blank" rel="noopener noreferrer" style={themeStyles.registrationLink}>
          {registrationLink}
        </a>
      )}
      {error && <p style={themeStyles.error}>{error.message}</p>}
    </div>
  );
};

export default GenerateRegistrationCode;
