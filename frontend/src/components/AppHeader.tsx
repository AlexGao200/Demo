import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axiosInstance from '../axiosInstance';
import { useUserContext } from '../context/UserContext';
import { useThemeContext } from '../context/ThemeContext';
import '../styles/AppHeader.css';
import { FaBars } from 'react-icons/fa6';
import logo from '../assets/images/logo3.png';
import Sidebar from '../components/Sidebar';

const AppHeader = ({ showBackToHome = true, showRegister = true, showLogin = true }) => {
    const { user, logout } = useUserContext();
    const { theme } = useThemeContext();
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const sidebarRef = useRef<HTMLDivElement>(null);
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

    const toggleSidebar = () => {
        setIsSidebarOpen(!isSidebarOpen);
    };

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (sidebarRef.current && !sidebarRef.current.contains(event.target as Node)) {
                setIsSidebarOpen(false);
            }
        };

        if (isSidebarOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isSidebarOpen]);

    return (
        <>
            <header className={`app-header ${theme === 'dark' ? 'dark-mode' : ''}`}>
                <div className="app-header-left">
                    <Link to="/home" className="app-header-title">
                        <div className="app-logo-container">
                            <div className="app-logo-box">
                                <img src={logo} alt="Acaceta Logo" className="app-logo" style={{ height: '34px', width: 'auto' }} />
                            </div>
                            <div className="app-title-box">
                                <h1>Acaceta</h1>
                            </div>
                        </div>
                    </Link>
                </div>
                <div className="app-header-center">
                    {showBackToHome && (
                        <Link to="/home" className="app-back-link app-center-home">
                            Home
                        </Link>
                    )}
                </div>
                <div className="app-header-right">
                    <div className="app-header-actions">
                        {user ? (
                            <>
                                <button onClick={handleLogout} className="app-logout-button">
                                    Logout
                                </button>
                                <button onClick={toggleSidebar} className="app-sidebar-toggle-button">
                                    <FaBars className="app-theme-icon" />
                                </button>
                            </>
                        ) : (
                            <>
                                {showLogin && (
                                    <Link to="/login" className="app-login-link">
                                        Login
                                    </Link>
                                )}
                                {showRegister && (
                                    <Link to="/register" className="app-register-link">
                                        Register
                                    </Link>
                                )}
                            </>
                        )}
                    </div>
                </div>
            </header>
            <div ref={sidebarRef}>
                <Sidebar isOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />
            </div>
        </>
    );
};

export default AppHeader;
