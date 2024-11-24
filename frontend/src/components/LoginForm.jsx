import { useState } from "react";
import { Link } from 'react-router-dom';
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { MessageSquare, Mic, Volume2, VolumeX, User, KeyRound } from 'lucide-react';
import { cn } from "../lib/utils";
import './SwarmChat.css';

const LoginForm = ({
  username,
  isLoading,
  isListening,
  isTTSEnabled,
  isSpeaking,
  error,
  onUsernameChange,
  onSubmit,
  onToggleSpeech,
  onToggleTTS
}) => {
  const [password, setPassword] = useState('');
  
  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(e, username, password);
  };

  return (
    <div className="auth-form-container">
      <Card className="p-6 space-y-6">
        <div className="flex justify-between items-center flex-col gap-4">
          <h2 className="text-2xl font-bold">Login to Swarm Chat</h2>
          <h3 className="text-blue-500">A Swarm of Intelligent Agents is ready to talk to you</h3>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="icon"
              type="button"
              onClick={onToggleSpeech}
              className={cn(isListening && "bg-blue-100")}
              title="Speech-to-text"
            >
              <Mic className="w-4 h-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={onToggleTTS}
              className={cn(isTTSEnabled && "bg-blue-100")}
              title="Text-to-speech"
            >
              {isTTSEnabled ? (
                <Volume2 className={cn("w-4 h-4", isSpeaking && "animate-pulse")} />
              ) : (
                <VolumeX className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="block text-sm font-medium">Username</label>
              <div className="relative">
                <User className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
                <Input
                  value={username}
                  onChange={onUsernameChange}
                  placeholder="Enter your username"
                  disabled={isLoading}
                  className="pl-9"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <label className="block text-sm font-medium">Password</label>
              <div className="relative">
                <KeyRound className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  disabled={isLoading}
                  className="pl-9"
                />
              </div>
            </div>
          </div>

          {error && (
            <div className="p-3 text-sm text-red-600 bg-red-50 rounded-md">
              {error}
            </div>
          )}

          <Button 
            type="submit" 
            disabled={isLoading} 
            className="w-full"
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            {isLoading ? 'Logging in...' : 'Login'}
          </Button>

          <div className="text-center text-sm text-gray-500">
            Don't have an account?{' '}
            <Link 
              to="/register" 
              className="text-blue-500 hover:text-blue-600"
            >
              Register here
            </Link>
          </div>
        </form>
      </Card>
    </div>
  );
};

export default LoginForm;
