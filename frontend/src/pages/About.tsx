import React from 'react'
import logo from '../assets/images/logo3.png';
import ContactUs from '../components/ContactUs';

const About: React.FC = () => {
  return (
    <div style={styles.container}>
      <div style={styles.content}>
        <div style={styles.topLogoContainer}>
          <img src={logo} alt="Acaceta Logo" style={styles.largeLogo} />
          <h2 style={styles.bottomText}>Acaceta AI</h2>
        </div>
        <p style={styles.text}>
          We leverage language models to empower medical device reps and companies with information. Our platform allows medical professionals to interface with thousands of documents, getting lightning-fast evidence-based answers to product questions.
        </p>
        <ContactUs />
      </div>
    </div>
  );
};

const styles: {
  [key: string]: React.CSSProperties | { [key: string]: React.CSSProperties }
} = {
  container: {
    textAlign: 'center',
    padding: '15px',
    backgroundColor: '#F5F5F5',
    color: '#333333',
    minHeight: '100vh',
    fontFamily: "'Inter', sans-serif",
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '20px',
    flex: 1,
  },
  topLogoContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    marginTop: '50px',
  },
  largeLogo: {
    width: '120px',
    height: '120px',
  },
  bottomText: {
    fontSize: '36px',
    fontWeight: 600,
    color: '#1A1A1A',
    marginTop: '20px',
    fontFamily: "'Inter', sans-serif",
    letterSpacing: '0.1em',
  },
  text: {
    color: '#1A1A1A',
    fontWeight: 400,
    fontSize: '16px',
    fontFamily: "'Inter', sans-serif",
    maxWidth: '800px',
    textAlign: 'left',
    margin: '20px auto',
  },
  '@media (max-width: 768px)': {
    content: {
      marginTop: '30px',
      marginBottom: '10px',
    },
    largeLogo: {
      width: '100px',
      height: '100px',
    },
    bottomText: {
      fontSize: '28px',
    },
    text: {
      fontSize: '14px',
      maxWidth: '90%',
    },
  },
  '@media (max-width: 480px)': {
    content: {
      marginTop: '20px',
      marginBottom: '5px',
    },
    largeLogo: {
      width: '80px',
      height: '80px',
    },
    bottomText: {
      fontSize: '24px',
    },
    text: {
      fontSize: '12px',
      maxWidth: '95%',
    },
  },
};

export default About;
