import { useState, useEffect, useRef } from 'react';

const STORAGE_PREFIX = 'initialQueryProcessed_';
const MAX_STORAGE_AGE = 30 * 24 * 60 * 60 * 1000; // 30 days in milliseconds
const QUERY_TIMEOUT = 60000; // 30 seconds to match useMessageHandler timeout

const cleanupStorage = () => {
  const now = Date.now();
  Object.keys(localStorage).forEach(key => {
    if (key.startsWith(STORAGE_PREFIX)) {
      const timestamp = parseInt(localStorage.getItem(key) || '0', 10);
      if (now - timestamp > MAX_STORAGE_AGE) {
        localStorage.removeItem(key);
      }
    }
  });
};

export const useInitialQuery = (
  currentChatId: string,
  initialQuery: string | undefined,
  handleSendMessage: (query: string) => Promise<void>
) => {
  const [isInitialQueryProcessed, setIsInitialQueryProcessed] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const handleSendMessageRef = useRef(handleSendMessage);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    handleSendMessageRef.current = handleSendMessage;
  }, [handleSendMessage]);

  useEffect(() => {
    // Cleanup function
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  useEffect(() => {
    cleanupStorage();

    const processInitialQuery = async () => {
      const storageKey = `${STORAGE_PREFIX}${currentChatId}`;
      const isProcessed = localStorage.getItem(storageKey);

      if (initialQuery && !isProcessed && currentChatId && !isProcessing) {
        console.log("Processing initial query:", initialQuery, "for chat:", currentChatId);
        setIsProcessing(true);

        try {
          // Create new AbortController for this attempt
          abortControllerRef.current = new AbortController();

          const timeoutId = setTimeout(() => {
            if (abortControllerRef.current) {
              abortControllerRef.current.abort();
            }
          }, QUERY_TIMEOUT);

          await Promise.race([
            handleSendMessageRef.current(initialQuery),
            new Promise((_, reject) => {
              abortControllerRef.current?.signal.addEventListener('abort', () => {
                reject(new Error('Initial query timed out or was aborted'));
              });
            })
          ]);

          clearTimeout(timeoutId);
          localStorage.setItem(storageKey, Date.now().toString());
          console.log("Initial query processed successfully");
        } catch (error) {
          console.error("Error processing initial query:", error);
          // Only mark as processed if it wasn't aborted
          if (!(error instanceof Error && error.name === 'AbortError')) {
            localStorage.setItem(storageKey, Date.now().toString());
          }
        } finally {
          setIsProcessing(false);
          setIsInitialQueryProcessed(true);
          abortControllerRef.current = null;
        }
      } else {
        setIsInitialQueryProcessed(true);
      }
    };

    processInitialQuery();
  }, [currentChatId, initialQuery, isProcessing]);

  return {
    isInitialQueryProcessed,
    isProcessing
  };
};
