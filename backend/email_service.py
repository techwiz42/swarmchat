# email_service.py
import os
import pickle
from datetime import datetime, timedelta
from typing import Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
import logging

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
TOKEN_PICKLE_PATH = 'token.pickle'
CREDENTIALS_PATH = 'credentials.json'

class EmailService:
    def __init__(self):
        self.service = None
        self.credentials = None

    def refresh_token_if_needed(self) -> None:
        """Refresh the token if it's expired or about to expire."""
        try:
            if os.path.exists(TOKEN_PICKLE_PATH):
                with open(TOKEN_PICKLE_PATH, 'rb') as token:
                    self.credentials = pickle.load(token)

            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    logger.info("Refreshing expired token")
                    self.credentials.refresh(Request())
                else:
                    logger.info("Getting new token from OAuth flow")
                    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                    self.credentials = flow.run_local_server(port=0)

                with open(TOKEN_PICKLE_PATH, 'wb') as token:
                    pickle.dump(self.credentials, token)

            self.service = build('gmail', 'v1', credentials=self.credentials)
            logger.info("Email service initialized successfully")

        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            raise

    def send_verification_email(self, to_email: str, verification_token: str, base_url: str) -> bool:
        """Send verification email to user."""
        try:
            self.refresh_token_if_needed()
            verification_link = f"{base_url}/verify-email?token={verification_token}"
            
            message = MIMEText(f"""
            Welcome to SwarmChat!
            
            Please verify your email address by clicking the link below:
            {verification_link}
            
            This link will expire in 24 hours.
            
            If you did not create this account, please ignore this email.
            """)

            message['to'] = to_email
            message['subject'] = 'Verify your SwarmChat account'
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            self.service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
            
            logger.info(f"Verification email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Error sending verification email: {str(e)}")
            return False

    def send_password_reset_email(self, to_email: str, reset_token: str, base_url: str) -> bool:
        """Send password reset email to user."""
        try:
            self.refresh_token_if_needed()
            reset_link = f"{base_url}/reset-password?token={reset_token}"
            
            message = MIMEText(f"""
            You have requested to reset your SwarmChat password.
            
            Click the link below to reset your password:
            {reset_link}
            
            This link will expire in 1 hour.
            
            If you did not request this password reset, please ignore this email.
            """)

            message['to'] = to_email
            message['subject'] = 'Reset your SwarmChat password'
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            self.service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
            
            logger.info(f"Password reset email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Error sending password reset email: {str(e)}")
            return False

email_service = EmailService()
