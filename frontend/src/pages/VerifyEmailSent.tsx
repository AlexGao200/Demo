import React from 'react'
import { useLocation } from 'react-router-dom';

interface Styles {
  container: React.CSSProperties;
  messageBox: React.CSSProperties;
  header: React.CSSProperties;
  message: React.CSSProperties;
}

const styles: Styles = {
  container: {
    textAlign: 'center',
    padding: '20px',
    backgroundColor: '#F5F5F5',
    color: '#333333',
    minHeight: '100vh',
    fontFamily: "'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif",
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
  },
  messageBox: {
    width: '100%',
    maxWidth: '400px',
    padding: '30px',
    backgroundColor: '#FFFFFF',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
  },
  header: {
    fontSize: '24px',
    fontWeight: 600,
    color: '#1A1A1A',
    marginBottom: '20px',
    letterSpacing: '-0.5px',
  },
  message: {
    fontSize: '16px',
    color: '#333333',
    marginBottom: '10px',
  },
};

const VerifyEmailSent: React.FC = () => {
  const location = useLocation();
  const orgNameToShowUser = location.state?.orgNameToShowUser;

  return (
    <div style={styles.container}>
      <div style={styles.messageBox}>
        <h2 style={styles.header}>Verification Email Sent</h2>
        <p style={styles.message}>Please check your email to verify your account.</p>
        {orgNameToShowUser && (
          <p style={styles.message}>
            You have been registered with the organization: <strong>{orgNameToShowUser}</strong>
          </p>
        )}
      </div>
    </div>
  );
};

export default VerifyEmailSent;
