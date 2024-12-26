import React, { useState, useContext } from 'react';
import axiosInstance from '../axiosInstance';
import { useNavigate } from 'react-router-dom';
import { ThemeContext } from '../context/ThemeContext';
import { AxiosError } from 'axios';
import { ThemeContextType } from '../types';


// Define the OrganizationData interface
interface OrganizationData {
  name: string;
  email_suffix: string;
  admin_password: string;
  organization_password: string;
}

interface Styles {
  [key: string]: React.CSSProperties;
}

const CreateOrganization: React.FC = () => {
    const [name, setName] = useState<string>('');
    const [emailSuffix, setEmailSuffix] = useState<string>('');
    const [adminPassword, setAdminPassword] = useState<string>('');
    const [organizationPassword, setOrganizationPassword] = useState<string>('');
    const [error, setError] = useState<string>('');
    const navigate = useNavigate();

    const { theme } = useContext(ThemeContext) as ThemeContextType;

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setError('');

        try {
            const organizationData: OrganizationData = {
                name,
                email_suffix: emailSuffix,
                admin_password: adminPassword,
                organization_password: organizationPassword,
            };

            const response = await axiosInstance.post('/organization/create_organization', organizationData);

            if (response.status === 201) {
                navigate('/org-create-success');
            }
        } catch (err) {
            console.error('Error creating organization:', err);

            if (err instanceof AxiosError && err.response) {
                const errorMessage = err.response.data.message;
                setError(errorMessage || 'Failed to create organization. Please try again.');
            } else {
                setError('Network error. Please check your connection and try again.');
            }
        }
    };

    // Define theme-based styles
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
            fontFamily: "'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif",
        },
        form: {
            width: '100%',
            maxWidth: '500px',
            padding: '65px 30px',
            backgroundColor: theme === 'light' ? '#FFFFFF' : '#333333',
            borderRadius: '8px',
            boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
            border: theme === 'light' ? 'none' : '1px solid #444444',
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
            marginBottom: '20px',
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
            border: theme === 'light' ? '1px solid #CCCCCC' : '1px solid #555555',
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
            marginTop: '25px',
        },
        error: {
            color: '#800000',
            marginBottom: '15px',
            fontSize: '14px',
        },
    };

    return (
        <div style={styles.container}>
            <div style={styles.form}>
                <h2 style={styles.header}>Create Organization</h2>
                {error && <p style={styles.error}>{error}</p>}
                <form onSubmit={handleSubmit}>
                    <div style={styles.inputGroup}>
                        <label style={styles.label}>Organization Name</label>
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            required
                            style={styles.input}
                            placeholder="Enter organization name"
                        />
                    </div>
                    <div style={styles.inputGroup}>
                        <label style={styles.label}>Corporate Email Suffix (optional)</label>
                        <input
                            type="text"
                            value={emailSuffix}
                            onChange={(e) => setEmailSuffix(e.target.value)}
                            style={styles.input}
                            placeholder="ex. @acaceta.com"
                        />
                    </div>
                    <div style={styles.inputGroup}>
                        <label style={styles.label}>Admin Password</label>
                        <input
                            type="password"
                            value={adminPassword}
                            onChange={(e) => setAdminPassword(e.target.value)}
                            required
                            style={styles.input}
                            placeholder="Enter admin password"
                        />
                    </div>
                    <div style={styles.inputGroup}>
                        <label style={styles.label}>Organization Upload Password</label>
                        <input
                            type="password"
                            value={organizationPassword}
                            onChange={(e) => setOrganizationPassword(e.target.value)}
                            required
                            style={styles.input}
                            placeholder="Enter organization upload password"
                        />
                    </div>
                    <button type="submit" style={styles.button}>Create Organization</button>
                </form>
            </div>
        </div>
    );
};

export default CreateOrganization;
