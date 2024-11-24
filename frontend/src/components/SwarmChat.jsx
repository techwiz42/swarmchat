import React, { useState, useRef, useEffect } from 'react';
import { SpeechHandler, useSpeechStore } from '../lib/SpeechHandler';
import IntroDialog from './IntroDialog.jsx';
import Header from './Header.jsx';
import Footer from './Footer.jsx';
import LoginForm from './LoginForm.jsx';
import ChatInterface from './ChatInterface.jsx';
import ActivityIndicator from './ActivityIndicator.jsx';

const API_BASE_URL = '/api';

const SwarmChat = () => {
  const [isIntroOpen, setIsIntroOpen] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [username, setUsername] = useState('');
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const messagesEndRef = useRef(null);
  const [token, setToken] = useState(null);
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
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleLogin = async (e) => {
    e?.preventDefault();
    if (!username.trim()) return;

    try {
      setIsLoading(true);
      setError(null);
      
      const credentials = btoa(`${username}:dummy`);
      
      const response = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${credentials}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const errorData = await response.text();
        throw new Error(`Login failed: ${errorData}`);
      }

      const data = await response.json();
      setToken(data.token);
      setIsConnected(true);
      await fetchHistory(data.token);
    } catch (err) {
      setError(`Connection error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchHistory = async (currentToken) => {
    try {
      const response = await fetch(`${API_BASE_URL}/history`, {
        headers: {
          'Authorization': `Bearer ${currentToken}`
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
    if (!currentMessage.trim() || !token || isLoading) return;

    try {
      setIsLoading(true);
      setError(null);
      
      setInputMessage('');

      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
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

  const handleLogout = () => {
    setIsConnected(false);
    setToken(null);
    setMessages([]);
    setUsername('');
    setError(null);
    if (speechHandlerRef.current && isListening) {
      speechHandlerRef.current.stopListening();
      setListening(false);
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
        {!isConnected ? (
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
        ) : (
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
        )}
      </div>

      <Footer />
    </div>
  );
};

export default SwarmChat;
