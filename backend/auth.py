from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os
import logging
from database import User, db_manager

# Configure logging
logger = logging.getLogger(__name__)

# Constants
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Get JWT secret key from environment variable
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    logger.warning("JWT_SECRET_KEY not set! Using default secret - DO NOT USE IN PRODUCTION!")
    SECRET_KEY = "your-default-secret-key-change-in-production"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class AuthManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user and return the user object if successful."""
        try:
            db = self.db_manager.get_session()
            try:
                user = db.query(User).filter(User.username == username).first()
                if user and user.verify_password(password):
                    return user
                return None
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication error"
            )

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT token."""
        try:
            to_encode = data.copy()
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                
            to_encode.update({"exp": expire})
            encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"Token creation error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create access token"
            )

    async def get_current_user(self, token: str = Depends(oauth2_scheme)) -> User:
        """Get the current user from a JWT token."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            # Decode JWT token
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
                
            # Get user from database
            db = self.db_manager.get_session()
            try:
                user = db.query(User).filter(User.username == username).first()
                if user is None:
                    raise credentials_exception
                    
                # Check if user is active
                if user.is_active != 'Y':
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="User account is disabled"
                    )
                    
                return user
            finally:
                db.close()
                
        except JWTError as e:
            logger.error(f"JWT validation error: {str(e)}", exc_info=True)
            raise credentials_exception
        except Exception as e:
            logger.error(f"User validation error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication error"
            )

    async def get_optional_user(self, token: str = Depends(oauth2_scheme)) -> Optional[User]:
        """Get the current user from a JWT token, but don't raise an exception if not found."""
        try:
            return await self.get_current_user(token)
        except HTTPException:
            return None

    def verify_token(self, token: str) -> bool:
        """Verify if a token is valid."""
        try:
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return True
        except JWTError:
            return False

    async def refresh_token(self, current_token: str = Depends(oauth2_scheme)) -> str:
        """Refresh an existing token."""
        try:
            # Verify current token
            payload = jwt.decode(current_token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token for refresh"
                )
                
            # Create new token
            new_token = self.create_access_token(
                data={"sub": username},
                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            
            return new_token
            
        except JWTError as e:
            logger.error(f"Token refresh error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not refresh token"
            )
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token refresh error"
            )

# Create auth manager instance
auth_manager = AuthManager(db_manager)
