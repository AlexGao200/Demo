import React, { createContext, useState, useEffect, useContext, useCallback, useRef } from 'react';
import { jwtDecode } from 'jwt-decode';
import axiosInstance from '../axiosInstance';
import { AxiosError } from 'axios';
import { User, UserContextType } from '../types';

export const UserContext = createContext<UserContextType | undefined>(undefined);

interface UserProviderProps {
  children: React.ReactNode;
}

export const useUserContext = (): UserContextType => {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error('useUserContext must be used within a UserProvider');
  }
  return context;
};

export const UserProvider: React.FC<UserProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [messageCount, setMessageCount] = useState<number>(0);
  const [selectedOrganization, setSelectedOrganization] = useState<string | null>(null);
  const [guestToken, setGuestToken] = useState<string | null>(null);
  const refreshingRef = useRef(false);

  const logout = useCallback(() => {
    console.log("Logging out...");
    setUser(null);
    setGuestToken(null);
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('guest_token');
    delete axiosInstance.defaults.headers.common['Authorization'];
  }, []);

  const setInitialOrganization = useCallback(
    (initialOrganization: string | undefined) => {
      if (initialOrganization) {
        console.log(`Setting initial organization from token: ${initialOrganization}`);
        setSelectedOrganization(initialOrganization);
      } else {
        console.log("No initial organization found in the token.");
        setSelectedOrganization(null);
      }
    },
    []
  );

  const setGuestSession = useCallback((sessionId: string) => {
    console.log("Setting guest session:", sessionId);
    setGuestToken(sessionId);
    localStorage.setItem('guest_token', sessionId);
    axiosInstance.defaults.headers.common["Authorization"] = `Bearer ${sessionId}`;

    // Clear any existing user data
    setUser(null);
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
  }, []);

  const createGuestSession = async () => {
    try {
      console.log("Creating guest session...");
      const response = await axiosInstance.post("/auth/refresh_token", {});
      const { access_token } = response.data;

      if (access_token) {
        console.log("Guest token received:", access_token);
        setGuestSession(access_token);
      } else {
        console.error("No access token received for guest session");
      }
    } catch (error) {
      console.error("Error creating guest session:", error);
    }
  };

  const refreshAccessToken = useCallback(async () => {
    if (refreshingRef.current) {
      console.log("Refresh token request is already in progress.");
      return;
    }

    try {
      refreshingRef.current = true;
      console.log("Attempting to refresh access token...");
      const refreshToken = localStorage.getItem("refresh_token");

      // Debug logs for token state
      console.log("Current stored tokens:", {
        token: localStorage.getItem("token"),
        refreshToken: refreshToken,
        guestToken: localStorage.getItem("guest_token")
      });

      if (refreshToken) {
        try {
          const decodedRefresh = jwtDecode(refreshToken);
          console.log("Decoded refresh token:", decodedRefresh);
        } catch (e) {
          console.log("Failed to decode refresh token:", e);
        }
      }

      if (!refreshToken) {
        console.log("No refresh token available, creating guest session");
        await createGuestSession();
        return;
      }

      const response = await axiosInstance.post("/auth/refresh_token", {
        refresh_token: refreshToken,
      });

      const { access_token, user: updatedUserData, is_guest } = response.data;
      console.log("Token refresh response:", { access_token, is_guest });

      if (!access_token) {
        throw new Error("No access token received from server");
      }

      if (is_guest) {
        setGuestToken(access_token);
        localStorage.setItem('guest_token', access_token);
        setUser(null);
      } else {
        localStorage.setItem("token", access_token);
        setUser(updatedUserData);
        setInitialOrganization(updatedUserData.initial_organization);
      }

      axiosInstance.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;

    } catch (error) {
      console.error("Error refreshing token:", error);
      if (error instanceof AxiosError && error.response?.status === 401) {
        console.log("Refresh token is invalid or expired. Creating guest session.");
        await createGuestSession();
      }
    } finally {
      refreshingRef.current = false;
    }
  }, [setInitialOrganization, setGuestSession]);

  const handleOrganizationChange = useCallback(async (organizationId: string) => {
    try {
      console.log(`Organization changed to: ${organizationId}`);
      setSelectedOrganization(organizationId);

      if (user?.id) {
        const response = await axiosInstance.post(`/user/${user.id}/set_initial_organization`, {
          organization_id: organizationId,
        });
        console.log('Organization updated on backend:', response.data.message);

        await refreshAccessToken();
      }
    } catch (error) {
      console.error("Error updating organization:", error);
    }
  }, [refreshAccessToken, user]);

  useEffect(() => {
    if (selectedOrganization && user) {
      handleOrganizationChange(selectedOrganization);
    }
  }, [selectedOrganization, handleOrganizationChange, user]);

  const isTokenExpiringSoon = (token: string): boolean => {
    try {
      const decodedToken = jwtDecode<User>(token);
      const expirationTime = decodedToken.exp * 1000;
      const now = Date.now();
      const expiringSoon = expirationTime - now < 5 * 60 * 1000;
      console.log(`Token expiring soon? ${expiringSoon}`);
      return expiringSoon;
    } catch (error) {
      console.error("Error checking token expiration:", error);
      return true;
    }
  };

  useEffect(() => {
    console.log("Initializing user session...");
    const token = localStorage.getItem('token');
    const guestTokenFromStorage = localStorage.getItem('guest_token');

    const initializeSession = async () => {
      if (token) {
        try {
          console.log("Found user token:", token);
          const decodedUser = jwtDecode<User>(token);

          if (decodedUser.exp * 1000 < Date.now()) {
            console.log("Token expired, refreshing...");
            await refreshAccessToken();
          } else {
            setUser(decodedUser);
            axiosInstance.defaults.headers.common['Authorization'] = `Bearer ${token}`;
            setInitialOrganization(decodedUser.initial_organization);

            if (isTokenExpiringSoon(token)) {
              await refreshAccessToken();
            }
          }
        } catch (error) {
          console.error("Error during token handling:", error);
          await createGuestSession();
        }
      } else if (guestTokenFromStorage) {
        console.log("Found guest token:", guestTokenFromStorage);
        setGuestToken(guestTokenFromStorage);
        axiosInstance.defaults.headers.common['Authorization'] = `Bearer ${guestTokenFromStorage}`;
      } else {
        console.log("No token found, creating guest session");
        await createGuestSession();
      }
      setLoading(false);
    };

    initializeSession();
  }, [refreshAccessToken, setInitialOrganization, setGuestSession]);

  const login = useCallback(
    async (userData: Partial<User>, token: string, refreshToken: string) => {
      console.log("Login process started.");
      try {
        const decodedUser = jwtDecode<User>(token);
        console.log("Decoded user after login:", decodedUser);

        if (decodedUser.exp * 1000 < Date.now()) {
          throw new Error("User token expired");
        }

        localStorage.setItem("token", token);
        localStorage.setItem("refresh_token", refreshToken);
        localStorage.removeItem('guest_token');
        setGuestToken(null);

        axiosInstance.defaults.headers.common["Authorization"] = `Bearer ${token}`;

        setUser(decodedUser);
        setInitialOrganization(decodedUser.initial_organization);
      } catch (error) {
        console.error("Error during login:", error);
      }
    },
    [setInitialOrganization]
  );

  const incrementMessageCount = useCallback(() => {
    setMessageCount((prevCount) => prevCount + 1);
    console.log("Message count incremented:", messageCount + 1);
  }, [messageCount]);

  return (
    <UserContext.Provider value={{
      user,
      messageCount,
      selectedOrganization,
      guestToken,
      login,
      logout,
      setSelectedOrganization,
      loading,
      incrementMessageCount,
      setUser,
      setGuestSession
    }}>
      {children}
    </UserContext.Provider>
  );
};

export default UserProvider;
