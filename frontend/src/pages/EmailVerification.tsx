import React, { useEffect, useState, useContext } from 'react';
import { useParams } from 'react-router-dom';
import axiosInstance from '../axiosInstance';
import { ThemeContext } from '../context/ThemeContext';
import { AxiosError } from 'axios';
import { ThemeContextType } from '../types';


interface Styles {
  container: React.CSSProperties;
  messageBox: React.CSSProperties;
  header: React.CSSProperties;
  message: React.CSSProperties;
}

interface ErrorResponse {
  message: string;
}

const EmailVerification: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const [message, setMessage] = useState<string>('');
  const { theme } = useContext(ThemeContext) as ThemeContextType;

  useEffect(() => {
    const verifyEmail = async (): Promise<void> => {
      try {
        const response = await axiosInstance.get<{ message: string }>(`/auth/verify-email/${token}`);
        setMessage(response.data.message);
      } catch (error) {
        const axiosError = error as AxiosError<ErrorResponse>;
        setMessage(axiosError.response?.data?.message || 'Verification failed. Please try again.');
      }
    };

    verifyEmail();
  }, [token]);

  const styles: Styles = {
    container: {
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      background:
        theme === 'light'
          ? 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)'
          : '#1A1A1A',
    },
    messageBox: {
      textAlign: 'center',
      padding: '40px',
      borderRadius: '10px',
      background: theme === 'light' ? '#fff' : '#333333',
      boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1)',
    },
    header: {
      marginBottom: '20px',
      color: theme === 'light' ? '#333' : '#f5f5f5',
    },
    message: {
      color: theme === 'light' ? '#555' : '#cccccc',
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.messageBox}>
        <h1 style={styles.header}>Email Verification</h1>
        <p style={styles.message}>{message}</p>
      </div>
    </div>
  );
};

export default EmailVerification;
