import { Button } from "./ui/button";
import { LogOut, Mic, Volume2, VolumeX } from 'lucide-react';
import { cn } from "../lib/utils";

const Header = ({ 
  isConnected, 
  isLoading, 
  isListening,
  isTTSEnabled,
  isSpeaking,
  onLogout,
  onToggleSpeech,
  onToggleTTS 
}) => (
  <div className="bg-white shadow-sm p-4 flex justify-between items-center">
    <div className="flex items-center gap-2">
      <div className={cn(
        "w-3 h-3 rounded-full",
        isConnected ? "bg-green-500" : "bg-red-500",
        isLoading && "animate-pulse"
      )} />
      <span>{isConnected ? 'Connected' : 'Not Connected'}</span>
    </div>
    {isConnected && (
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="icon"
          onClick={onToggleSpeech}
          className={cn(isListening && "bg-blue-100")}
        >
          <Mic className="w-4 h-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          onClick={onToggleTTS}
          className={cn(isTTSEnabled && "bg-blue-100")}
        >
          {isTTSEnabled ? (
            <Volume2 className={cn("w-4 h-4", isSpeaking && "animate-pulse")} />
          ) : (
            <VolumeX className="w-4 h-4" />
          )}
        </Button>
        <Button variant="ghost" onClick={onLogout} disabled={isLoading}>
          <LogOut className="w-4 h-4 mr-2" />
          Exit Session
        </Button>
      </div>
    )}
  </div>
);

export default Header;
