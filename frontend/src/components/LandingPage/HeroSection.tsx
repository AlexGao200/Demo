import React from 'react';
import heroImage from '../../assets/images/carousel/31.png';
import styles from '../../styles/landingpage/HeroSection.module.css'; // Import CSS Module

const HeroSection: React.FC = () => {
  return (
    <div className={styles['hero-section']}>
      <div className={styles['hero-content']}>
        <img
          src={heroImage}
          alt="Delivering language learning solutions to medical device companies"
          className={styles['hero-image']}
        />
        <div className={styles['hero-text']}>
          <h1>Acaceta AI</h1>
          <h2>Delivering language learning solutions to medical device companies</h2>
        </div>
      </div>
    </div>
  );
};

export default HeroSection;
