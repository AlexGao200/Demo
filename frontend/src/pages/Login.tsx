import React, { useState, useContext, FormEvent, ChangeEvent } from 'react';
import { ThemeContext } from '../context/ThemeContext';
import { Link } from 'react-router-dom';
import { ThemeContextType } from '../types';
import AppHeader from '../components/AppHeader';
import { useHandleLogin } from '../hooks/useHandleLogin';

type LoginProps = object

const Login: React.FC<LoginProps> = () => {
  const { theme } = useContext(ThemeContext) as ThemeContextType;
  const [usernameOrEmail, setUsernameOrEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const { handleLogin, isLoading, error: errorMessage } = useHandleLogin();

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    await handleLogin(usernameOrEmail, password);
  };

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
    loginBox: {
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
    rememberMeForgotPassword: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: '20px',
      fontSize: '14px',
    },
    rememberMe: {
      display: 'flex',
      alignItems: 'center',
    },
    rememberMeLabel: {
      marginLeft: '5px',
      minWidth: '100%',
    },
    forgotPassword: {
      color: theme === 'light' ? '#800000' : '#A9A9A9',
      textDecoration: 'none',
    },
    loginButton: {
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
    registerLinkContainer: {
      marginTop: '20px',
      fontSize: '14px',
    },
    registerLink: {
      color: theme === 'light' ? '#800000' : '#A9A9A9',
      textDecoration: 'none',
      fontWeight: 500,
    },
    error: {
      color: theme === 'light' ? '#800000' : '#FFFFFF',
      marginBottom: '15px',
      fontSize: '14px',
    },
  };

  return (
    <div style={styles.container}>
      <AppHeader showLogin={false} showBackToHome={false}/>
      <div style={styles.loginBox}>
        <h2 style={styles.header}>Login</h2>
        {errorMessage && <p style={styles.error}>{errorMessage}</p>}
        <form onSubmit={onSubmit}>
          <div style={styles.inputGroup}>
            <label style={styles.label}>Username or email:</label>
            <input
              type="text"
              value={usernameOrEmail}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setUsernameOrEmail(e.target.value)}
              required
              style={styles.input}
            />
          </div>
          <div style={styles.inputGroup}>
            <label style={styles.label}>Password:</label>
            <input
              type="password"
              value={password}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
              required
              style={styles.input}
            />
          </div>
          <div style={styles.rememberMeForgotPassword}>
            <div style={styles.rememberMe}>
              <input type="checkbox" id="remember-me" />
              <label htmlFor="remember-me" style={styles.rememberMeLabel}>Remember Me</label>
            </div>
            <Link to="/forgot-password" style={styles.forgotPassword}>Forgot Password?</Link>
          </div>
          <button type="submit" style={styles.loginButton} disabled={isLoading}>
            {isLoading ? 'Logging in...' : 'Login'}
          </button>
        </form>
        <div style={styles.registerLinkContainer}>
          <Link to="/register" style={styles.registerLink}>Register</Link>
        </div>
      </div>
    </div>
  );
};

export default Login;
