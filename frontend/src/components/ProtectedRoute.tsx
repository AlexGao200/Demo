import React, { useEffect, useContext, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { UserContext } from '../context/UserContext';

interface ProtectedRouteProps {
    children: ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
    const { user, guestToken, loading } = useContext(UserContext); // Add guestToken to context
    const navigate = useNavigate();

    useEffect(() => {
        if (!loading) {
            // Allow access if user is logged in or if a guest token is available
            if (!user && !guestToken) {
                navigate('/home'); // Redirect to home if no user or guest session
            } else if (user?.sessionExpired) {
                navigate('/login'); // Redirect to login if user session expired
            }
        }
    }, [user, guestToken, loading, navigate]);

    return <>{children}</>;
};

export default ProtectedRoute;
