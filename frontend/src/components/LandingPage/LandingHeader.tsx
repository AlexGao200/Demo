import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useUserContext } from '../../context/UserContext';
import { useThemeContext } from '../../context/ThemeContext';
import { FaMoon, FaSun } from 'react-icons/fa6';
import styles from '../../styles/landingpage/LandingHeader.module.css';
import logo from '../../assets/images/logo3.png';

interface LandingHeaderProps {
  headerHidden: boolean;
}

const LandingHeader: React.FC<LandingHeaderProps> = ({ headerHidden }) => {
  const { user, logout } = useUserContext();
  const { theme, toggleTheme } = useThemeContext();
  const navigate = useNavigate();
  const [isModalOpen, setModalOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const toggleModal = () => {
    setModalOpen(!isModalOpen);
  };

  return (
    <header className={`${styles.landingHeader} ${headerHidden ? styles.headerHidden : ''} ${theme === 'dark' ? styles.darkMode : ''}`}>
      <div className={styles.logoContainer}>
        <Link to="/" className={styles.headerTitle}>
          <img src={logo} alt="Acaceta Logo" className={styles.logo} />
          <h1 className={styles.title}>Acaceta</h1>
        </Link>
      </div>

      <nav className={styles.navLinks}>
        {user ? (
          <>
            <Link to="/" onClick={handleLogout} className={styles.navLink}>Logout</Link>
            <Link to="/home" className={styles.navLink}>Home</Link>
          </>
        ) : (
          <>
            <Link to="/register" className={styles.navLink}>Register</Link>
            <Link to="/login" className={styles.navLink}>Login</Link>
          </>
        )}
        <Link to="/home" className={styles.navLink}>Chat</Link>
        <Link to="/about" className={styles.navLink}>About</Link>
        <button onClick={toggleModal} className={styles.contactButton}>
          Contact
        </button>

      </nav>

      {isModalOpen && (
        <div className={styles.modalOverlay} onClick={toggleModal}>
          <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <h2>Contact Us</h2>
            <form action="https://formspree.io/f/mkgngeyk" method="POST">
              <label>
                Your email:
                <input type="email" name="email" required />
              </label>
              <label>
                Your message:
                <textarea name="message" required></textarea>
              </label>
              <button type="submit">Send</button>
            </form>
            <button className={styles.closeButton} onClick={toggleModal}>X</button>
          </div>
        </div>
      )}
    </header>
  );
};

export default LandingHeader;
