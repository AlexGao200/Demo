import React, { ComponentType } from 'react';
import { Navigate } from 'react-router-dom';
import { useUserContext } from '../context/UserContext';

interface PrivateRouteProps {
  element: ComponentType<any>;
  [key: string]: any;
}

const PrivateRoute: React.FC<PrivateRouteProps> = ({ element: Component, ...rest }) => {
  const { user, loading } = useUserContext();

  console.log('PrivateRoute: user:', user); // Debug user state
  console.log('PrivateRoute: token:', localStorage.getItem('token')); // Debug token state

  if (loading) {
    return <div>Loading...</div>; // Render a loading state while fetching user
  }

  return user ? (
    <Component {...rest} />
  ) : (
    <Navigate to="/login" replace />
  );
};

export default PrivateRoute;
