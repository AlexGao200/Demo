import React, { useReducer, useEffect, useCallback, useRef, useState } from 'react';
import axiosInstance from '../axiosInstance';
import { useUserContext } from '../context/UserContext';
import { FaArrowUp, FaRedo } from 'react-icons/fa';
import '../styles/ChatBox.css';
import filterIcon from '../assets/images/filter.png';
import MessageList from './MessageList';
import { useMessageHandler } from '../hooks/useMessageHandler';
import { useInitialQuery } from '../hooks/useInitialQuery';
import QueryFilter from './filters_new/QueryFilter';
import Modal from './Modal';
import { ChatSession, Message } from '../types';
import { useUnifiedFilter } from '../context/UnifiedFilterContext';
import { Index } from '../types/FilterTypes';

const log = (level: 'info' | 'warn' | 'error', message: string, data?: unknown) => {
    const timestamp = new Date().toISOString();
    const logMessage = `[ChatBox] [${timestamp}] [${level.toUpperCase()}] ${message}`;
    switch (level) {
        case 'info':
            console.log(logMessage, data);
            break;
        case 'warn':
            console.warn(logMessage, data);
            break;
        case 'error':
            console.error(logMessage, data);
            break;
    }
};

interface ChatBoxProps {
    selectedChatSession: ChatSession | null;
    onTitleUpdate: (chatId: string, title: string) => void;
    initialQuery?: string;
    refreshChatSessions: () => void;
    isChangingChat: boolean;
}

interface ChatBoxState {
    messages: Message[];
    currentChatSessionId: string | null;
    showFilterOptions: boolean;
    isModalOpen: boolean;
    modalMessage: string;
}

type ChatBoxAction =
    | { type: 'SET_MESSAGES'; payload: Message[] | ((prevMessages: Message[]) => Message[]) }
    | { type: 'ADD_MESSAGE'; payload: Message }
    | { type: 'SET_CURRENT_CHAT_SESSION_ID'; payload: string | null }
    | { type: 'TOGGLE_FILTER_OPTIONS' }
    | { type: 'SET_MODAL_STATE'; payload: { isOpen: boolean; message: string } }
    | { type: 'UPDATE_CHAT_TITLE'; payload: { chatId: string; title: string } };

const chatBoxReducer = (state: ChatBoxState, action: ChatBoxAction): ChatBoxState => {
    log('info', `Reducer action: ${action.type}`, action);
    switch (action.type) {
        case 'SET_MESSAGES':
            return { ...state, messages: action.payload instanceof Function ? action.payload(state.messages) : action.payload };
        case 'ADD_MESSAGE':
            return { ...state, messages: [...state.messages, action.payload] };
        case 'SET_CURRENT_CHAT_SESSION_ID':
            return {
                ...state,
                currentChatSessionId: action.payload,
                messages: state.currentChatSessionId === action.payload ? state.messages : []
            };
        case 'TOGGLE_FILTER_OPTIONS':
            return { ...state, showFilterOptions: !state.showFilterOptions };
        case 'SET_MODAL_STATE':
            return { ...state, isModalOpen: action.payload.isOpen, modalMessage: action.payload.message };
        case 'UPDATE_CHAT_TITLE':
            return state;
        default:
            return state;
    }
};

