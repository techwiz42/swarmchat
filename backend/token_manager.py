# token_manager.py
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy import and_
from database import db_manager, User

class TokenManager:
    @staticmethod
    async def create_verification_token(user_id: int) -> str:
        """Create a new email verification token."""
        token = secrets.token_urlsafe(32)
        expiry = datetime.utcnow() + timedelta(hours=24)
        
        async with db_manager.get_session() as session:
            await session.execute(
                """
                INSERT INTO verification_tokens (user_id, token, expires_at)
                VALUES (:user_id, :token, :expires_at)
                """,
                {"user_id": user_id, "token": token, "expires_at": expiry}
            )
            await session.commit()
        
        return token

    @staticmethod
    async def verify_email_token(token: str) -> Optional[int]:
        """Verify an email verification token and return user_id if valid."""
        async with db_manager.get_session() as session:
            result = await session.execute(
                """
                SELECT user_id FROM verification_tokens
                WHERE token = :token AND expires_at > :now AND used = false
                """,
                {"token": token, "now": datetime.utcnow()}
            )
            token_data = result.first()
            
            if token_data:
                # Mark token as used
                await session.execute(
                    """
                    UPDATE verification_tokens
                    SET used = true, used_at = :now
                    WHERE token = :token
                    """,
                    {"token": token, "now": datetime.utcnow()}
                )
                
                # Mark user as verified
                await session.execute(
                    """
                    UPDATE users
                    SET email_verified = true
                    WHERE id = :user_id
                    """,
                    {"user_id": token_data.user_id}
                )
                
                await session.commit()
                return token_data.user_id
                
        return None

    @staticmethod
    async def create_password_reset_token(user_id: int) -> str:
        """Create a new password reset token."""
        token = secrets.token_urlsafe(32)
        expiry = datetime.utcnow() + timedelta(hours=1)
        
        async with db_manager.get_session() as session:
            await session.execute(
                """
                INSERT INTO password_reset_tokens (user_id, token, expires_at)
                VALUES (:user_id, :token, :expires_at)
                """,
                {"user_id": user_id, "token": token, "expires_at": expiry}
            )
            await session.commit()
        
        return token

    @staticmethod
    async def verify_reset_token(token: str) -> Optional[int]:
        """Verify a password reset token and return user_id if valid."""
        async with db_manager.get_session() as session:
            result = await session.execute(
                """
                SELECT user_id FROM password_reset_tokens
                WHERE token = :token AND expires_at > :now AND used = false
                """,
                {"token": token, "now": datetime.utcnow()}
            )
            token_data = result.first()
            
            if token_data:
                # Mark token as used
                await session.execute(
                    """
                    UPDATE password_reset_tokens
                    SET used = true, used_at = :now
                    WHERE token = :token
                    """,
                    {"token": token, "now": datetime.utcnow()}
                )
                await session.commit()
                return token_data.user_id
                
        return None

token_manager = TokenManager()
