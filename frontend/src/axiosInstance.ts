import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';


const backendUrl = import.meta.env.VITE_REACT_APP_BACKEND_URL || 'http://127.0.0.1:5000';

console.log("Environment variable REACT_APP_BACKEND_URL:", import.meta.env.VITE_REACT_APP_BACKEND_URL);
console.log("Using backend URL:", backendUrl);

const axiosInstance: AxiosInstance = axios.create({
    baseURL: `${backendUrl}/api`,
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    },
});

const createGuestSession = async () => {

    try {
        const response = await axiosInstance.post('/auth/refresh_token', {});
        const { access_token } = response.data;
        if (!access_token) {
            throw new Error('No access token received for guest session');
        }
        localStorage.setItem('guest_token', access_token);
        return access_token;
    } catch (error) {
        console.error('Failed to create guest session:', error);
        throw error;
    }
};

const refreshAccessToken = async () => {


    const refreshToken = localStorage.getItem("refresh_token");

    try {
        if (!refreshToken) {
            console.log("No refresh token available, creating guest session");
            return await createGuestSession();
        }

        const response = await axiosInstance.post('/auth/refresh_token', {
            refresh_token: refreshToken,
        });

        const { access_token, is_guest } = response.data;

        if (!is_guest) {
            localStorage.setItem('token', access_token);
            localStorage.removeItem('guest_token');
        } else {
            localStorage.setItem('guest_token', access_token);
            localStorage.removeItem('token');
        }

        return access_token;
    } catch (error) {
        console.error('Failed to refresh access token:', error);
        localStorage.removeItem('token');
        localStorage.removeItem('refresh_token');

        try {
            return await createGuestSession();
        } catch (guestError) {
            console.error('Failed to create guest session:', guestError);
            throw guestError;
        }
    }
};

axiosInstance.interceptors.request.use(
    (config) => {
        console.log('[Request Interceptor] Initial state:', {
            existingAuth: config.headers['Authorization'],
            timestamp: new Date().toISOString()
        });

        // Only respect valid existing auth headers
        if (config.headers['Authorization'] &&
            config.headers['Authorization'] !== 'Bearer null' &&
            !config.headers['Authorization'].includes('undefined')) {
            return config;
        }

        // Only use stored tokens if no URL session exists
        const storedToken = localStorage.getItem('token') || localStorage.getItem('guest_token');
        if (storedToken) {
            config.headers['Authorization'] = `Bearer ${storedToken}`;
            console.log('[Request Interceptor] Using stored token:', {
                token: storedToken,
                finalHeader: config.headers['Authorization'],
                timestamp: new Date().toISOString()
            });
        } else {
            console.log('[Request Interceptor] No token available', {
                timestamp: new Date().toISOString()
            });
        }

        // Log final config state
        console.log('[Request Interceptor] Final request config:', {
            url: config.url,
            method: config.method,
            headers: {
                ...config.headers,
                Authorization: config.headers['Authorization'] || 'none'
            },
            timestamp: new Date().toISOString()
        });

        return config;
    },
    (error) => {
        console.error('[Request Interceptor] Error:', {
            error: error.message,
            timestamp: new Date().toISOString()
        });
        return Promise.reject(error);
    }
);

axiosInstance.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig;

        // Skip token refresh and guest session creation for auth endpoints
        if (originalRequest.url?.includes('/auth/')) {
            return Promise.reject(error);
        }

        if (error.response) {
            const { status } = error.response;

            switch (status) {
                case 400:
                    console.error('Bad Request:', error.response.data);
                    break;

                case 401:
                    // Skip if this is a retry
                    if (originalRequest._retry) {
                        return Promise.reject(error);
                    }

                    originalRequest._retry = true;
                    console.log('Unauthorized, attempting to refresh token or create guest session');
                    try {
                        const newToken = await refreshAccessToken();
                        if (originalRequest.headers) {
                            originalRequest.headers['Authorization'] = `Bearer ${newToken}`;
                        }
                        return axiosInstance(originalRequest);
                    } catch (refreshError) {
                        console.error('Token refresh and guest session creation failed:', refreshError);
                        return Promise.reject(refreshError);
                    }

                case 403:
                    if (error.response.data &&
                        typeof error.response.data === 'object' &&
                        'error' in error.response.data) {
                        const errorMessage = (error.response.data as { error: string }).error;
                        if (errorMessage === "Token is outdated. Please refresh your token.") {
                            // Skip if this is a retry
                            if (originalRequest._retry) {
                                return Promise.reject(error);
                            }

                            originalRequest._retry = true;
                            try {
                                const newToken = await refreshAccessToken();
                                if (originalRequest.headers) {
                                    originalRequest.headers['Authorization'] = `Bearer ${newToken}`;
                                }
                                return axiosInstance(originalRequest);
                            } catch (refreshError) {
                                console.error('Token refresh failed:', refreshError);
                                return Promise.reject(refreshError);
                            }
                        }
                    }
                    break;

                case 404:
                    console.error('Not Found:', error.response.data);
                    break;

                case 500:
                    console.error('Internal Server Error:', error.response.data);
                    break;

                default:
                    console.error('An unexpected error occurred:', error.response.data);
            }
        } else if (error.request) {
            console.error('No response received:', error.request);
        } else {
            console.error('Error setting up request:', error.message);
        }

        return Promise.reject(error);
    }
);

export default axiosInstance;
