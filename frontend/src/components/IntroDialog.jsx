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
          <p>This is a unique chat experience where you'll interact with friendly, helpful AI agents</p>
          <ul className="list-disc pl-6 space-y-2">
          </ul>
        </div>
      </div>
    </DialogContent>
  </Dialog>
);

export default IntroDialog;
