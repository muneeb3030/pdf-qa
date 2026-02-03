"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";

interface AuthContextType {
    token: string | null;
    refreshToken: string | null;
    login: (token: string, refreshToken: string) => void;
    logout: () => void;
    isAuthenticated: boolean;
    loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [token, setToken] = useState<string | null>(null);
    const [refreshToken, setRefreshToken] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        const savedToken = localStorage.getItem("token");
        const savedRefreshToken = localStorage.getItem("refreshToken");
        if (savedToken) setToken(savedToken);
        if (savedRefreshToken) setRefreshToken(savedRefreshToken);
        setLoading(false);
    }, []);

    useEffect(() => {
        if (!loading) {
            const publicRoutes = ["/", "/login", "/signup"];
            const isPublicRoute = publicRoutes.includes(pathname);

            if (!token && !isPublicRoute) {
                router.push("/login");
            } else if (token && (pathname === "/login" || pathname === "/signup")) {
                router.push("/dashboard");
            }
        }
    }, [token, loading, pathname, router]);

    const login = (newToken: string, newRefreshToken: string) => {
        localStorage.setItem("token", newToken);
        localStorage.setItem("refreshToken", newRefreshToken);
        setToken(newToken);
        setRefreshToken(newRefreshToken);
        router.push("/dashboard");
    };

    const logout = () => {
        localStorage.removeItem("token");
        localStorage.removeItem("refreshToken");
        setToken(null);
        setRefreshToken(null);
        router.push("/login");
    };

    // Inactivity Auto-Logout (Option B)
    useEffect(() => {
        let timeout: NodeJS.Timeout;

        const resetTimer = () => {
            if (timeout) clearTimeout(timeout);
            // 15 Minutes = 900,000 ms
            timeout = setTimeout(() => {
                if (token) {
                    console.log("Auto-logging out due to 15 minutes of inactivity");
                    logout();
                }
            }, 900000);
        };

        if (token) {
            // Events to track user activity
            const events = ["mousedown", "keydown", "scroll", "touchstart"];
            events.forEach((event) => window.addEventListener(event, resetTimer));

            // Start the initial timer
            resetTimer();

            return () => {
                if (timeout) clearTimeout(timeout);
                events.forEach((event) => window.removeEventListener(event, resetTimer));
            };
        }
    }, [token]);

    return (
        <AuthContext.Provider value={{ token, refreshToken, login, logout, isAuthenticated: !!token, loading }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}
