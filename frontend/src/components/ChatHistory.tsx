import React, { useEffect, useState } from 'react';
import axiosInstance from '../axiosInstance';
import { Link } from 'react-router-dom';

import { ChatSession } from '../types';

const ChatHistory: React.FC = () => {
  const [chats, setChats] = useState<ChatSession[]>([]);

  useEffect(() => {
    const fetchChatSessions = async () => {
      try {
        const response = await axiosInstance.get<ChatSession[]>('/chat_sessions');
        setChats(response.data);
      } catch (error) {
        console.error('Error fetching chat sessions:', error);
      }
    };

    fetchChatSessions();
  }, []);

  return (
    <div style={styles.container}>
      <h1>Chat History</h1>
      <ul style={styles.chatList}>
        {chats.map((chat) => (
          <li key={chat.id} style={styles.chatItem}>
            <Link to={`/chat/${chat.id}`} style={styles.link}>
              {chat.title}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
};

const styles = {
  container: {
    padding: '20px',
  },
  chatList: {
    listStyle: 'none' as const,
    padding: 0,
  },
  chatItem: {
    padding: '10px 0',
  },
  link: {
    color: '#4CAF50',
    textDecoration: 'none',
  },
};

export default ChatHistory;
