import React, { useState } from 'react';
import axiosInstance from '../axiosInstance';

const ContactUs: React.FC = () => {
  const [name, setName] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const [message, setMessage] = useState<string>('');
  const [statusMessage, setStatusMessage] = useState<string>('');

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    try {
      await axiosInstance.post('/contact', { name, email, message });
      setStatusMessage('Your message has been sent successfully!');
      setName('');
      setEmail('');
      setMessage('');
    } catch (error) {
      setStatusMessage('There was an error sending your message. Please try again later.');
    }
  };

  return (
    <div style={styles.contactContainer}>
      <h2 style={styles.contactHeader}>Contact Us</h2>
      {statusMessage && <p style={styles.statusMessage}>{statusMessage}</p>}
      <form onSubmit={handleSubmit} style={styles.contactForm}>
        <div style={styles.inputGroup}>
          <label style={styles.label}>Name:</label>
          <input
            type="text"
            value={name}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)}
            required
            style={styles.input}
          />
        </div>
        <div style={styles.inputGroup}>
          <label style={styles.label}>Email:</label>
          <input
            type="email"
            value={email}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
            required
            style={styles.input}
          />
        </div>
        <div style={styles.inputGroup}>
          <label style={styles.label}>Message:</label>
          <textarea
            value={message}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setMessage(e.target.value)}
            required
            style={styles.textarea}
          />
        </div>
        <button type="submit" style={styles.submitButton}>Send Message</button>
      </form>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  contactContainer: {
    marginTop: '50px',
    maxWidth: '600px',
    width: '100%',
    textAlign: 'left',
    fontFamily: "'Inter', sans-serif",
  },
  contactHeader: {
    fontSize: '24px',
    fontWeight: 600,
    marginBottom: '20px',
    fontFamily: "'Inter', sans-serif",
  },
  contactForm: {
    display: 'flex',
    flexDirection: 'column',
    gap: '15px',
    fontFamily: "'Inter', sans-serif",
  },
  inputGroup: {
    display: 'flex',
    flexDirection: 'column',
    fontFamily: "'Inter', sans-serif",
  },
  label: {
    fontSize: '14px',
    marginBottom: '5px',
    fontFamily: "'Inter', sans-serif",
  },
  input: {
    padding: '10px',
    fontSize: '14px',
    borderRadius: '4px',
    border: '1px solid #ccc',
    fontFamily: "'Inter', sans-serif",
  },
  textarea: {
    padding: '10px',
    fontSize: '14px',
    borderRadius: '4px',
    border: '1px solid #ccc',
    minHeight: '100px',
    fontFamily: "'Inter', sans-serif",
  },
  submitButton: {
    padding: '10px',
    fontSize: '16px',
    fontWeight: 'bold',
    color: '#fff',
    backgroundColor: '#a40000',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontFamily: "'Inter', sans-serif",
  },
  statusMessage: {
    marginBottom: '20px',
    fontSize: '14px',
    color: '#a40000',
    fontFamily: "'Inter', sans-serif",
  },
};

export default ContactUs;
