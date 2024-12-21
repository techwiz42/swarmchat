import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';

// Components
import SwarmChat from './components/SwarmChat';
import Header from './components/Header';
import Footer from './components/Footer';
import LoginForm from './components/LoginForm';
import RegisterForm from './components/RegisterForm';
import ForgotPassword from './components/ForgotPassword';
import ResetPassword from './components/ResetPassword';
import EmailVerification from './components/EmailVerification';
import ProtectedRoute from './components/ProtectedRoute';

// Styles
import './styles/globals.css';

function Layout({ children }) {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      <main className="flex-1 container mx-auto max-w-4xl p-4">
        {children}
      </main>
      <Footer />
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="min-h-screen bg-background">
          <Routes>
            {/* Public Routes */}
            <Route 
              path="/login" 
              element={
                <Layout>
                  <LoginForm />
                </Layout>
              } 
            />
            <Route 
              path="/register" 
              element={
                <Layout>
                  <RegisterForm />
                </Layout>
              } 
            />
            <Route 
              path="/forgot-password" 
              element={
                <Layout>
                  <ForgotPassword />
                </Layout>
              } 
            />
            <Route 
              path="/reset-password" 
              element={
                <Layout>
                  <ResetPassword />
                </Layout>
              } 
            />
            <Route 
              path="/verify-email" 
              element={
                <Layout>
                  <EmailVerification />
                </Layout>
              } 
            />

            {/* Protected Routes */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout>
                    <SwarmChat />
                  </Layout>
                </ProtectedRoute>
              }
            />

            {/* Catch all unmatched routes */}
            <Route 
              path="*" 
              element={<Navigate to="/login" replace />} 
            />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
