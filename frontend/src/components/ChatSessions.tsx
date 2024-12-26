import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { format, isToday, isThisWeek, isThisMonth, isThisYear } from 'date-fns';
import '../styles/ChatSessions.css';
import { useUserContext } from '../context/UserContext';
import axiosInstance from '../axiosInstance';
import { ChatSession } from '../types/ChatTypes';

interface ChatSessionsProps {
  sessions: ChatSession[];
  onSelectChat: (chat: ChatSession) => void;
  onNewChat: () => void;
}

const ChatSessions: React.FC<ChatSessionsProps> = ({ sessions = [], onSelectChat, onNewChat }) => {
  const { user, guestToken } = useUserContext();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [activeChatId, setActiveChatId] = useState<string | undefined>(id);
  const [currentSessions, setCurrentSessions] = useState<ChatSession[]>(sessions);

  // Convert UTC to the user's local timezone
  const convertToUserTimezone = (dateString: string): Date => {
    const dateUTC = new Date(dateString);
    return new Date(dateUTC.toLocaleString());
  };

  // Update active chat ID when URL changes
  useEffect(() => {
    if (id) {
      setActiveChatId(id);
    }
  }, [id]);

  // Watch for changes in the sessions prop and update local state
  useEffect(() => {
    const updatedSessions = sessions.map((session) => ({
      ...session,
      createdAt: convertToUserTimezone(session.createdAt).toISOString(),
    }));
    setCurrentSessions(updatedSessions);
  }, [sessions]);

  const handleChatClick = (session: ChatSession) => {
    setActiveChatId(session.id);
    onSelectChat(session);
    navigate(`/chat/${session.id}`);
  };

  const fetchChatSessions = async () => {
    try {
      const token = localStorage.getItem('token') || localStorage.getItem('guest_token');
      console.log('Token being used for chat session fetch:', token);

      if (!token) {
        console.error('Token is required to fetch chat sessions.');
        return;
      }

      const response = await axiosInstance.get<ChatSession[]>('/chat_sessions', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      console.log('Fetched chat sessions:', response.data);
      const updatedSessions = response.data.map((session) => ({
        ...session,
        createdAt: convertToUserTimezone(session.createdAt).toISOString(),
      }));
      setCurrentSessions(updatedSessions);
    } catch (error) {
      console.error('Error fetching chat sessions:', error);
    }
  };

  useEffect(() => {
    fetchChatSessions();
  }, [user, guestToken]); // Run whenever user or guestToken changes

  const categorizeSessions = (sessions: ChatSession[]) => {
    const categories: { [key: string]: ChatSession[] } = {
      Today: [],
      'Past week': [],
      'Past month': [],
      'Past year': [],
    };
    const months: { [key: string]: ChatSession[] } = {};
    const years: { [key: string]: ChatSession[] } = {};

    sessions.forEach((session) => {
      let createdAt: Date;
      try {
        if (!session.createdAt) {
          throw new Error(`Session ${session.id} does not have a createdAt field.`);
        }

        createdAt = new Date(session.createdAt);
        if (isNaN(createdAt.getTime())) {
          throw new Error('Invalid date');
        }

        if (isToday(createdAt)) {
          categories.Today.push(session);
        } else if (isThisWeek(createdAt)) {
          categories['Past week'].push(session);
        } else if (isThisMonth(createdAt)) {
          categories['Past month'].push(session);
        } else if (isThisYear(createdAt)) {
          categories['Past year'].push(session);
        } else {
          const monthYear = format(createdAt, 'MMMM yyyy');
          const year = format(createdAt, 'yyyy');

          if (!months[monthYear]) {
            months[monthYear] = [];
          }
          months[monthYear].push(session);

          if (!years[year]) {
            years[year] = [];
          }
        }
      } catch (error) {
        console.error(`Invalid date for session ${session.id}: ${session.createdAt}`);
        return;
      }
    });

    return { ...categories, ...months, ...years };
  };

  const renderSessions = (sessions: ChatSession[], title: string) => (
    <>
      {sessions.length > 0 && <h3 className="section-header">{title}</h3>}
      <ul className="session-list">
        {sessions.map((session) => (
          <li
            key={session.id}
            onClick={() => handleChatClick(session)}
            className={`session-item ${session.id === activeChatId ? 'active' : ''}`}
          >
            <span className="session-title">{session.title}</span>
          </li>
        ))}
      </ul>
    </>
  );

  const categorizedSessions = categorizeSessions(currentSessions);

  return (
    <div className="chat-sessions-container">
      <button onClick={onNewChat} className="new-chat-button">
        New Conversation
      </button>
      {Object.keys(categorizedSessions).map((category) =>
        renderSessions(categorizedSessions[category], category)
      )}
    </div>
  );
};

export default ChatSessions;
