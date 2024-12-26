import { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AxiosError } from 'axios';
import axiosInstance from '../axiosInstance';
import { UserContext } from '../context/UserContext';
import { UserContextType } from '../types';
import { User } from '../types';

interface LoginResponse {
    user: User;
    token: string;
    refresh_token: string;
}

export const useHandleLogin = () => {
    const { login, logout } = useContext(UserContext) as UserContextType;
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string>('');
    const navigate = useNavigate();

    const handleLogin = async (usernameOrEmail: string, password: string) => {
        setIsLoading(true);
        setError('');
        try {
            localStorage.removeItem('guest_token');
            const response = await axiosInstance.post<LoginResponse>('/auth/login', {
                usernameOrEmail,
                password
            });

            const { user, token, refresh_token } = response.data;

            // Clear any existing session
            logout();

            // Set new tokens
            localStorage.setItem('token', token);
            localStorage.setItem('refresh_token', refresh_token);

            // Update user context
            login(user, token, refresh_token);

            // Navigate to home
            navigate('/home');
            return true;
        } catch (error) {
            if (error instanceof AxiosError) {
                // Extract and clean up error message
                let errorMessage = error.response?.data?.error ||
                                 error.response?.data?.message ||
                                 error.message ||
                                 'An unexpected error occurred. Please try again.';

                // Clean up specific error messages
                if (errorMessage.includes('Invalid login credentials:')) {
                    errorMessage = 'Invalid login credentials';
                }

                // Set the cleaned error message for display
                setError(errorMessage);

                // Log for debugging
                console.error('Login error:', {
                    status: error.response?.status,
                    data: error.response?.data,
                    originalMessage: error.response?.data?.error,
                    cleanedMessage: errorMessage
                });
            } else {
                setError('An unexpected error occurred. Please try again.');
            }
            return false;
        } finally {
            setIsLoading(false);
        }
    };

    return {
        handleLogin,
        isLoading,
        error
    };
};
