import React, { useEffect, useState, useContext, useCallback } from 'react';
import { UserContext } from '../context/UserContext';
import { Link, useNavigate } from 'react-router-dom';
import { FaArrowRight } from 'react-icons/fa';
import axiosInstance from '../axiosInstance';
import filterIcon from '../assets/images/filter.png';
import AppHeader from '../components/AppHeader';
import logo from '../assets/images/logo2.png';
import QueryFilter from '../components/filters_new/QueryFilter';
import { UnifiedFilterProvider, useUnifiedFilter, setQueryFilters } from '../context/UnifiedFilterContext';
import '../styles/Home.css';
import { UserContextType } from '../types';
import { ChatSession } from '../types';
import { FilterProps } from '../types/FilterTypes';
import { getUserTimeZone } from '../utils/timeZone';

interface ApiError {
  response?: {
    status: number;
  };
}

const HomeContent: React.FC = () => {
  const { user, guestToken } = useContext(UserContext) as UserContextType;
  const { state: filterState, dispatch: filterDispatch } = useUnifiedFilter();
  const [recentChats, setRecentChats] = useState<ChatSession[]>([]);
  const [query, setQuery] = useState<string>('');
  const [showFilterOptions, setShowFilterOptions] = useState<boolean>(false);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchChatSessions = async (): Promise<void> => {
      try {
        const token = localStorage.getItem('token') || localStorage.getItem('guest_token');
        if (token) {
          const response = await axiosInstance.get<ChatSession[]>('/chat_sessions', {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });
          setRecentChats(response.data.slice(0, 3));
        }
      } catch (error) {
        console.error('Error fetching chat sessions:', error);
      }
    };
    fetchChatSessions();
  }, [user, guestToken]);

  const handleQueryAbort = () => {
    setShowFilterOptions(false);
  };

  const toggleFilterOptions = useCallback((): void => {
    setShowFilterOptions((prev) => !prev);
  }, []);

  const handleFiltersApplied = (filters: FilterProps): void => {
    setQueryFilters(filterDispatch, filters);
    setShowFilterOptions(false);
  };

  const handleNewChat = async (): Promise<void> => {
    if (query.trim()) {
      try {
        const token = localStorage.getItem('token') || localStorage.getItem('guest_token');
        if (!token) {
          // If no token exists, the axiosInstance will automatically create a guest session
          const response = await axiosInstance.post<{ chat_id: string }>(
            '/chat',
            {
              indices: filterState.query.indices.map(index => index.name),
              filters: filterState.query.filters || {},
              time_zone: getUserTimeZone(),
            }
          );
          const { chat_id } = response.data;
          navigate(`/chat/${chat_id}`, {
            state: { initialQuery: query },
          });
        } else {
          const response = await axiosInstance.post<{ chat_id: string }>(
            '/chat',
            {
              indices: filterState.query.indices.map(index => index.name),
              filters: filterState.query.filters || {},
              time_zone: getUserTimeZone(),
            }
          );
          const { chat_id } = response.data;
          navigate(`/chat/${chat_id}`, {
            state: { initialQuery: query },
          });
        }
      } catch (error) {
        console.error('Error starting a new chat:', error);
        const apiError = error as ApiError;
        if (apiError.response?.status === 401) {
          console.log('Unauthorized - attempting to create guest session');
          try {
            // Let axiosInstance handle the 401 error and create a guest session
            const response = await axiosInstance.post<{ chat_id: string }>(
              '/chat',
              {
                indices: filterState.query.indices.map(index => index.name),
                filters: filterState.query.filters || {},
                time_zone: getUserTimeZone(),
              }
            );
            const { chat_id } = response.data;
            navigate(`/chat/${chat_id}`, {
              state: { initialQuery: query },
            });
          } catch (retryError) {
            console.error('Error creating guest session:', retryError);
          }
        }
      }
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent<HTMLInputElement>): void => {
    if (event.key === 'Enter') {
      handleNewChat();
    }
  };

  return (
    <div className="container">
      <AppHeader showBackToHome={false} />
      <div className="content">
        <div className="home-container">
          <div className="content">
            {/* Logo */}
            <div className="logoContainer">
              <img src={logo} alt="Acaceta Logo" className="logo" />
            </div>
            <h2 className="greeting">
              Welcome, {user ? user.first_name : 'Guest'}
            </h2>
            <>
              <div className="inputContainer">
                <div className="queryInputContainer">
                  <button
                    className="filter-button"
                    onClick={toggleFilterOptions}
                    style={{
                      position: 'absolute',
                      left: '8px',
                      top: '0px',
                      backgroundColor: 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      width: '30px',
                      height: '30px',
                      padding: '0',
                    }}
                  >
                    <img
                      src={filterIcon}
                      alt="Filter"
                      style={{
                        width: '16px',
                        height: '16px',
                        display: 'block',
                        margin: '0 auto',
                      }}
                    />
                  </button>
                  <input
                    type="text"
                    placeholder="How may I assist you?"
                    value={query}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setQuery(e.target.value)}
                    onKeyUp={handleKeyPress}
                    className="queryInput"
                  />
                  {query && (
                    <FaArrowRight
                      className="arrowIcon"
                      onClick={handleNewChat}
                    />
                  )}
                </div>
              </div>

              {/* View Uploads button */}
              <Link to="/library" className="uploadLink">
                View Library
              </Link>

              {/* Recent conversations */}
              <div className="recentChatsContainer">
                <h2 className="recentChatsTitle">Recent conversations</h2>
                <ul className="chatList">
                  {recentChats.map((chat) => (
                    <li key={chat.id} className="chatItem">
                      <Link to={`/chat/${chat.id}`} className="chatLink">
                        {chat.title}
                      </Link>
                    </li>
                  ))}
                </ul>
                <Link to="/chat_history" className="viewAllLink">
                  View all
                </Link>
              </div>
            </>
          </div>
        </div>

        {showFilterOptions && (
          <QueryFilter
            onComplete={handleFiltersApplied}
            onAbort={handleQueryAbort}
          />
        )}
      </div>
    </div>
  );
};

const Home: React.FC = () => {
  return (
    <UnifiedFilterProvider>
      <HomeContent />
    </UnifiedFilterProvider>
  );
};

export default Home;
