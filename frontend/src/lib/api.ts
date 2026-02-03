import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        "Content-Type": "application/json",
    },
});

// Automatically add token to requests
api.interceptors.request.use((config) => {
    const token = localStorage.getItem("token");
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Handle 401 Unauthorized globally
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;
            const refreshToken = localStorage.getItem("refreshToken");

            if (refreshToken) {
                try {
                    const { data } = await axios.post(`${API_BASE_URL}/refresh`, {
                        refresh_token: refreshToken
                    });

                    localStorage.setItem("token", data.access_token);
                    localStorage.setItem("refreshToken", data.refresh_token);

                    originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
                    return axios(originalRequest);
                } catch (refreshError) {
                    localStorage.removeItem("token");
                    localStorage.removeItem("refreshToken");
                    if (typeof window !== "undefined") {
                        window.location.href = "/login";
                    }
                    return Promise.reject(refreshError);
                }
            } else {
                localStorage.removeItem("token");
                if (typeof window !== "undefined") {
                    window.location.href = "/login";
                }
            }
        }
        return Promise.reject(error);
    }
);

export default api;
