import React, { useState, useContext, useEffect } from 'react';
import axiosInstance from '../axiosInstance';
import { ThemeContext } from '../context/ThemeContext';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { AxiosError } from 'axios';
import { ThemeContextType } from '../types';
import { debounce } from 'lodash';
import AppHeader from '../components/AppHeader';
import { useHandleLogin } from '../hooks/useHandleLogin';

interface RegistrationData {
  email: string;
  first_name: string;
  last_name: string;
  username: string;
  password: string;
  invitation_token?: string;
  organization_registration_code?: string;
}

interface Styles {
  [key: string]: React.CSSProperties;
}

const Register: React.FC = () => {
  const { theme } = useContext(ThemeContext) as ThemeContextType;
  const [step, setStep] = useState<number>(1);
  const [email, setEmail] = useState<string>('');
  const [verificationCode, setVerificationCode] = useState<string>('');
  const [firstName, setFirstName] = useState<string>('');
  const [lastName, setLastName] = useState<string>('');
  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [organizationCode, setOrganizationCode] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [countdown, setCountdown] = useState<number>(0);
  const [usernameAvailable, setUsernameAvailable] = useState<boolean | null>(null);
  const [usernameError, setUsernameError] = useState<string>('');
  const [passwordStrength, setPasswordStrength] = useState<string>('');
  const navigate = useNavigate();
  const location = useLocation();
  const { handleLogin } = useHandleLogin();

  const handleBack = () => {
    setStep(1);
    setVerificationCode('');
    setError('');
    setCountdown(0);
  };

  useEffect(() => {
    const queryParams = new URLSearchParams(location.search);
    const code = queryParams.get('code');
    const verification = queryParams.get('verification');
    const verificationEmail = queryParams.get('email');

    if (code) {
      setOrganizationCode(code);
    }

    // Handle email verification from link
    if (verification === 'success' && verificationEmail) {
      setEmail(verificationEmail);
      setStep(3); // Skip to identity step since email is verified
    } else if (verification === 'failed') {
      const error = queryParams.get('error');
      if (error === 'invalid_token') {
        setError('Invalid verification link. Please try again or use the verification code sent to your email.');
      } else if (error === 'expired_token') {
        setError('Verification link has expired. Please request a new verification code.');
      } else {
        setError('Verification failed. Please try again or contact support.');
      }
    }
  }, [location.search]);

  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  const checkUsernameAvailability = debounce(async (username: string) => {
    if (username.length < 3) {
      setUsernameAvailable(null);
      setUsernameError('Username must be at least 3 characters long');
      return;
    }

    if (username.length > 20) {
      setUsernameAvailable(null);
      setUsernameError('Username must be no more than 20 characters long');
      return;
    }

    if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
      setUsernameAvailable(null);
      setUsernameError('Username can only contain letters, numbers, underscores, and hyphens');
      return;
    }

    try {
      const response = await axiosInstance.get(`/auth/check-username/${username}`);
      setUsernameAvailable(response.data.available);
      setUsernameError(response.data.message);
    } catch (error) {
      if (error instanceof AxiosError && error.response?.data?.message) {
        setUsernameError(error.response.data.message);
      } else {
        setUsernameError('Error checking username availability');
      }
      setUsernameAvailable(null);
    }
  }, 300);

  useEffect(() => {
    if (username) {
      checkUsernameAvailability(username);
    } else {
      setUsernameAvailable(null);
      setUsernameError('');
    }
  }, [username, checkUsernameAvailability]);

  const checkPasswordStrength = (password: string) => {
    const strongRegex = new RegExp("^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*])(?=.{8,})");
    const mediumRegex = new RegExp("^(((?=.*[a-z])(?=.*[A-Z]))|((?=.*[a-z])(?=.*[0-9]))|((?=.*[A-Z])(?=.*[0-9])))(?=.{6,})");
    if (password.length > 0) {
      if (strongRegex.test(password)) {
        setPasswordStrength('strong');
      } else if (mediumRegex.test(password)) {
        setPasswordStrength('medium');
      } else {
        setPasswordStrength('weak');
      }
    }
  };

  useEffect(() => {
    checkPasswordStrength(password);
  }, [password]);

  const handleEmailSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const response = await axiosInstance.post('/auth/initiate-registration', { email });
      if (response.status === 200) {
        setStep(2);
        setCountdown(60);
      }
    } catch (err) {
      if (err instanceof AxiosError && err.response) {
        setError(err.response.data.message || 'An error occurred during registration.');
      } else {
        setError('Network error. Please check your connection and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerificationSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const response = await axiosInstance.post('/auth/verify-email-code', { email, code: verificationCode });
      if (response.status === 200) {
        setStep(3);
      }
    } catch (err) {
      if (err instanceof AxiosError && err.response) {
        setError(err.response.data.message || 'Invalid verification code.');
      } else {
        setError('Network error. Please check your connection and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleIdentitySubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    if (!usernameAvailable) {
      setError(usernameError || 'Username is not available. Please choose a different one.');
      setIsSubmitting(false);
      return;
    }

    setStep(4);
    setIsSubmitting(false);
  };

  const handleFinalSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      setIsSubmitting(false);
      return;
    }

    if (passwordStrength === 'weak') {
      setError('Password is too weak. Please choose a stronger password.');
      setIsSubmitting(false);
      return;
    }

    try {
      const registrationData: RegistrationData = {
        email,
        first_name: firstName,
        last_name: lastName,
        username,
        password,
        organization_registration_code: organizationCode
      };

      const response = await axiosInstance.post('/auth/register', registrationData);

      if (response.status === 201) {
        // Automatically log in after successful registration
        const success = await handleLogin(username, password);
        if (!success) {
          setError('Registration successful but automatic login failed. Please try logging in manually.');
          navigate('/login');
        }
      }
    } catch (err) {
      if (err instanceof AxiosError && err.response) {
        setError(err.response.data.message || 'An error occurred during registration.');
      } else {
        setError('Network error. Please check your connection and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResendVerification = async () => {
    if (countdown > 0) return;

    try {
      await axiosInstance.post('/auth/resend-verification', { email });
      setCountdown(60);
    } catch (error) {
      if (error instanceof AxiosError && error.response) {
        setError(error.response.data.message || 'Failed to resend verification email.');
      } else {
        setError('Failed to resend verification email. Please try again.');
      }
    }
  };

  // Dynamic styles based on the current theme
  const styles: Styles = {
    container: {
      textAlign: 'center',
      padding: '20px',
      backgroundColor: theme === 'light' ? '#F5F5F5' : '#1a1a1a',
      color: theme === 'light' ? '#333333' : '#f5f5f5',
      minHeight: '100vh',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
    },
    registerBox: {
      width: '100%',
      maxWidth: '500px',
      padding: '50px 30px',
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
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      marginBottom: '10px',
      width: '100%',
    },
    label: {
      display: 'block',
      color: theme === 'light' ? '#333333' : '#f5f5f5',
      marginBottom: '10px',
      fontSize: '14px',
      width: '80%',
      textAlign: 'left',
    },
    input: {
      width: '80%',
      padding: '10px',
      borderRadius: '4px',
      border: `1px solid ${theme === 'light' ? '#CCCCCC' : '#555555'}`,
      fontSize: '16px',
      backgroundColor: theme === 'light' ? '#FFFFFF' : '#444444',
      color: theme === 'light' ? '#333333' : '#f5f5f5',
    },
    button: {
      width: '80%',
      padding: '10px',
      backgroundColor: theme === 'light' ? '#800000' : '#A9A9A9',
      border: 'none',
      borderRadius: '4px',
      color: '#FFFFFF',
      fontSize: '16px',
      cursor: isSubmitting ? 'not-allowed' : 'pointer',
      fontWeight: 500,
      marginTop: '25px',
      opacity: isSubmitting ? 0.7 : 1,
    },
    backButton: {
      width: '80%',
      padding: '10px',
      backgroundColor: 'transparent',
      border: `1px solid ${theme === 'light' ? '#800000' : '#A9A9A9'}`,
      borderRadius: '4px',
      color: theme === 'light' ? '#800000' : '#A9A9A9',
      fontSize: '16px',
      cursor: 'pointer',
      fontWeight: 500,
      marginTop: '10px',
    },
    loginLinkContainer: {
      marginTop: '20px',
      fontSize: '14px',
      textAlign: 'center',
    },
    loginLink: {
      color: theme === 'light' ? '#800000' : '#A9A9A9',
      textDecoration: 'none',
      fontWeight: 500,
      marginLeft: '40px',
    },
    error: {
      color: '#800000',
      marginBottom: '15px',
      fontSize: '14px',
    },
    resendLink: {
      color: theme === 'light' ? '#800000' : '#A9A9A9',
      textDecoration: 'none',
      cursor: 'pointer',
      fontSize: '14px',
      marginTop: '10px',
    },
    usernameAvailability: {
      fontSize: '14px',
      marginTop: '5px',
      color: usernameAvailable ? 'green' : 'red',
    },
    usernameRequirements: {
      fontSize: '12px',
      marginTop: '5px',
      color: theme === 'light' ? '#666666' : '#999999',
      width: '80%',
      textAlign: 'left',
    },
    passwordStrength: {
      fontSize: '14px',
      marginTop: '5px',
      color: passwordStrength === 'strong' ? 'green' : passwordStrength === 'medium' ? 'orange' : 'red',
    },
    emailDisplay: {
      fontSize: '14px',
      color: theme === 'light' ? '#444444' : '#999999',
      marginBottom: '20px',
      padding: '10px',
      backgroundColor: theme === 'light' ? '#f8f8f8' : '#2a2a2a',
      borderRadius: '4px',
      width: '80%',
      margin: '0 auto 20px',
    },
  };

  return (
    <div style={styles.container}>
      <AppHeader showRegister={false} showBackToHome={false}/>
      <div style={styles.registerBox}>
        <h2 style={styles.header}>Register</h2>
        {error && <p style={styles.error}>{error}</p>}
        {step === 1 && (
          <form onSubmit={handleEmailSubmit}>
            <div style={styles.inputGroup}>
              <label style={styles.label}>Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                style={styles.input}
                placeholder="Enter your email"
                disabled={isSubmitting}
              />
            </div>
            <button type="submit" style={styles.button} disabled={isSubmitting}>
              {isSubmitting ? 'Sending...' : 'Send Verification Code'}
            </button>
          </form>
        )}
        {step === 2 && (
          <form onSubmit={handleVerificationSubmit}>
            <div style={styles.emailDisplay}>
              Verification code sent to: {email}
            </div>
            <p style={styles.resendLink} onClick={handleResendVerification}>
              {countdown > 0 ? `Resend code in ${countdown}s` : 'Click to resend verification code'}
            </p>
            <div style={styles.inputGroup}>
              <label style={styles.label}>Verification Code</label>
              <input
                type="text"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value)}
                required
                style={styles.input}
                placeholder="Enter verification code"
                disabled={isSubmitting}
              />
            </div>
            <button type="submit" style={styles.button} disabled={isSubmitting}>
              {isSubmitting ? 'Verifying...' : 'Verify Code'}
            </button>
            <button type="button" style={styles.backButton} onClick={handleBack}>
              Back
            </button>
          </form>
        )}
        {step === 3 && (
          <form onSubmit={handleIdentitySubmit}>
            <div style={styles.inputGroup}>
              <label style={styles.label}>First Name</label>
              <input
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
                style={styles.input}
                placeholder="Enter your first name"
                disabled={isSubmitting}
              />
            </div>
            <div style={styles.inputGroup}>
              <label style={styles.label}>Last Name</label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
                style={styles.input}
                placeholder="Enter your last name"
                disabled={isSubmitting}
              />
            </div>
            <div style={styles.inputGroup}>
              <label style={styles.label}>Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                style={styles.input}
                placeholder="Choose a username"
                disabled={isSubmitting}
              />
              <div style={styles.usernameRequirements}>
                Username requirements:
                <ul>
                  <li>3-20 characters long</li>
                  <li>Letters, numbers, underscores, and hyphens only</li>
                  <li>Must be unique</li>
                </ul>
              </div>
              {username && (
                <p style={styles.usernameAvailability}>
                  {usernameError}
                </p>
              )}
            </div>
            <button type="submit" style={styles.button} disabled={isSubmitting || !usernameAvailable}>
              {isSubmitting ? 'Submitting...' : 'Next'}
            </button>
          </form>
        )}
        {step === 4 && (
          <form onSubmit={handleFinalSubmit}>
            <div style={styles.inputGroup}>
              <label style={styles.label}>Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={styles.input}
                placeholder="Enter password"
                disabled={isSubmitting}
              />
              {password.length > 0 &&
                (<p style={styles.passwordStrength}>
                  Password strength: {passwordStrength}
                </p>)
              }
            </div>
            <div style={styles.inputGroup}>
              <label style={styles.label}>Confirm Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                style={styles.input}
                placeholder="Confirm password"
                disabled={isSubmitting}
              />
            </div>
            <div style={styles.inputGroup}>
              <label style={styles.label}>Organization Sign-up Code (Optional)</label>
              <input
                type="text"
                value={organizationCode}
                onChange={(e) => setOrganizationCode(e.target.value)}
                style={styles.input}
                placeholder="XXXX-XXXX-XXXX"
                disabled={isSubmitting}
              />
            </div>
            <button type="submit" style={styles.button} disabled={isSubmitting || passwordStrength === 'weak'}>
              {isSubmitting ? 'Registering...' : 'Complete Registration'}
            </button>
          </form>
        )}
        <div style={styles.loginLinkContainer}>
          <span>Already have an account?</span>
          <Link to="/login" style={styles.loginLink}>Login</Link>
        </div>
      </div>
    </div>
  );
};

export default Register;
