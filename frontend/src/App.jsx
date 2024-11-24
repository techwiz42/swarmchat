import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import SwarmChat from './components/SwarmChat';
import './styles/globals.css';

function App() {
  return (
    <div className="min-h-screen bg-background">
      <Router>
        <Routes>
          <Route path="/" element={<SwarmChat />} />
          <Route path="/login" element={<SwarmChat />} />
          <Route path="/register" element={<SwarmChat />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </Router>
    </div>
  );
}

export default App;
