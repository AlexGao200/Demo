import { useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { UserContext } from '../context/UserContext';
import axiosInstance from '../axiosInstance';

interface UseAuthReturn {
  user: any;
  handleLogout: () => Promise<void>;
}

export const useAuth = (): UseAuthReturn => {
  const { user, logout } = useContext(UserContext);
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await axiosInstance.post('/auth/logout');
      logout();
      navigate('/login');
    } catch (error) {
      console.error('Error logging out:', error);
    }
  };

  return { user, handleLogout };
};
