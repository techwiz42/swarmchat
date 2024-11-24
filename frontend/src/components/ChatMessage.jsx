import { cn } from "../lib/utils";

const ChatMessage = ({ message }) => (
  <div className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
    <div
      className={cn(
        "max-w-[80%] p-3 rounded-lg",
        message.role === 'user'
          ? "bg-blue-500 text-white"
          : "bg-gray-100 text-gray-900"
      )}
    >
      {message.content}
    </div>
  </div>
);

export default ChatMessage;
