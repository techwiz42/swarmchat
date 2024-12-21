// src/contexts/AuthContext.jsx
import { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing token and user data
    const token = localStorage.getItem('accessToken');
    const userData = localStorage.getItem('userData');
    if (token && userData) {
      setUser(JSON.parse(userData));
    }
    setLoading(false);
  }, []);

  const login = async (username, password) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await fetch('/api/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    const data = await response.json();
    localStorage.setItem('accessToken', data.access_token);
    localStorage.setItem('userData', JSON.stringify({
      username: data.username,
      email_verified: data.email_verified
    }));
    setUser({
      username: data.username,
      email_verified: data.email_verified
    });
  };

  const logout = async () => {
    try {
      await fetch('/api/logout', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
        }
      });
    } finally {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('userData');
      setUser(null);
    }
  };

  const requestPasswordReset = async (email) => {
    const response = await fetch('/api/request-password-reset', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to request password reset');
    }
  };

  const resetPassword = async (token, newPassword) => {
    const response = await fetch('/api/reset-password', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ token, new_password: newPassword })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to reset password');
    }
  };

  const resendVerification = async () => {
    const response = await fetch('/api/request-verification', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
      }
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to resend verification');
    }
  };

  return (
    <AuthContext.Provider value={{
      user,
      loading,
      login,
      logout,
      requestPasswordReset,
      resetPassword,
      resendVerification
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