const ChatBox: React.FC<ChatBoxProps> = ({
    selectedChatSession,
    onTitleUpdate,
    initialQuery,
    refreshChatSessions,
    isChangingChat,
}) => {
    log('info', 'ChatBox rendered', { selectedChatSession, initialQuery });
    const [initializedChats, setInitializedChats] = useState<Set<string>>(new Set());
    const [state, dispatch] = useReducer(chatBoxReducer, {
        messages: [],
        currentChatSessionId: selectedChatSession ? selectedChatSession.id : null,
        showFilterOptions: false,
        isModalOpen: false,
        modalMessage: '',
    });

    const initializationPromiseRef = useRef<Promise<void> | null>(null);
    const [isInitialized, setIsInitialized] = useState(false);
    const { user, guestToken } = useUserContext();
    const { state: filterState, dispatch: filterDispatch } = useUnifiedFilter();
    const messagesEndRef = useRef<HTMLDivElement | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    const setMessagesCallback = useCallback((messagesOrUpdater: Message[] | ((prevMessages: Message[]) => Message[])) => {
        dispatch({ type: 'SET_MESSAGES', payload: messagesOrUpdater });
    }, []);

    const { query, setQuery, handleSendMessage } = useMessageHandler({
        currentChatSessionId: state.currentChatSessionId,
        setMessages: setMessagesCallback,
        selectedIndices: filterState.query.indices.map((index: Index) => index.name),
        setModalMessage: (message) => dispatch({ type: 'SET_MODAL_STATE', payload: { isOpen: true, message } }),
        setIsModalOpen: (isOpen) => dispatch({ type: 'SET_MODAL_STATE', payload: { isOpen, message: state.modalMessage } }),
        filterDimensions: filterState.query.filters || {}
    });

    // Use the external useInitialQuery hook
    const hasProcessedInitialQuery = useInitialQuery(
        state.currentChatSessionId || '',
        initialQuery,
        handleSendMessage
    );

    const refreshGuestSession = async () => {
        log('info', 'Refreshing guest session');
        try {
            localStorage.removeItem('guest_token');
            const response = await axiosInstance.post('/create_guest_session');
            const newGuestToken = response.data.token;
            localStorage.setItem('guest_token', newGuestToken);
            log('info', 'Guest session refreshed successfully');
            return newGuestToken;
        } catch (error) {
            log('error', 'Failed to refresh guest session', { error });
            throw error;
        }
    };

    const handleGuestSessionError = useCallback(async (error: any): Promise<boolean> => {
        if (error?.response?.status === 403 && error?.response?.data?.message?.includes('Invalid guest session')) {
            log('warn', 'Invalid guest session detected, attempting refresh');
            try {
                await refreshGuestSession();
                return true;
            } catch (refreshError) {
                log('error', 'Failed to refresh session', { refreshError });
                return false;
            }
        }
        return false;
    }, []);

    const toggleFilterOptions = useCallback(() => {
        log('info', 'Toggling filter options');
        dispatch({ type: 'TOGGLE_FILTER_OPTIONS' });
    }, []);

    const fetchChatHistory = useCallback(async (chatId: string) => {
        log('info', 'Fetching chat history', { chatId });

        const fetchWithRetry = async (retryCount = 0) => {
            try {
                const token = localStorage.getItem('token') || localStorage.getItem('guest_token');
                const headers: Record<string, string> = { 'Authorization': `Bearer ${token}` };

                const response = await axiosInstance.get<Message[]>('/chat_history', {
                    params: { chat_id: chatId },
                    headers,
                });

                const fetchedMessages = response.data.map((msg: Message) => ({
                    ...msg,
                    cited_sections: msg.cited_sections
                        ? msg.cited_sections.map(cs => typeof cs === 'string' ? JSON.parse(cs) : cs)
                            .filter(cs => cs !== null && cs.title && cs.preview)
                        : undefined,
                }));

                log('info', 'Chat history fetched successfully', { messageCount: fetchedMessages.length });
                dispatch({ type: 'SET_MESSAGES', payload: fetchedMessages });
            } catch (error: any) {
                if (retryCount < 1 && await handleGuestSessionError(error)) {
                    return fetchWithRetry(retryCount + 1);
                }

                log('error', 'Error fetching chat history', { error });
                if (!guestToken && !localStorage.getItem('guest_token')) {
                    dispatch({ type: 'SET_MODAL_STATE', payload: { isOpen: true, message: 'An error occurred while fetching chat history. Please try again.' } });
                }
                throw error;
            }
        };

        return fetchWithRetry();
    }, [guestToken, handleGuestSessionError]);

    useEffect(() => {
        if (selectedChatSession && selectedChatSession.id !== state.currentChatSessionId) {
            log('info', 'Updating current chat session', { newSessionId: selectedChatSession.id });
            dispatch({ type: 'SET_CURRENT_CHAT_SESSION_ID', payload: selectedChatSession.id });

            if (!initializedChats.has(selectedChatSession.id)) {
                initializationPromiseRef.current = fetchChatHistory(selectedChatSession.id)
                    .then(() => {
                        setInitializedChats(prev => new Set([...prev, selectedChatSession.id]));
                        setIsInitialized(true);
                    })
                    .catch(error => {
                        console.error('Failed to initialize chat:', error);
                        setIsInitialized(false);
                        throw error;
                    });
            } else {
                setIsInitialized(true);
            }
        }
    }, [selectedChatSession, state.currentChatSessionId, fetchChatHistory, initializedChats]);

    useEffect(() => {
        return () => {
            setInitializedChats(new Set());
            setIsInitialized(false);
            setIsLoading(false);
        };
    }, []);

    useEffect(() => {
        if (messagesEndRef.current) {
            log('info', 'Scrolling to bottom of messages');
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [state.messages]);

    const handleQueryAbort = useCallback(() => {
        log('info', 'Query aborted');
        dispatch({ type: 'TOGGLE_FILTER_OPTIONS' });
    }, []);

    const closeModal = useCallback(() => {
        log('info', 'Closing modal');
        dispatch({ type: 'SET_MODAL_STATE', payload: { isOpen: false, message: '' } });
    }, []);

    const renderMessage = useCallback((message: Message) => {
        if (message.isError) {
            log('warn', 'Rendering error message', { messageId: message.id });
            return (
                <div className="error-message">
                    <p>{message.content}</p>
                    <button onClick={() => message.retry && message.retry()} className="retry-button">
                        <FaRedo /> Retry
                    </button>
                </div>
            );
        }
        return message.content;
    }, []);

    const handleSendMessageWithUpdates = useCallback(async (message: string) => {
        if (isChangingChat) {
            log('info', 'Chat changing, skipping message send');
            return;
        }

        if (!message.trim()) {
            log('info', 'Empty message, skipping');
            return;
        }

        if (!initializedChats.has(state.currentChatSessionId || "")) {
            log('warn', 'Chat not initialized, skipping message');
            return;
        }

        if (user?.subscription_status === 'inactive' && !user?.is_admin) {
            log('warn', 'Inactive subscription, cannot send message');
            dispatch({ type: 'SET_MODAL_STATE', payload: { isOpen: true, message: 'Please renew your subscription to continue.' } });
            return;
        }

        setIsLoading(true);
        try {
            await handleSendMessage(message);
            log('info', 'Message sent successfully');
            refreshChatSessions();

            if (state.messages.length === 0 && state.currentChatSessionId) {
                const newTitle = message.slice(0, 50) + (message.length > 50 ? '...' : '');
                log('info', 'Updating chat title', { newTitle });
                onTitleUpdate(state.currentChatSessionId, newTitle);
            }
        } catch (error) {
            log('error', 'Error sending message', { error });
            dispatch({ type: 'SET_MODAL_STATE', payload: { isOpen: true, message: 'An error occurred while sending the message. Please try again.' } });
        } finally {
            setIsLoading(false);
        }
    }, [user, state.currentChatSessionId, state.messages.length, handleSendMessage, refreshChatSessions, onTitleUpdate, isChangingChat, initializedChats]);

    if (!user && !guestToken && !localStorage.getItem('guest_token')) {
        log('warn', 'No user or guest token found');
        return <div>Please log in to use the chat.</div>;
    }

    return (
        <div className="chat-box-container">
            <MessageList
                messages={state.messages}
                handleCopy={(content) => {
                    log('info', 'Copying message content');
                    navigator.clipboard.writeText(content).catch(err => {
                        log('error', 'Error copying text', { error: err });
                        console.error('Error copying text:', err);
                    });
                }}
                currentChatId={state.currentChatSessionId || ""}
            />
            <div className="input-container-chat">
                <div className="query-input-wrapper">
                    <img src={filterIcon} alt="Filter" className="filter-icon" onClick={toggleFilterOptions} />
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyUp={(e: React.KeyboardEvent<HTMLInputElement>) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                log('info', 'Sending message via Enter key');
                                handleSendMessageWithUpdates(query);
                                setQuery('');
                            }
                        }}
                        className="input"
                    />
                    <button
                        onClick={() => {
                            log('info', 'Sending message via button click');
                            handleSendMessageWithUpdates(query);
                            setQuery('');
                        }}
                        className="send-button"
                        disabled={isLoading}
                    >

                        <FaArrowUp className="send-icon" />
                    </button>
                </div>
            </div>
            {state.showFilterOptions && (
                <QueryFilter
                    onAbort={handleQueryAbort}
                    onComplete={(filters) => {
                        log('info', 'Filters applied', { filters });
                        filterDispatch({ type: 'SET_QUERY_FILTERS', payload: filters });
                        dispatch({ type: 'TOGGLE_FILTER_OPTIONS' });
                    }}
                />
            )}
            <Modal isOpen={state.isModalOpen} onClose={closeModal} message={state.modalMessage} />
            <div ref={messagesEndRef} />
        </div>
    );
};

export default ChatBox;
