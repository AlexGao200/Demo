import React, { useRef, useEffect, useState } from 'react';
import { format } from 'date-fns';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

import { useThemeContext } from '../context/ThemeContext';
import logo from '../assets/images/logo3.png';
import copyIcon from '../assets/images/copy.png';
import LoadingAnimation from './LoadingAnimation';
import { Message, CitedSection } from '../types';
import '../styles/markdown.css';

marked.setOptions({
  breaks: true,
  gfm: true,
});

const log = (level: 'info' | 'warn' | 'error', message: string, data?: unknown) => {
  const timestamp = new Date().toISOString();
  const logMessage = `[MessageList] [${timestamp}] [${level.toUpperCase()}] ${message}`;

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

export interface MessageListProps {
  messages: Message[];
  handleCopy: (content: string) => void;
  currentChatId: string;
  renderMessage?: (msg: Message) => React.ReactNode;
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  handleCopy,
  currentChatId,
  renderMessage,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { theme } = useThemeContext();

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  useEffect(() => {
    messages.forEach((msg, index) => {
      const hasCitations = Array.isArray(msg.cited_sections) && msg.cited_sections.length > 0;
      log('info', `Message ${index}`, {
        sender: msg.sender,
        contentLength: msg.content.length,
        hasCitations,
        citationCount: msg.cited_sections?.length || 0
      });
    });
  }, [messages]);

  const handleLinkClick = (event: React.MouseEvent<Element, MouseEvent>) => {
    const target = event.target as HTMLAnchorElement;
    if (target.tagName === 'A' && target.href) {
      event.preventDefault();
      window.open(target.href, '_blank');
    }
  };

  const formatDate = (dateString: string): string => {
    if (!dateString) return 'Invalid Date';
    try {
      const date = new Date(dateString);
      return isNaN(date.getTime()) ? 'Invalid Date' : format(date, 'MMM do, yyyy');
    } catch (error) {
      console.error('Error formatting date:', error);
      return 'Invalid Date';
    }
  };

  const renderSanitizedMarkdown = (content: string) => {
    const rawMarkup = marked(content) as string;
    const sanitizedMarkup = DOMPurify.sanitize(rawMarkup);
    return { __html: sanitizedMarkup };
  };

  return (
    <div className="messages-container" onClick={handleLinkClick}>
      {messages.map((msg, index) => (
        <MessageItem
          key={`${msg.id}-${index}`}
          msg={msg}
          handleCopy={handleCopy}
          currentChatId={currentChatId}
          formatDate={formatDate}
          theme={theme}
          renderSanitizedMarkdown={renderSanitizedMarkdown}
          renderMessage={renderMessage}
        />
      ))}
      {messages[messages.length - 1]?.sender === 'ai' && messages[messages.length - 1]?.isStreaming && (
        <div style={loadingContainerStyle}>
          <LoadingAnimation />
          <p style={loadingMessageStyle}>Response being generated</p>
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>
  );
};

interface MessageItemProps {
  msg: Message;
  handleCopy: (content: string) => void;
  currentChatId: string;
  formatDate: (dateString: string) => string;
  renderMessage?: (msg: Message) => React.ReactNode;
  theme: string;
  renderSanitizedMarkdown: (content: string) => { __html: string };
}

const MessageItem: React.FC<MessageItemProps> = ({
  msg,
  handleCopy,
  currentChatId,
  formatDate,
  renderMessage,
  theme,
  renderSanitizedMarkdown,
}) => {
  const hasCitations = Array.isArray(msg.cited_sections) && msg.cited_sections.length > 0;

  useEffect(() => {
    log('info', 'Rendering MessageItem', {
      sender: msg.sender,
      contentLength: msg.content.length,
      hasCitations,
      citationCount: msg.cited_sections?.length || 0
    });
  }, [msg, hasCitations]);

  return (
    <div className={msg.sender === 'user' ? 'user-message-container' : 'ai-message-container'}>
      {msg.sender === 'ai' && <img src={logo} alt="Logo" className="logo" />}
      <div className={msg.sender === 'user' ? 'user-message' : 'ai-message'} style={{ position: 'relative' }}>
        {msg.sender === 'ai' && (
          <img
            src={copyIcon}
            alt="Copy"
            style={{
              filter: theme === 'dark' ? 'invert(1)' : 'none',
              width: '16px',
              height: '16px',
              cursor: 'pointer',
              position: 'absolute',
              right: '10px',
              top: '10px',
            }}
            onClick={() => handleCopy(msg.content)}
          />
        )}
        {renderMessage ? renderMessage(msg) : (
          <div
            className={`${msg.sender === 'user' ? '' : 'ai-response'} ${msg.sender === 'ai' ? 'markdown-content' : ''}`}
            dangerouslySetInnerHTML={renderSanitizedMarkdown(msg.content)}
          />
        )}
        {hasCitations && msg.cited_sections && msg.cited_sections.map((section, sectionIndex) => (
          <CitationSection
            key={`${msg.id}-citation-${sectionIndex}`}
            section={section}
            sectionIndex={sectionIndex}
            currentChatId={currentChatId}
          />
        ))}
        {msg.sender !== 'user' && (
          <p><strong></strong> {msg.timestamp ? formatDate(msg.timestamp) : 'Invalid Date'}</p>
        )}
      </div>
    </div>
  );
};

interface CitationSectionProps {
  section: CitedSection;
  sectionIndex: number;
  currentChatId: string;
}

const CitationSection: React.FC<CitationSectionProps> = ({
  section,
  sectionIndex
}) => {
  if (!section || !section.preview) {
    log('warn', 'Invalid citation section', { sectionIndex, section });
    return null;
  }

  const { preview, pages, title, section_title, index_display_name, nominal_creator_name, highlighted_file_url } = section;
  const pageNumber = pages && pages.length > 0 ? pages[0] : 'N/A';

  log('info', 'Rendering CitationSection', {
    sectionIndex,
    title,
    sectionTitle: section_title,
    pageNumber,
    textLength: preview.length
  });

  return (
    <div className="citation-section">
      <p className="citation-title">
        <strong>{sectionIndex + 1}.</strong> {section_title || 'Untitled Section'} from <em>{title || 'Untitled Document'}</em>, page {pageNumber}:
      </p>
      <pre className="pre citation-body">
        <a
          href={highlighted_file_url}
          target="_blank"
          rel="noopener noreferrer"
          className="pdf-link"
          data-page-number={pageNumber}
        >
          (Link)
        </a>
        {': ' + preview}
      </pre>
      <p className="index-info">
        {nominal_creator_name || index_display_name}
      </p>
    </div>
  );
};

const loadingContainerStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100%',
  textAlign: 'center',
};

const loadingMessageStyle: React.CSSProperties = {
  marginTop: '10px',
  color: '#333',
  fontSize: '14px',
  fontFamily: 'Inter, sans-serif',
  textAlign: 'center',
};

export default MessageList;
