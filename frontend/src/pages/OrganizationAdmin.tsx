import React, { useState, useEffect, useContext } from 'react';
import axiosInstance from '../axiosInstance';
import { ThemeContext } from '../context/ThemeContext';
import { ApiError, handleApiError } from '../utils/errorHandling';

interface ThemeContextType {
    theme: 'light' | 'dark';
}

interface Organization {
    organization_id: string;
    organization_name: string;
}

function AddAdmin() {
    const { theme } = useContext(ThemeContext) as ThemeContextType;
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [selectedOrganization, setSelectedOrganization] = useState<string>('');
    const [password, setPassword] = useState<string>('');
    const [email, setEmail] = useState<string>('');  // Changed from username to email
    const [error, setError] = useState<ApiError | null>(null);
    const [successMessage, setSuccessMessage] = useState<string>('');

    // Fetch organizations on component mount
    useEffect(() => {
        async function fetchOrganizations() {
            try {
                const response = await axiosInstance.get<{ organizations: Organization[] }>('/organization/get-all');
                setOrganizations(response.data.organizations);
            } catch (error: unknown) {
                setError(handleApiError(error));
            }
        }
        fetchOrganizations();
    }, []);

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setError(null);
        setSuccessMessage('');

        try {
            // Send request to add the admin by email
            const response = await axiosInstance.post<{ message: string }>('/organization/add_admin', {
                organization_id: selectedOrganization,
                password: password,
                email: email.trim(),  // Changed to email
            });

            setSuccessMessage(response.data.message);
        } catch (error: unknown) {
            setError(handleApiError(error));
        }
    };

    const styles: { [key: string]: React.CSSProperties } = {
        container: {
            textAlign: 'center',
            padding: '20px',
            backgroundColor: theme === 'light' ? '#F5F5F5' : '#1A1A1A',
            color: theme === 'light' ? '#333333' : '#F5F5F5',
            minHeight: '100vh',
            fontFamily: "'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif",
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
        },
        formContainer: {
            width: '100%',
            maxWidth: '400px',
            padding: '30px',
            backgroundColor: theme === 'light' ? '#FFFFFF' : '#333333',
            borderRadius: '8px',
            boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
        },
        input: {
            width: '100%',
            padding: '10px',
            borderRadius: '4px',
            border: `1px solid ${theme === 'light' ? '#CCCCCC' : '#555555'}`,
            backgroundColor: theme === 'light' ? '#FFFFFF' : '#444444',
            color: theme === 'light' ? '#333333' : '#F5F5F5',
            marginBottom: '20px',
            fontSize: '16px',
        },
        button: {
            width: '100%',
            padding: '10px',
            backgroundColor: theme === 'light' ? '#0066CC' : '#A9A9A9',
            border: 'none',
            borderRadius: '4px',
            color: '#FFFFFF',
            fontSize: '16px',
            cursor: 'pointer',
            fontWeight: 500,
        },
        message: {
            marginTop: '20px',
            color: theme === 'light' ? '#006600' : '#A9A9A9',
        },
        error: {
            marginTop: '20px',
            color: '#FF0000',
        },
    };

    return (
        <div style={styles.container}>
            <div style={styles.formContainer}>
                <h1>Add Administrator</h1>
                <form onSubmit={handleSubmit}>
                    {/* Dropdown for organization selection */}
                    <select
                        value={selectedOrganization}
                        onChange={(e) => setSelectedOrganization(e.target.value)}
                        style={styles.input}
                    >
                        <option value="" disabled>Select Organization</option>
                        {organizations.map((org) => (
                            <option key={org.organization_id} value={org.organization_id}>
                                {org.organization_name}
                            </option>
                        ))}
                    </select>

                    <input
                        type="password"
                        placeholder="Organization Password"
                        value={password}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
                        style={styles.input}
                    />
                    <input
                        type="email"
                        placeholder="User Email"  // Changed label to "User Email"
                        value={email}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
                        style={styles.input}
                    />
                    <button type="submit" style={styles.button}>Add Admin</button>
                </form>
                {successMessage && <p style={styles.message}>{successMessage}</p>}
                {error && (
                    <div style={styles.error}>
                        <p>{error.message}</p>
                        {error.details && <p>{error.details}</p>}
                    </div>
                )}
            </div>
        </div>
    );
}

export default AddAdmin;
