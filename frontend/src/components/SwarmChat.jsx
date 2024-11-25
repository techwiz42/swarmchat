import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { SpeechHandler, useSpeechStore } from '../lib/SpeechHandler';
import IntroDialog from './IntroDialog.jsx';
import Header from './Header.jsx';
import Footer from './Footer.jsx';
import LoginForm from './LoginForm.jsx';
import RegisterForm from './RegisterForm.jsx';
import ChatInterface from './ChatInterface.jsx';
import ActivityIndicator from './ActivityIndicator.jsx';

const API_BASE_URL = '/api';

const SwarmChat = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isIntroOpen, setIsIntroOpen] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [username, setUsername] = useState('');
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [accessToken, setAccessToken] = useState(null);
  const [chatToken, setChatToken] = useState(null);
  
  const messagesEndRef = useRef(null);
  const speechHandlerRef = useRef(null);
  const { isTTSEnabled, isListening, setTTSEnabled, setListening } = useSpeechStore();

  useEffect(() => {
    speechHandlerRef.current = new SpeechHandler();
    
    if (window.speechSynthesis) {
      const handleSpeechStart = () => setIsSpeaking(true);
      const handleSpeechEnd = () => setIsSpeaking(false);
      
      window.speechSynthesis.addEventListener('start', handleSpeechStart);
      window.speechSynthesis.addEventListener('end', handleSpeechEnd);
      
      return () => {
        window.speechSynthesis.removeEventListener('start', handleSpeechStart);
        window.speechSynthesis.removeEventListener('end', handleSpeechEnd);
      };
    }
  }, []);

  useEffect(() => {
    // Check for saved tokens in localStorage
    const savedAccessToken = localStorage.getItem('accessToken');
    const savedChatToken = localStorage.getItem('chatToken');
    const savedUsername = localStorage.getItem('username');
    
    if (savedAccessToken && savedChatToken && savedUsername) {
      setAccessToken(savedAccessToken);
      setChatToken(savedChatToken);
      setUsername(savedUsername);
      setIsConnected(true);
      setInputMessage('');  // Clear input message when restoring session
      fetchHistory(savedAccessToken);
      navigate('/'); // Redirect to chat if already logged in
    }
  }, [navigate]);

  const handleIntroDialogClose = (isOpen) => {
    setIsIntroOpen(isOpen);
    if (!isOpen) {
      // When intro dialog is closed, always navigate to login
      navigate('/login');
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleLogin = async (e, username, password) => {
    e?.preventDefault();
    if (!username.trim() || !password.trim()) return;

    try {
      setIsLoading(true);
      setError(null);
      
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      
      const response = await fetch(`${API_BASE_URL}/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }

      const data = await response.json();
      setAccessToken(data.access_token);
      setChatToken(data.chat_token);
      setUsername(data.username);
      setIsConnected(true);
      setInputMessage('');  // Clear input message on new session

      // Save tokens and username
      localStorage.setItem('accessToken', data.access_token);
      localStorage.setItem('chatToken', data.chat_token);
      localStorage.setItem('username', data.username);

      await fetchHistory(data.access_token);
      navigate('/'); // Redirect to chat after successful login
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchHistory = async (token) => {
    try {
      const response = await fetch(`${API_BASE_URL}/history`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch history: ${response.statusText}`);
      }

      const data = await response.json();
      setMessages(data.messages);
    } catch (error) {
      setError('Failed to load chat history. Please try refreshing.');
    }
  };

  const handleSendMessage = async (e, autoSend = false) => {
    e?.preventDefault();
    const currentMessage = inputMessage;
    if (!currentMessage.trim() || !accessToken || !chatToken || isLoading) return;

    try {
      setIsLoading(true);
      setError(null);
      
      setInputMessage('');

      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
          'X-Chat-Token': chatToken
        },
        body: JSON.stringify({ content: currentMessage })
      });

      if (!response.ok) {
        throw new Error(`Failed to send message: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data.response) {
        setMessages(prev => [...prev, 
          { role: 'user', content: currentMessage },
          { role: 'assistant', content: data.response }
        ]);
        
        if (isTTSEnabled && speechHandlerRef.current) {
          try {
            await speechHandlerRef.current.speak(data.response);
          } catch (err) {
            console.error('TTS Error:', err);
          }
        }
      }
    } catch (err) {
      setError(`Failed to send message: ${err.message}`);
      setInputMessage(currentMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegistration = async (userData) => {
    try {
      // After successful registration, automatically log in
      await handleLogin(null, userData.username, userData.password);
      navigate('/'); // Redirect to chat after successful registration
    } catch (err) {
      setError(err.message);
    }
  };

  const handleLogout = async () => {
    try {
      // Call logout endpoint if it exists
      if (accessToken && chatToken) {
        await fetch(`${API_BASE_URL}/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'X-Chat-Token': chatToken
          }
        });
      }
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      // Clean up local state regardless of logout request success
      setIsConnected(false);
      setAccessToken(null);
      setChatToken(null);
      setMessages([]);
      setUsername('');
      setError(null);
      setInputMessage('');  // Clear input message on logout
      
      // Clear stored tokens
      localStorage.removeItem('accessToken');
      localStorage.removeItem('chatToken');
      localStorage.removeItem('username');
      
      if (speechHandlerRef.current && isListening) {
        speechHandlerRef.current.stopListening();
        setListening(false);
      }
      
      navigate('/login'); // Redirect to login after logout
    }
  };

  const toggleSpeechRecognition = () => {
    if (speechHandlerRef.current) {
      const newListeningState = speechHandlerRef.current.toggleSpeech((text, autoSend) => {
        setInputMessage(text);
        if (autoSend) {
          handleSendMessage({ preventDefault: () => {} }, true);
        }
      });
      setListening(newListeningState);
    }
  };

  const toggleTTS = () => {
    if (window.speechSynthesis) {
      if (isTTSEnabled) {
        window.speechSynthesis.cancel();
      }
      setTTSEnabled(!isTTSEnabled);
    }
  };

  // Render different components based on route and auth state
  const renderContent = () => {
    if (isConnected) {
      return (
        <ChatInterface
          messages={messages}
          inputMessage={inputMessage}
          isLoading={isLoading}
          error={error}
          onInputChange={(e) => setInputMessage(e.target.value)}
          onSubmit={handleSendMessage}
          messagesEndRef={messagesEndRef}
        >
          <ActivityIndicator 
            isListening={isListening}
            isLoading={isLoading}
            isSpeaking={isSpeaking}
          />
        </ChatInterface>
      );
    }

    if (location.pathname === '/register') {
      return (
        <RegisterForm
          onRegister={handleRegistration}
        />
      );
    }

    return (
      <LoginForm
        username={username}
        isLoading={isLoading}
        isListening={isListening}
        isTTSEnabled={isTTSEnabled}
        isSpeaking={isSpeaking}
        error={error}
        onUsernameChange={(e) => setUsername(e.target.value)}
        onSubmit={handleLogin}
        onToggleSpeech={toggleSpeechRecognition}
        onToggleTTS={toggleTTS}
      />
    );
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <IntroDialog isOpen={isIntroOpen} onOpenChange={setIsIntroOpen} />
      
      <Header 
        isConnected={isConnected}
        isLoading={isLoading}
        isListening={isListening}
        isTTSEnabled={isTTSEnabled}
        isSpeaking={isSpeaking}
        onLogout={handleLogout}
        onToggleSpeech={toggleSpeechRecognition}
        onToggleTTS={toggleTTS}
      />

      <div className="flex-1 container mx-auto max-w-4xl p-4">
        {renderContent()}
      </div>

      <Footer />
    </div>
  );
};

export default SwarmChat;
