import React, { useEffect, useState, useContext } from 'react';
import axiosInstance from '../axiosInstance';
import { ThemeContext } from '../context/ThemeContext';
import { useNavigate } from 'react-router-dom';
import { ThemeContextType } from '../types';
import { handleApiError, ApiError } from '../utils/errorHandling';

const SubscriptionManagement: React.FC = () => {
  const { theme } = useContext(ThemeContext) as ThemeContextType;
  const [error, setError] = useState<ApiError | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [subscriptionEndDate, setSubscriptionEndDate] = useState<string | null>(null); // For canceled subscriptions
  const navigate = useNavigate();

  // Fetches and redirects to the billing portal
  const handleManageSubscription = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await axiosInstance.get('/billing-portal');
      if (response.status === 200 && response.data.url) {
        window.location.href = response.data.url;
      } else if (response.data.error === 'no_customer_id') {
        navigate('/products');
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (err) {
      const apiError = handleApiError(err);
      setError(apiError);
    } finally {
      setIsLoading(false);
    }
  };

  // Cancels the subscription by calling the backend API
  const handleCancelSubscription = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await axiosInstance.post('/subscription_cancel');
      if (response.status === 200) {
        setSubscriptionEndDate(response.data.subscription_end_date); // Display the end date
        alert(`Subscription canceled. It will expire on ${new Date(response.data.subscription_end_date).toLocaleDateString()}.`);
      } else {
        throw new Error('Failed to cancel subscription');
      }
    } catch (err) {
      const apiError = handleApiError(err);
      setError(apiError);
    } finally {
      setIsLoading(false);
    }
  };

  // Updates the subscription plan by calling the backend API
  const handleUpdateSubscription = async (newPlanId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await axiosInstance.post('/subscription_update', { new_plan_id: newPlanId });
      if (response.status === 200) {
        alert('Subscription updated successfully');
      } else {
        throw new Error('Failed to update subscription');
      }
    } catch (err) {
      const apiError = handleApiError(err);
      setError(apiError);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    handleManageSubscription();
  }, []);

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
    messageBox: {
      width: '100%',
      maxWidth: '400px',
      padding: '40px 20px',
      backgroundColor: theme === 'light' ? '#FFFFFF' : '#333333',
      borderRadius: '8px',
      boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
      textAlign: 'center',
    },
    header: {
      fontSize: '24px',
      fontWeight: 600,
      color: theme === 'light' ? '#1A1A1A' : '#f5f5f5',
      marginBottom: '20px',
      letterSpacing: '-0.5px',
    },
    error: {
      color: theme === 'light' ? '#800000' : '#FFFFFF',
      marginBottom: '15px',
      fontSize: '14px',
    },
    button: {
      backgroundColor: theme === 'light' ? '#007BFF' : '#0056b3',
      color: '#FFFFFF',
      border: 'none',
      padding: '10px 20px',
      borderRadius: '4px',
      cursor: 'pointer',
      fontSize: '16px',
      marginTop: '20px',
      marginRight: '10px',
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.messageBox}>
        <h2 style={styles.header}>Subscription Management</h2>
        {isLoading ? (
          <p>Loading billing portal...</p>
        ) : error ? (
          <>
            <p style={styles.error}>{error.message}</p>
            {error.details && <p style={styles.error}>{error.details}</p>}
            <button style={styles.button} onClick={handleManageSubscription}>
              Try Again
            </button>
          </>
        ) : (
          <>
            <p>Manage your subscription below.</p>
            <button style={styles.button} onClick={() => handleUpdateSubscription('price_1QASZFRtAgEFTutZLDB7nKlI')}>
              Upgrade to Pro Plan
            </button>
            <button style={styles.button} onClick={handleCancelSubscription}>
              Cancel Subscription
            </button>
            {subscriptionEndDate && (
              <p>Your subscription will remain active until: {new Date(subscriptionEndDate).toLocaleDateString()}</p>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default SubscriptionManagement;
