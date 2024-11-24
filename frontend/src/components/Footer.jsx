import { Github, Mail } from 'lucide-react';

const Footer = () => (
  <footer className="bg-white shadow-sm p-4 mt-auto">
    <div className="container mx-auto max-w-4xl flex justify-center gap-4 text-sm text-gray-600">
      <a
        href="https://github.com/techwiz42/swarmchat"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center hover:text-gray-900"
      >
        <Github className="w-4 h-4 mr-1" />
        View on GitHub
      </a>
      <span>|</span>
      <a
        href="mailto:thetechwizard42@gmail.com"
        className="flex items-center hover:text-gray-900"
      >
        <Mail className="w-4 h-4 mr-1" />
        Contact Developer
      </a>
    </div>
  </footer>
);

export default Footer;
