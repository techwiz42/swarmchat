import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { Send } from 'lucide-react';
import ChatMessage from "./ChatMessage.jsx";
import './SwarmChat.css'; 

const ChatInterface = ({
  messages,
  inputMessage,
  isLoading,
  error,
  onInputChange,
  onSubmit,
  messagesEndRef,
  children
}) => {
  const handleSubmit = (e) => {
    console.log("Form submit triggered");
    onSubmit(e);
  };

  const handleButtonClick = () => {
    console.log("Button clicked");
  };

  return (
    <Card className="h-[calc(100vh-12rem)]">
      <div className="h-full flex flex-col">
        <div className="flex-1 overflow-y-auto p-4 space-y-4 chat-container">
          {messages.map((msg, idx) => (
            <ChatMessage key={idx} message={msg} />
          ))}
          <div ref={messagesEndRef} />
          {children}
        </div>
        <div className="p-4 border-t">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <Input
              value={inputMessage}
              onChange={onInputChange}
              placeholder="Type your message..."
              className="flex-1"
              disabled={isLoading}
            />
            <Button type="submit" disabled={isLoading} onClick={handleButtonClick}>
              <Send className="w-4 h-4" />
            </Button>
          </form>
          {error && (
            <p className="text-sm text-red-500 mt-2">{error}</p>
          )}
        </div>
      </div>
    </Card>
  );
};

export default ChatInterface;
