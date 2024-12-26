import React, { useContext } from 'react';
import { Link } from 'react-router-dom';
import '../styles/Sidebar.css'; // Sidebar styles
import { ThemeContext } from '../context/ThemeContext';
import { useUserContext } from '../context/UserContext'; // Use UserContext for user data
import { FaMoon, FaSun } from 'react-icons/fa6'; // Icons for theme toggle
import logo from '../assets/images/logo3.png'; // Import the logo

interface SidebarProps {
  isOpen: boolean;
  toggleSidebar: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, toggleSidebar }) => {
  const { theme, toggleTheme } = useContext(ThemeContext);
  const { user } = useUserContext(); // Get user data from UserContext

  // Determine the link and label for subscription management or billing
  let billingLink = null;

  // Check if subscription_paid_by is None (i.e., user is responsible for payment)
  if (!user?.subscription_paid_by) {
    if (user?.subscription_status === 'none') {
      // If no subscription, direct to the subscription sign-up page
      billingLink = (
        <li>
          <Link to="/subscription">Subscription</Link>
        </li>
      );
    } else if (user?.subscription_status === 'active') {
      // If active subscription, direct to the subscription management page
      billingLink = (
        <li>
          <Link to="/subscription-management">Manage Subscription</Link>
        </li>
      );
    }
  }

  return (
    <div className={`sidebar ${isOpen ? 'open' : ''} ${theme === 'dark' ? 'dark-mode' : ''}`}>
      <button className="close-btn" onClick={toggleSidebar}>
        Close
      </button>

      {/* Logo */}
      <div className="logo-container">
        <img src={logo} alt="Acaceta Logo" className="sidebar-logo" />
      </div>

      {/* Display user's name */}
      <div className="user-info">
        {user ? (
          <p>{user.first_name} {user.last_name}</p>
        ) : (
          <p>Guest</p>
        )}
      </div>

      <nav>
        <ul>
          <li>
            <Link to="/home">Home</Link>
          </li>
          <li>
            <Link to="/library">Library</Link>
          </li>
          <li>
            <Link to="/chat_history">Chat History</Link>
          </li>
          <li>
            <Link to="/organization-login">Organization Dashboard</Link>
          </li>

          {/* Conditionally render the subscription or billing link */}
          {billingLink}

        </ul>
      </nav>

      {/* Theme Toggle */}
      <div className="theme-toggle">
        <button onClick={toggleTheme} className="theme-toggle-switch">
          {theme === 'dark' ? <FaMoon className="theme-icon" /> : <FaSun className="theme-icon" />}
          <span className="theme-text">
            {theme === 'dark' ? ' Dark Mode' : ' Light Mode'}
          </span>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
