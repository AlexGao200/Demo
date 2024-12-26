import { useState, useCallback, useRef, useEffect } from 'react';
import axiosInstance from '../axiosInstance';
import { CitedSection, UseMessageHandlerProps, UseMessageHandlerReturn } from '../types/ChatTypes';
import { Index } from '../types/FilterTypes';

interface EventData {
  type: 'content' | 'citations' | 'error' | 'done';
  text?: string;
  message?: string;
  data?: {
    cited_sections?: CitedSection[];
  };
}

const TIMEOUT_DURATION = 30000; // 30 seconds timeout
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 second

const log = (level: 'info' | 'warn' | 'error', message: string, data?: unknown) => {
  const timestamp = new Date().toISOString();
  const logMessage = `[${timestamp}] [${level.toUpperCase()}] ${message}`;

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

const parseCitedSections = (sections: any[]): CitedSection[] => {
  return sections
    .map(cs => {
      try {
        return typeof cs === 'string' ? JSON.parse(cs) : cs;
      } catch (e) {
        console.error('Error parsing cited section:', e);
        return null;
      }
    })
    .filter((cs): cs is CitedSection => cs !== null && cs.title && cs.preview);
};

export const useMessageHandler = ({
  currentChatSessionId,
  setMessages,
  selectedIndices,
  setModalMessage,
  setIsModalOpen,
  filterDimensions
}: UseMessageHandlerProps): UseMessageHandlerReturn => {
  const [query, setQuery] = useState<string>('');
  const messageCounterRef = useRef<number>(0);
  const activeController = useRef<AbortController | null>(null);
  const activeRequestRef = useRef<{ chatId: string; timestamp: number } | null>(null);
  const pendingContentRef = useRef<string>('');
  const citedSectionsRef = useRef<CitedSection[]>([]);
  const currentMessageIdRef = useRef<string | null>(null);

  const getMessageId = useCallback(() => {
    const timestamp = Date.now();
    const counter = messageCounterRef.current++;
    return `${timestamp}-${counter}`;
  }, []);

  const abortActiveRequest = useCallback(() => {
    if (activeController.current) {
      activeController.current.abort();
      activeController.current = null;
    }
    activeRequestRef.current = null;
  }, []);

  const fetchWithRetry = useCallback(async (url: string, options: RequestInit, retries = MAX_RETRIES): Promise<Response> => {
    try {
      log('info', `Attempting fetch to ${url}`, { retries });
      const response = await fetch(url, options);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      log('info', `Fetch successful`, { url, status: response.status });
      return response;
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        log('info', 'Request aborted', { url });
        throw error;
      }

      if (retries > 0) {
        log('warn', `Fetch failed, retrying...`, { url, error, retriesLeft: retries - 1 });
        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
        return fetchWithRetry(url, options, retries - 1);
      } else {
        log('error', `Fetch failed after all retries`, { url, error });
        throw error;
      }
    }
  }, []);

  const updateMessage = useCallback((messageId: string, updates: Partial<{
    content: string;
    cited_sections: CitedSection[];
    isStreaming: boolean;
  }>) => {
    log('info', 'Updating message', { messageId, updates });
    setMessages((prevMessages) =>
      prevMessages.map((msg) =>
        msg.id === messageId
          ? {
              ...msg,
              ...updates,
              cited_sections: updates.cited_sections || msg.cited_sections,
              timestamp: new Date().toISOString(),
            }
          : msg
      )
    );
  }, [setMessages]);

  const handleSendMessage = useCallback(async (initialQuery?: string, initialIndices?: string[]) => {
    log('info', "handleSendMessage called", {
      initialQuery,
      initialIndices: initialIndices || selectedIndices,
      currentChatId: currentChatSessionId
    });

    if (!currentChatSessionId) {
      log('error', 'Error: Missing chat information.');
      return;
    }

    // Reset refs for new message
    pendingContentRef.current = '';
    citedSectionsRef.current = [];

    // Abort any existing request
    abortActiveRequest();

    // Create new controller for this request
    activeController.current = new AbortController();
    activeRequestRef.current = {
      chatId: currentChatSessionId,
      timestamp: Date.now()
    };

    const queryToSend = initialQuery || query;
    const indicesToUse = initialIndices || selectedIndices || [];
    const requestChatId = currentChatSessionId;

    const userMessageId = getMessageId();
    const aiMessageId = getMessageId();
    currentMessageIdRef.current = aiMessageId;

    try {
      if (indicesToUse.length === 0) {
        log('info', 'Fetching indices');
        const response = await axiosInstance.get<{ indices: Index[] }>(`/user/indices`);
        const indices: Index[] = response.data.indices;
        indicesToUse.push(...indices.map(index => index.name));
        log('info', 'Indices fetched successfully', { indices: indicesToUse });
      }

      // Check if the chat has changed during indices fetch
      if (requestChatId !== currentChatSessionId) {
        log('info', 'Chat changed during request, aborting');
        return;
      }

      log('info', 'Setting initial messages', { userMessageId, aiMessageId });
      setMessages((prevMessages) => [
        ...prevMessages,
        {
          id: userMessageId,
          sender: 'user',
          content: queryToSend,
          timestamp: new Date().toISOString(),
        },
        {
          id: aiMessageId,
          sender: 'ai',
          content: '',
          cited_sections: [],
          isStreaming: true,
          timestamp: new Date().toISOString(),
        },
      ]);

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      const token = localStorage.getItem('token') || localStorage.getItem('guest_token');
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const timeoutId = setTimeout(() => {
        if (activeController.current) {
          activeController.current.abort();
          log('warn', 'Request timed out', { timeout: TIMEOUT_DURATION });
        }
      }, TIMEOUT_DURATION);

      log('info', 'Sending request to /api/ask_stream', {
        query: queryToSend,
        chat_id: requestChatId,
        indices: indicesToUse,
        filter_dimensions: filterDimensions
      });

      const response = await fetchWithRetry(
        `${axiosInstance.defaults.baseURL || ''}/ask_stream`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({
            query: queryToSend,
            chat_id: requestChatId,
            indices: indicesToUse,
            filter_dimensions: filterDimensions
          }),
          signal: activeController.current?.signal,
        }
      );

      clearTimeout(timeoutId);

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Failed to get response reader');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      const processEventData = (eventData: EventData) => {
        // Skip processing if chat has changed
        if (requestChatId !== currentChatSessionId || aiMessageId !== currentMessageIdRef.current) {
          return;
        }

        log('info', 'Processing event data', { eventType: eventData.type });
        switch (eventData.type) {
          case 'content':
            if (eventData.text) {
              pendingContentRef.current += eventData.text;
              log('info', 'Updating message with new content', {
                aiMessageId,
                contentLength: pendingContentRef.current.length,
                hasCitations: citedSectionsRef.current.length > 0
              });
              updateMessage(aiMessageId, {
                content: pendingContentRef.current,
                cited_sections: citedSectionsRef.current,
                isStreaming: true
              });
            }
            break;
          case 'citations':
            if (eventData.cited_sections) {
              citedSectionsRef.current = parseCitedSections(eventData.cited_sections);
              log('info', 'Received and parsed citations', {
                citationsCount: citedSectionsRef.current.length,
                currentContent: pendingContentRef.current.length
              });
              // Force a state update with the new citations
              setMessages((prevMessages) =>
                prevMessages.map((msg) =>
                  msg.id === aiMessageId
                    ? {
                        ...msg,
                        content: pendingContentRef.current,
                        cited_sections: citedSectionsRef.current,
                        isStreaming: true,
                        timestamp: new Date().toISOString(),
                      }
                    : msg
                )
              );
            }
            break;
          case 'error':
            log('error', 'Received error event', { errorMessage: eventData.message });
            throw new Error(eventData.message || "An error occurred with no message.");
          case 'done':
            log('info', 'Received done event, updating message', {
              aiMessageId,
              finalContentLength: pendingContentRef.current.length,
              finalCitationsCount: citedSectionsRef.current.length
            });
            // Force a final state update with all content and citations
            setMessages((prevMessages) =>
              prevMessages.map((msg) =>
                msg.id === aiMessageId
                  ? {
                      ...msg,
                      content: pendingContentRef.current,
                      cited_sections: citedSectionsRef.current,
                      isStreaming: false,
                      timestamp: new Date().toISOString(),
                    }
                  : msg
              )
            );
            break;
          default:
            log('warn', `Unhandled event type: ${(eventData as { type: string }).type}`);
            break;
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          log('info', 'Stream reading completed');
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const eventData = JSON.parse(line.slice(6)) as EventData;
              processEventData(eventData);
            } catch (error) {
              log('error', 'Error parsing event data', { error, rawData: line.slice(6) });
            }
          }
        }
      }

      setQuery('');
      log('info', 'Message processing completed successfully');
    } catch (error: unknown) {
      if (error instanceof Error && error.name === 'AbortError') {
        log('info', 'Request aborted, skipping error handling');
        return;
      }

      log('error', 'Error sending message', { error });

      let errorMessage = 'An unknown error occurred. Please try again.';
      if (error instanceof Error) {
        errorMessage = `An error occurred: ${error.message}`;
      }

      setMessages((prevMessages) =>
        prevMessages.map((msg) =>
          msg.id === aiMessageId
            ? {
                ...msg,
                content: errorMessage,
                isError: true,
                isStreaming: false,
                timestamp: new Date().toISOString(),
                retry: () => handleSendMessage(queryToSend, indicesToUse),
              }
            : msg
        )
      );

      setModalMessage(errorMessage);
      setIsModalOpen(true);
    } finally {
      if (activeRequestRef.current?.chatId === requestChatId) {
        activeController.current = null;
        activeRequestRef.current = null;
      }
    }
  }, [
    currentChatSessionId,
    query,
    selectedIndices,
    setMessages,
    filterDimensions,
    setModalMessage,
    setIsModalOpen,
    getMessageId,
    fetchWithRetry,
    abortActiveRequest,
    updateMessage
  ]);

  // Cleanup on chat change or unmount
  useEffect(() => {
    messageCounterRef.current = 0;
    pendingContentRef.current = '';
    citedSectionsRef.current = [];
    currentMessageIdRef.current = null;
    log('info', 'Message counter and refs reset', { chatSessionId: currentChatSessionId });

    return () => {
      abortActiveRequest();
    };
  }, [currentChatSessionId, abortActiveRequest]);

  return {
    query,
    setQuery,
    handleSendMessage,
  };
};
