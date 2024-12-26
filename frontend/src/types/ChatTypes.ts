import React from 'react'

export interface Message {
    id: string;
    sender: 'user' | 'ai';
    content: string;
    isError?: boolean;
    isStreaming?: boolean;
    retry?: () => void;
    cited_sections?: CitedSection[];
    timestamp?: string;
}

export interface ChatSession {
    id: string;
    createdAt: string;
    title: string;
    messages: Message[];
}

export interface ChatSessionsProps {
    sessions: ChatSession[];
    onSelectChat: (chat: ChatSession) => void;
    onNewChat: () => void;
}

export interface Chat {
    id: string;
    title: string;
    createdAt: string;
    messages: Message[];
}

export interface LocationState {
    initialQuery?: string;
    selectedIndices?: string[];
}

export interface CitedSection {
    text: string;
    file_url: string;
    title: string;
    section_title: string;
    pages: number[];
    index_names: string[];
    organization: string;
    filter_dimensions: Record<string, any>;
    preview: string;
    index_display_name?: string;
    nominal_creator_name?: string;
    highlighted_file_url?: string;
}

export interface UseMessageHandlerProps {
    currentChatSessionId: string | null;
    setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
    selectedIndices: string[];
    setModalMessage: (message: string) => void;
    setIsModalOpen: (isOpen: boolean) => void;
    filterDimensions: { [key: string]: string[] };
}

export interface UseMessageHandlerReturn {
    query: string;
    setQuery: React.Dispatch<React.SetStateAction<string>>;
    handleSendMessage: (initialQuery?: string, initialIndices?: string[]) => Promise<void>;
}
