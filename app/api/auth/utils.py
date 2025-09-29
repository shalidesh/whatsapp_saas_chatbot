import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash
import structlog

from ...config.settings import config
from ...models.user import User
from ...config.database import db_session

logger = structlog.get_logger(__name__)

def generate_jwt_token(user_id: int, expires_in: Optional[int] = None) -> str:
    """Generate JWT token for user authentication"""
    try:
        if expires_in is None:
            expires_in = config.JWT_ACCESS_TOKEN_EXPIRES
            
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow(),
            'type': 'access'
        }
        
        token = jwt.encode(payload, config.JWT_SECRET_KEY, algorithm='HS256')
        
        logger.info("JWT token generated", user_id=user_id, expires_in=expires_in)
        return token
        
    except Exception as e:
        logger.error("Error generating JWT token", error=str(e), user_id=user_id)
        raise

def generate_refresh_token(user_id: int) -> str:
    """Generate refresh token for token renewal"""
    try:
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(days=30),  # 30 days
            'iat': datetime.utcnow(),
            'type': 'refresh'
        }
        
        token = jwt.encode(payload, config.JWT_SECRET_KEY, algorithm='HS256')
        
        logger.info("Refresh token generated", user_id=user_id)
        return token
        
    except Exception as e:
        logger.error("Error generating refresh token", error=str(e), user_id=user_id)
        raise

def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired", token=token[:20] + "...")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid JWT token", token=token[:20] + "...")
        return None
    except Exception as e:
        logger.error("Error decoding JWT token", error=str(e))
        return None

def validate_user_credentials(email: str, password: str) -> Optional[User]:
    """Validate user login credentials"""
    try:
        # Find user by email
        user = db_session.query(User).filter(
            User.email == email.lower().strip(),
            User.is_active == True
        ).first()
        
        if not user:
            logger.warning("Login attempt with non-existent email", email=email)
            return None
        
        # Check password
        if not user.check_password(password):
            logger.warning("Login attempt with incorrect password", 
                         email=email, user_id=user.id)
            return None
        
        logger.info("User credentials validated successfully", 
                   email=email, user_id=user.id)
        return user
        
    except Exception as e:
        logger.error("Error validating user credentials", error=str(e), email=email)
        return None

def hash_password(password: str) -> str:
    """Hash password securely"""
    try:
        return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    except Exception as e:
        logger.error("Error hashing password", error=str(e))
        raise

def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    try:
        return check_password_hash(password_hash, password)
    except Exception as e:
        logger.error("Error verifying password", error=str(e))
        return False

def create_user_session(user: User) -> Dict[str, Any]:
    """Create user session data"""
    try:
        access_token = generate_jwt_token(user.id)
        refresh_token = generate_refresh_token(user.id)
        
        session_data = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict(),
            'expires_in': config.JWT_ACCESS_TOKEN_EXPIRES,
            'token_type': 'Bearer'
        }
        
        logger.info("User session created", user_id=user.id, email=user.email)
        return session_data
        
    except Exception as e:
        logger.error("Error creating user session", error=str(e), user_id=user.id)
        raise

def refresh_access_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    """Refresh access token using refresh token"""
    try:
        # Decode refresh token
        payload = decode_jwt_token(refresh_token)
        if not payload or payload.get('type') != 'refresh':
            return None
        
        user_id = payload.get('user_id')
        if not user_id:
            return None
        
        # Find user
        user = db_session.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()
        
        if not user:
            return None
        
        # Generate new access token
        access_token = generate_jwt_token(user.id)
        
        return {
            'access_token': access_token,
            'expires_in': config.JWT_ACCESS_TOKEN_EXPIRES,
            'token_type': 'Bearer'
        }
        
    except Exception as e:
        logger.error("Error refreshing access token", error=str(e))
        return None

def invalidate_user_tokens(user_id: int):
    """Invalidate all user tokens (logout)"""
    try:
        # In a production system, you'd maintain a token blacklist
        # For now, we'll just log the invalidation
        logger.info("User tokens invalidated", user_id=user_id)
        
        # TODO: Implement token blacklist in Redis
        # redis_client.sadd(f"blacklisted_tokens:{user_id}", token_jti)
        
    except Exception as e:
        logger.error("Error invalidating user tokens", error=str(e), user_id=user_id)

def get_user_from_token(token: str) -> Optional[User]:
    """Get user object from JWT token"""
    try:
        payload = decode_jwt_token(token)
        if not payload:
            return None
        
        user_id = payload.get('user_id')
        if not user_id:
            return None
        
        user = db_session.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()
        
        return user
        
    except Exception as e:
        logger.error("Error getting user from token", error=str(e))
        return None

def is_token_valid(token: str) -> bool:
    """Check if token is valid"""
    try:
        payload = decode_jwt_token(token)
        return payload is not None
        
    except Exception as e:
        logger.error("Error checking token validity", error=str(e))
        return False

def get_password_strength(password: str) -> Dict[str, Any]:
    """Analyze password strength"""
    try:
        strength = {
            'score': 0,
            'feedback': [],
            'is_strong': False
        }
        
        # Length check
        if len(password) >= 8:
            strength['score'] += 1
        else:
            strength['feedback'].append("Password should be at least 8 characters long")
        
        # Uppercase check
        if any(c.isupper() for c in password):
            strength['score'] += 1
        else:
            strength['feedback'].append("Include at least one uppercase letter")
        
        # Lowercase check
        if any(c.islower() for c in password):
            strength['score'] += 1
        else:
            strength['feedback'].append("Include at least one lowercase letter")
        
        # Number check
        if any(c.isdigit() for c in password):
            strength['score'] += 1
        else:
            strength['feedback'].append("Include at least one number")
        
        # Special character check
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            strength['score'] += 1
        else:
            strength['feedback'].append("Include at least one special character")
        
        # Determine if strong (score >= 4)
        strength['is_strong'] = strength['score'] >= 4
        
        return strength
        
    except Exception as e:
        logger.error("Error analyzing password strength", error=str(e))
        return {'score': 0, 'feedback': ['Error analyzing password'], 'is_strong': False}