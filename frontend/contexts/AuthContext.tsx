"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { apiClient, User, LoginRequest, SignupRequest } from "@/lib/api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (data: LoginRequest) => Promise<void>;
  signup: (data: SignupRequest) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    const checkAuth = async () => {
      if (typeof window === "undefined") {
        if (isMounted) {
          setLoading(false);
        }
        return;
      }

      const token = localStorage.getItem("access_token");
      if (!token) {
        if (isMounted) {
          setLoading(false);
        }
        return;
      }

      try {
        // Fetch user data from API using token
        const user = await apiClient.getCurrentUser();
        if (isMounted) {
          setUser(user);
        }
      } catch (error) {
        // Token is invalid or expired, clear it
        console.error("Failed to fetch user:", error);
        localStorage.removeItem("access_token");
        if (isMounted) {
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    checkAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (data: LoginRequest) => {
    const response = await apiClient.login(data);
    setUser(response.user);
  };

  const signup = async (data: SignupRequest) => {
    await apiClient.signup(data);
    // After signup, automatically log in
    await login({ email: data.email, password: data.password });
  };

  const logout = () => {
    apiClient.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        signup,
        logout,
        isAuthenticated: !!user,
      }}
    >
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

