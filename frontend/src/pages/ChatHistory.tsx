import React, { useContext, useEffect, useState } from 'react';
import { UserContext } from '../context/UserContext';
import { Link, useNavigate } from 'react-router-dom';
import axiosInstance from '../axiosInstance';
import AppHeader from '../components/AppHeader';


const ChatHistory: React.FC = () => {
  const { user, logout } = useContext(UserContext);
  const [chats, setChats] = useState<Chat[]>([]);
  const navigate = useNavigate();

  // Detect the current theme from localStorage or context
  const currentTheme = localStorage.getItem('theme') || 'light';

  useEffect(() => {
    const fetchChatSessions = async () => {
      try {
        const response = await axiosInstance.get<Chat[]>('/chat_sessions');
        setChats(response.data);
      } catch (error) {
        console.error('Error fetching chat sessions:', error);
      }
    };

    if (user) {
      fetchChatSessions();
    }
  }, [user]);

  const handleLogout = async () => {
    try {
      await axiosInstance.post('/auth/logout');
      logout();
      navigate('/login');
    } catch (error) {
      console.error('Error logging out:', error);
    }
  };

  // Define styles dynamically based on the current theme
  const styles = {
    container: {
      backgroundColor: currentTheme === 'dark' ? '#121212' : '#F5F5F5',
      color: currentTheme === 'dark' ? '#F5F5F5' : '#333333',
      minHeight: '100vh',
      fontFamily: "'Inter', sans-serif",
      transition: 'background-color 0.3s ease, color 0.3s ease',
    },
    content: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      paddingTop: '40px',
    },
    title: {
      fontSize: '24px',
      marginBottom: '30px',
      color: currentTheme === 'dark' ? '#F5F5F5' : '#1A1A1A',
      fontWeight: 300,
      letterSpacing: '-0.5px',
    },
    chatsContainer: {
      display: 'flex',
      flexDirection: 'column',
      width: '80%',
      maxWidth: '800px',
      gap: '20px',
    },
    chat: {
      backgroundColor: currentTheme === 'dark' ? '#333333' : '#FFFFFF',
      padding: '0 0 0 15px',
      borderRadius: '4px',
      textDecoration: 'none',
      color: currentTheme === 'dark' ? '#F5F5F5' : '#4A4A4A',
      border: `1px solid ${currentTheme === 'dark' ? '#444444' : '#E0E0E0'}`,
      boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)',
      transition: 'box-shadow 0.3s ease, background-color 0.3s ease, color 0.3s ease',
      textAlign: 'left',
    },
    chatTitle: {
      fontSize: '14px',
      fontWeight: 500,
      marginBottom: '5px',
      color: currentTheme === 'dark' ? '#F5F5F5' : '#30343F',
    },
    chatDate: {
      fontSize: '12px',
      color: currentTheme === 'dark' ? '#CCCCCC' : '#999999',
    },
  } as const;

  return (
    <div style={styles.container}>
      <AppHeader />
      <div style={styles.content}>
        <h2 style={styles.title}>Chat History</h2>
        <div style={styles.chatsContainer}>
          {chats.map((chat, index) => (
            <Link key={index} to={`/chat/${chat._id}`} style={styles.chat}>
              <p style={styles.chatTitle}>{chat.title}</p>
              <p style={styles.chatDate}>{new Date(chat.createdAt).toLocaleString()}</p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ChatHistory;
