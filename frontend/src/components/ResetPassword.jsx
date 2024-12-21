import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { KeyRound } from 'lucide-react';

const ResetPassword = () => {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [token, setToken] = useState('');
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // Get token from URL query parameters
    const params = new URLSearchParams(location.search);
    const resetToken = params.get('token');
    if (!resetToken) {
      setError('Invalid or missing reset token');
      return;
    }
    setToken(resetToken);
  }, [location]);

  const validatePassword = (pass) => {
    if (pass.length < 8) {
      return 'Password must be at least 8 characters long';
    }
    if (!/[A-Z]/.test(pass)) {
      return 'Password must contain at least one uppercase letter';
    }
    if (!/[a-z]/.test(pass)) {
      return 'Password must contain at least one lowercase letter';
    }
    if (!/[0-9]/.test(pass)) {
      return 'Password must contain at least one number';
    }
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Validate password
    const passwordError = validatePassword(password);
    if (passwordError) {
      setError(passwordError);
      return;
    }

    // Check if passwords match
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch('/api/reset-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          token, 
          new_password: password 
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to reset password');
      }

      // Redirect to login with success message
      navigate('/login', { 
        state: { message: 'Password reset successful. Please log in with your new password.' }
      });

    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  if (!token) {
    return (
      <Card className="p-6">
        <div className="text-center text-red-600">
          Invalid or missing reset token. Please request a new password reset link.
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div className="space-y-6">
        <div className="text-center">
          <h2 className="text-2xl font-bold">Reset Your Password</h2>
          <p className="text-gray-600">
            Please enter your new password.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium">New Password</label>
            <div className="relative">
              <KeyRound className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter new password"
                disabled={isLoading}
                className="pl-9"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium">Confirm Password</label>
            <div className="relative">
              <KeyRound className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
              <Input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm new password"
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
            {isLoading ? 'Updating...' : 'Reset Password'}
          </Button>
        </form>
      </div>
    </Card>
  );
};

export default ResetPassword;
