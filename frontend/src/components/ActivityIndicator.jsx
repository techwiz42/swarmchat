import { Mic, Volume2 } from 'lucide-react';

const ActivityIndicator = ({ isListening, isLoading, isSpeaking }) => {
  if (isListening) {
    return (
      <div className="flex justify-start">
        <div className="bg-red-50 text-red-900 max-w-[80%] p-3 rounded-lg">
          <div className="flex items-center gap-2">
            <Mic className="w-4 h-4 animate-pulse text-red-500" />
            <div className="flex gap-2">
              <div className="w-2 h-2 bg-red-500 rounded-full animate-bounce" />
              <div className="w-2 h-2 bg-red-500 rounded-full animate-bounce [animation-delay:-.3s]" />
              <div className="w-2 h-2 bg-red-500 rounded-full animate-bounce [animation-delay:-.5s]" />
            </div>
          </div>
        </div>
      </div>
    );
  }
  if (isLoading) {
    return (
      <div className="flex justify-start">
        <div className="bg-gray-100 text-gray-900 max-w-[80%] p-3 rounded-lg">
          <div className="flex gap-2">
            <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" />
            <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce [animation-delay:-.3s]" />
            <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce [animation-delay:-.5s]" />
          </div>
        </div>
      </div>
    );
  }
  if (isSpeaking) {
    return (
      <div className="flex justify-start">
        <div className="bg-blue-100 text-blue-900 max-w-[80%] p-3 rounded-lg flex items-center gap-2">
          <Volume2 className="w-4 h-4 animate-pulse" />
          <span>Speaking...</span>
        </div>
      </div>
    );
  }
  return null;
};

export default ActivityIndicator;
