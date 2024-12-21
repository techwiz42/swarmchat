import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { Mail, ArrowLeft } from 'lucide-react';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    console.log('Sending request to:', '/api/request-password-reset');
    try {
      const response = await fetch('/api/request-password-reset', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });
      console.log('Response status:', response.status);
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to send reset email');
      }

      setIsSubmitted(true);

    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  if (isSubmitted) {
    return (
      <Card className="p-6 space-y-4">
        <h2 className="text-2xl font-bold text-center">Check Your Email</h2>
        <p className="text-center text-gray-600">
          If an account exists with the email {email}, you will receive password reset instructions.
        </p>
        <div className="text-center">
          <Link to="/login" className="text-blue-500 hover:text-blue-600">
            Return to Login
          </Link>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div className="space-y-6">
        <div className="text-center">
          <h2 className="text-2xl font-bold">Reset Password</h2>
          <p className="text-gray-600">
            Enter your email address and we'll send you instructions to reset your password.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                disabled={isLoading}
                className="pl-9"
                required
              />
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
            {isLoading ? 'Sending...' : 'Send Reset Instructions'}
          </Button>
        </form>

        <Link 
          to="/login" 
          className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to Login
        </Link>
      </div>
    </Card>
  );
};

export default ForgotPassword;
