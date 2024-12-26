import React, { useState, useContext, FormEvent } from 'react';
import { ThemeContext } from '../context/ThemeContext';
import { ThemeContextType } from '../types';
import AppHeader from '../components/AppHeader';
import axiosInstance from '../axiosInstance';
import { AxiosError } from 'axios';
import { Link } from 'react-router-dom';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { theme } = useContext(ThemeContext) as ThemeContextType;

  const styles: Record<string, React.CSSProperties> = {
    container: {
      textAlign: 'center',
      padding: '20px',
      backgroundColor: theme === 'light' ? '#F5F5F5' : '#1a1a1a',
      color: theme === 'light' ? '#333333' : '#f5f5f5',
      minHeight: '100vh',
      fontFamily: "'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif",
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
    },
    box: {
      width: '100%',
      maxWidth: '400px',
      padding: '65px 30px',
      backgroundColor: theme === 'light' ? '#FFFFFF' : '#333333',
      borderRadius: '8px',
      boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
    },
    header: {
      fontSize: '24px',
      fontWeight: 600,
      color: theme === 'light' ? '#1A1A1A' : '#f5f5f5',
      marginBottom: '40px',
      letterSpacing: '-0.5px',
    },
    inputGroup: {
      marginBottom: '20px',
      textAlign: 'left',
    },
    label: {
      display: 'block',
      color: theme === 'light' ? '#333333' : '#f5f5f5',
      marginBottom: '20px',
      fontSize: '14px',
    },
    input: {
      width: '100%',
      padding: '10px',
      borderRadius: '4px',
      border: `1px solid ${theme === 'light' ? '#CCCCCC' : '#555555'}`,
      fontSize: '16px',
      backgroundColor: theme === 'light' ? '#FFFFFF' : '#444444',
      color: theme === 'light' ? '#333333' : '#f5f5f5',
    },
    button: {
      width: '100%',
      padding: '10px',
      backgroundColor: theme === 'light' ? '#800000' : '#A9A9A9',
      border: 'none',
      borderRadius: '4px',
      color: '#FFFFFF',
      fontSize: '16px',
      cursor: 'pointer',
      fontWeight: 500,
      opacity: isLoading ? 0.7 : 1,
    },
    message: {
      color: '#4CAF50',
      marginBottom: '15px',
      fontSize: '14px',
    },
    error: {
      color: theme === 'light' ? '#800000' : '#FFFFFF',
      marginBottom: '15px',
      fontSize: '14px',
    },
    backToLogin: {
      marginTop: '20px',
      fontSize: '14px',
    },
    backToLoginLink: {
      color: theme === 'light' ? '#800000' : '#A9A9A9',
      textDecoration: 'none',
      fontWeight: 500,
    }
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setMessage('');
    setError('');
    setIsLoading(true);

    try {
      console.log(`Sending forgot password request for email: ${email}`);
      const response = await axiosInstance.post('/auth/forgot-password', { email });
      console.log('Response:', response);
      setMessage(response.data.message);
    } catch (err: unknown) {
      console.error('Error:', err);
      if (err instanceof AxiosError && err.response) {
        console.error('Error response:', err.response);
        setError(err.response.data.message || 'An error occurred. Please try again.');
      } else {
        setError('An error occurred. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <AppHeader showLogin={false} showBackToHome={false} />
      <div style={styles.box}>
        <h2 style={styles.header}>Forgot Password</h2>
        <form onSubmit={handleSubmit}>
          <div style={styles.inputGroup}>
            <label style={styles.label}>Email:</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={styles.input}
            />
          </div>
          {message && <p style={styles.message}>{message}</p>}
          {error && <p style={styles.error}>{error}</p>}
          <button type="submit" style={styles.button} disabled={isLoading}>
            {isLoading ? 'Sending...' : 'Send Reset Link'}
          </button>
        </form>
        <div style={styles.backToLogin}>
          <Link to="/login" style={styles.backToLoginLink}>Back to Login</Link>
        </div>
      </div>
    </div>
  );
};

export default ForgotPassword;
