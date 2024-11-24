import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { MessageSquare, Mic, Volume2, VolumeX } from 'lucide-react';
import { cn } from "../lib/utils";

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
}) => (
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
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="space-y-2">
        <label className="block text-sm font-medium">Username</label>
        <Input
          value={username}
          onChange={onUsernameChange}
          placeholder="Enter your name to start"
          disabled={isLoading}
        />
        <p className="text-sm text-gray-500">
          No account required - just enter your name to start chatting!
          {isListening && <span className="ml-2 text-blue-500">Listening...</span>}
        </p>
      </div>
      {error && (
        <div className="p-3 text-sm text-red-600 bg-red-50 rounded-md">
          {error}
        </div>
      )}
      <Button type="submit" disabled={isLoading}>
        <MessageSquare className="w-4 h-4 mr-2" />
        {isLoading ? 'Connecting...' : 'Start Chatting'}
      </Button>
    </form>
  </Card>
);

export default LoginForm;
