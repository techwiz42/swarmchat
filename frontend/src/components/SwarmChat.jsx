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

  // Add useEffect to monitor messages state
  useEffect(() => {
    console.log("Messages updated:", messages);
  }, [messages]);

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
      console.log("Restoring session from localStorage");
      setAccessToken(savedAccessToken);
      setChatToken(savedChatToken);
      setUsername(savedUsername);
      setIsConnected(true);
      setInputMessage('');
      fetchHistory(savedAccessToken);
      navigate('/');
    }
  }, [navigate]);

  const handleIntroDialogClose = (isOpen) => {
    setIsIntroOpen(isOpen);
    if (!isOpen) {
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
      
      console.log("Attempting login...");
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
      console.log("Login response:", data);  // Check if initial_message is present

      setAccessToken(data.access_token);
      setChatToken(data.chat_token);
      setUsername(data.username);
      setIsConnected(true);
      setInputMessage('');

      // Add initial message to messages if it exists
      if (data.initial_message) {
        console.log("Setting initial message:", data.initial_message);
        setMessages([{ role: 'assistant', content: data.initial_message }]);
      }

      // Save tokens and username
      localStorage.setItem('accessToken', data.access_token);
      localStorage.setItem('chatToken', data.chat_token);
      localStorage.setItem('username', data.username);

      navigate('/');
    } catch (err) {
      console.error("Login error:", err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchHistory = async (token) => {
    try {
      console.log("Fetching chat history...");
      const response = await fetch(`${API_BASE_URL}/history`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch history: ${response.statusText}`);
      }

      const data = await response.json();
      console.log("History response:", data.messages);
      setMessages(data.messages);
    } catch (error) {
      console.error("History fetch error:", error);
      setError('Failed to load chat history. Please try refreshing.');
    }
  };

  const handleSendMessage = async (e) => {
    e?.preventDefault();
    console.log("handleSendMessage called", { inputMessage, accessToken, chatToken });
    
    if (!inputMessage.trim() || !accessToken || isLoading) {
      console.log("Early return condition met:", { 
        isEmpty: !inputMessage.trim(), 
        noToken: !accessToken, 
        isLoading 
      });
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      const currentMessage = inputMessage;
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

      console.log("Chat response status:", response.status);

      if (!response.ok) {
        throw new Error(`Failed to send message: ${response.statusText}`);
      }

      const data = await response.json();
      console.log("Chat response data:", data);
      
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
      console.error("Send message error:", err);
      setError(`Failed to send message: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegistration = async (userData) => {
    try {
      await handleLogin(null, userData.username, userData.password);
      navigate('/');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleLogout = async () => {
    try {
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
      setIsConnected(false);
      setAccessToken(null);
      setChatToken(null);
      setMessages([]);
      setUsername('');
      setError(null);
      setInputMessage('');
      
      localStorage.removeItem('accessToken');
      localStorage.removeItem('chatToken');
      localStorage.removeItem('username');
      
      if (speechHandlerRef.current && isListening) {
        speechHandlerRef.current.stopListening();
        setListening(false);
      }
      
      navigate('/login');
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
