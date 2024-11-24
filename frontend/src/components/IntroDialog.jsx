import { Dialog, DialogContent, DialogHeader, DialogTitle } from "./ui/dialog";
import './SwarmChat.css'; 

const IntroDialog = ({ isOpen, onOpenChange }) => (
  <Dialog open={isOpen} onOpenChange={onOpenChange}>
    <DialogContent>
      <div className="intro-dialog">
        <DialogHeader>
          <DialogTitle>Welcome to Swarm Chat!</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <p>This is a unique chat experience where you'll interact with a variety of AI personalities, including:</p>
          <ul className="list-disc pl-6 space-y-2">
            <li>Ernest Hemingway - Known for direct, terse prose</li>
            <li>Thomas Pynchon - Complex, postmodern style</li>
            <li>Emily Dickinson - Poetic and contemplative</li>
            <li>Dale Carnegie - Motivational and positive</li>
            <li>H. L. Mencken - A somewhat caustic journalist</li>
            <li>A Freudian Psychoanalyst - Deep psychological insights</li>
            <li>...and many more</li>
          </ul>
        </div>
      </div>
    </DialogContent>
  </Dialog>
);

export default IntroDialog;
