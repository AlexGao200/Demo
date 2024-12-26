export interface UserContextType {
    user: User | null;
    messageCount: number;
    selectedOrganization: string | null;
    setSelectedOrganization: (organizationId: string) => void;
    login: (userData: Partial<User>, token: string, refreshToken: string) => void;
    logout: () => void;
    loading: boolean;
    incrementMessageCount: () => void;
    guestToken?: string | null;
    setUser: (user: User | null) => void;
    setGuestSession: (sessionId: string) => void;
}

export interface User {
    user_id: string;
    email: string;
    personal_index: string;
    organization_indices?: string[];
    first_name: string;
    last_name: string;
    id: string;
    is_superadmin: boolean;
    subscription_status: 'active' | 'inactive';
    initial_organization?: string;
    exp: number;
    [key: string]: unknown; // For any additional properties in the decoded token
}
