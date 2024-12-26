import React, { useState, useContext } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ThemeContext } from '../context/ThemeContext';
import { ThemeContextType } from '../types';
import AppHeader from '../components/AppHeader';
import axiosInstance from '../axiosInstance';

type ResetPasswordParams = {
    token: string;
};

const ResetPassword: React.FC = () => {
    const { token } = useParams<keyof ResetPasswordParams>();
    const navigate = useNavigate();
    const { theme } = useContext(ThemeContext) as ThemeContextType;
    const [newPassword, setNewPassword] = useState<string>('');
    const [confirmPassword, setConfirmPassword] = useState<string>('');
    const [message, setMessage] = useState<string>('');
    const [error, setError] = useState<string>('');
    const [isLoading, setIsLoading] = useState<boolean>(false);

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
        }
    };

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setError('');
        setMessage('');
        setIsLoading(true);

        if (newPassword !== confirmPassword) {
            setError('Passwords do not match');
            setIsLoading(false);
            return;
        }

        try {
            const response = await axiosInstance.post(`/auth/reset-password/${token}`, {
                new_password: newPassword
            });
            setMessage(response.data.message);
            setTimeout(() => {
                navigate('/login');
            }, 2000);
        } catch (err: unknown) {
            if (err instanceof Error) {
                setError(err.message);
            } else {
                setError('An unknown error occurred');
            }
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div style={styles.container}>
            <AppHeader showLogin={false} showBackToHome={false} />
            <div style={styles.box}>
                <h2 style={styles.header}>Reset Password</h2>
                <form onSubmit={handleSubmit}>
                    <div style={styles.inputGroup}>
                        <label style={styles.label}>New Password:</label>
                        <input
                            type="password"
                            value={newPassword}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewPassword(e.target.value)}
                            required
                            style={styles.input}
                        />
                    </div>
                    <div style={styles.inputGroup}>
                        <label style={styles.label}>Confirm Password:</label>
                        <input
                            type="password"
                            value={confirmPassword}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConfirmPassword(e.target.value)}
                            required
                            style={styles.input}
                        />
                    </div>
                    {message && <p style={styles.message}>{message}</p>}
                    {error && <p style={styles.error}>{error}</p>}
                    <button type="submit" style={styles.button} disabled={isLoading}>
                        {isLoading ? 'Resetting...' : 'Reset Password'}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default ResetPassword;
