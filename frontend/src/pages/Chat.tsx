import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import ChatBox from '../components/ChatBox';
import ChatSessions from '../components/ChatSessions';
import axiosInstance from '../axiosInstance';
import AppHeader from '../components/AppHeader';
import '../styles/Chat.css';
import { ChatSession, LocationState } from '../types';
import { UnifiedFilterProvider, useUnifiedFilter } from '../context/UnifiedFilterContext';

const ChatContent: React.FC = () => {
 const { id } = useParams<{ id: string }>();
 const navigate = useNavigate();
 const location = useLocation();
 const [searchParams] = useSearchParams();
 const { initialQuery } = (location.state as LocationState) || {};
 const [sessions, setSessions] = useState<ChatSession[]>([]);
 const [selectedChatSession, setSelectedChatSession] = useState<ChatSession | null>(null);
 const [isInitialized, setIsInitialized] = useState(false);
 const { state: filterState } = useUnifiedFilter();

 const userTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

 const [isChangingChat, setIsChangingChat] = useState(false);

 useEffect(() => {
   const setupGuestSession = async () => {
     const sessionId = searchParams.get('session');
     if (sessionId) {
       console.log('Setting up guest session from URL:', sessionId);
       try {
         // Don't try to create a new session, just initialize
         setIsInitialized(true);
         // Don't remove the session parameter from URL
       } catch (error) {
         console.error('Error setting up guest session:', error);
       }
     } else {
       setIsInitialized(true);
     }
   };

   setupGuestSession();
 }, [searchParams]);

 const convertToLocalTime = (dateString: string, timeZone: string): Date => {
   const dateUTC = new Date(dateString);
   return new Date(dateUTC.toLocaleString('en-US', { timeZone }));
 };

 const fetchChatSessions = useCallback(async (): Promise<void> => {
   // Get session from URL or stored token
   const urlSession = searchParams.get('session');
   const token = urlSession || localStorage.getItem('token') || localStorage.getItem('guest_token');

   if (!token) {
     console.log('No authentication token found');
     return;
   }

   try {
     const response = await axiosInstance.get<ChatSession[]>('/chat_sessions');

     const updatedSessions = response.data.map(chat => ({
       ...chat,
       createdAt: convertToLocalTime(chat.createdAt, userTimeZone).toISOString(),
     }));

     setSessions(updatedSessions);

     if (id && !selectedChatSession) {
       const matchingChat = updatedSessions.find(chat => chat.id === id);
       if (matchingChat) {
         setSelectedChatSession(matchingChat);
       }
     }
   } catch (error) {
     console.error('Error fetching chat sessions:', error);
   }
 }, [userTimeZone, id, selectedChatSession, searchParams]);

 useEffect(() => {
   if (isInitialized) {
     fetchChatSessions();
   }
 }, [fetchChatSessions, isInitialized]);

 useEffect(() => {
   if (isInitialized && id) {
     const fetchChat = async (): Promise<void> => {
       try {
         console.log('Fetching chat with ID:', id);
         const response = await axiosInstance.get<ChatSession>(`/chat/${id}`);
         const chat = response.data;
         const localCreatedAt = convertToLocalTime(chat.createdAt, userTimeZone);
         setSelectedChatSession({ ...chat, createdAt: localCreatedAt.toISOString() });
       } catch (error) {
         console.error('Error fetching chat:', error);
         navigate('/');
       }
     };

     fetchChat();
   }
 }, [id, userTimeZone, isInitialized, navigate]);

// Update handleSelectChat
const handleSelectChat = async (chat: ChatSession): Promise<void> => {
   setIsChangingChat(true);
   setSelectedChatSession(chat);

   await new Promise(resolve => setTimeout(resolve, 100));


   const sessionId = searchParams.get('session');
   const chatUrl = sessionId ? `/chat/${chat.id}?session=${sessionId}` : `/chat/${chat.id}`;
   navigate(chatUrl);

   // Give time for cleanup
   await new Promise(resolve => setTimeout(resolve, 100));
   setIsChangingChat(false);
};

 const handleNewChat = async (): Promise<void> => {
   const urlSession = searchParams.get('session');
   if (urlSession || localStorage.getItem('guest_token')) {
     console.warn('Guest users cannot create new chats');
     return;
   }

   try {
     const response = await axiosInstance.post<{ chat_id: string; title?: string }>('/chat', {
       time_zone: userTimeZone,
       indices: filterState.query.indices.map(index => index.name),
       filters: filterState.query.filters || {},
     });

     const newChatId = response.data.chat_id;
     const localCreatedAt = new Date().toLocaleString('en-US', { timeZone: userTimeZone });

     const newChat = {
       id: newChatId,
       createdAt: localCreatedAt,
       title: response.data.title || 'Untitled Chat',
       messages: [],
     };

     setSessions(prevSessions => [...prevSessions, newChat]);
     setSelectedChatSession(newChat);
     navigate(`/chat/${newChatId}`);
     await fetchChatSessions();
   } catch (error) {
     console.error('Error starting new chat:', error);
   }
 };

 const handleTitleUpdate = (chatId: string, newTitle: string): void => {
   setSessions(prevSessions =>
     prevSessions.map(chat =>
       chat.id === chatId ? { ...chat, title: newTitle } : chat
     )
   );

   if (selectedChatSession?.id === chatId) {
     setSelectedChatSession(prevChat =>
       prevChat ? { ...prevChat, title: newTitle } : null
     );
   }

   fetchChatSessions();
 };

 // Update isGuestMode to check URL session as well
 const isGuestMode = Boolean(searchParams.get('session')) || Boolean(localStorage.getItem('guest_token'));

 return (
   <div className="container">
     <AppHeader />
     <div className="content">
       {!isGuestMode && (
         <div className="chat-sessions-container">
           <ChatSessions
             sessions={sessions}
             onNewChat={handleNewChat}
             onSelectChat={handleSelectChat}
           />
         </div>
       )}
       <div className={`chat-box-container ${isGuestMode ? 'full-width' : ''}`}>
       <ChatBox
          selectedChatSession={selectedChatSession}
          onTitleUpdate={handleTitleUpdate}
          refreshChatSessions={fetchChatSessions}
          initialQuery={initialQuery}
          isChangingChat={isChangingChat}  // Add this prop
        />
       </div>
     </div>
   </div>
 );
};

const Chat: React.FC = () => {
 return (
   <UnifiedFilterProvider>
     <ChatContent />
   </UnifiedFilterProvider>
 );
};

export default Chat;
