const ResendVerification = () => {
  const handleResend = async () => {
    try {
      await fetch('/api/request-verification', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
        }
      });
      alert('Verification email sent!');
    } catch (error) {
      console.error('Error:', error);
    }
  };

  return (
    <Button onClick={handleResend}>
      Resend Verification Email
    </Button>
  );
};
