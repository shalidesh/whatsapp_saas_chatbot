
# 2. UPDATED: api/auth/routes.py
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import jwt
import structlog

from ...models.user import User
from ...models.business import Business
from ...config.database import db_session
from ...config.settings import config
from ...utils.validators import validate_email, validate_password

logger = structlog.get_logger(__name__)

auth_router = APIRouter()
security = HTTPBearer()

# Pydantic models for request/response validation
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: str
    business_name: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    phone: str
    created_at: datetime
    is_active: bool

class BusinessResponse(BaseModel):
    id: int
    name: str
    description: str
    user_id: int
    created_at: datetime
    is_active: bool

class RegisterResponse(BaseModel):
    message: str
    token: str
    user: dict
    business: dict

class LoginResponse(BaseModel):
    message: str
    token: str
    user: dict
    businesses: list

class VerifyTokenResponse(BaseModel):
    valid: bool
    user: dict

@auth_router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest):
    """User registration"""
    try:
        # Validate input
        email = request.email.lower().strip()
        password = request.password
        first_name = request.first_name.strip()
        last_name = request.last_name.strip()
        phone = request.phone.strip()
        business_name = request.business_name.strip()
        
        # Validation
        if not validate_password(password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters"
            )
        
        if not first_name or not last_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="First name and last name are required"
            )
        
        if not business_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Business name is required"
            )
        
        # Check if user already exists
        existing_user = db_session.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists"
            )
        
        # Create user
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone
        )
        user.set_password(password)
        
        db_session.add(user)
        db_session.flush()  # Get user ID
        
        # Create business
        business = Business(
            user_id=user.id,
            name=business_name,
            description=f"{business_name} - AI-powered customer service",
            whatsapp_phone_number=phone
        )
        
        db_session.add(business)
        db_session.commit()
        
        # Generate JWT token
        token = generate_jwt_token(user.id)
        
        logger.info("User registered successfully", 
                   user_id=user.id, email=email, business_id=business.id)
        
        return RegisterResponse(
            message="Registration successful",
            token=token,
            user=user.to_dict(),
            business=business.to_dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db_session.rollback()
        logger.error("Registration error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@auth_router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """User login"""
    try:
        email = request.email.lower().strip()
        password = request.password
        
        # Find user
        user = db_session.query(User).filter(
            User.email == email,
            User.is_active == True
        ).first()
        
        if not user or not user.check_password(password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Generate JWT token
        token = generate_jwt_token(user.id)
        
        # Get user's businesses
        businesses = db_session.query(Business).filter(
            Business.user_id == user.id,
            Business.is_active == True
        ).all()
        
        logger.info("User logged in successfully", user_id=user.id, email=email)
        
        return LoginResponse(
            message="Login successful",
            token=token,
            user=user.to_dict(),
            businesses=[business.to_dict() for business in businesses]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@auth_router.post("/verify-token", response_model=VerifyTokenResponse)
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    try:
        token = credentials.credentials
        
        # Decode token
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')
        
        # Find user
        user = db_session.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        return VerifyTokenResponse(
            valid=True,
            user=user.to_dict()
        )
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error("Token verification error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token verification failed"
        )

def generate_jwt_token(user_id: int) -> str:
    """Generate JWT token for user"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(seconds=config.JWT_ACCESS_TOKEN_EXPIRES),
        'iat': datetime.utcnow()
    }
    
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm='HS256')

# 3. UPDATED: utils.py (no changes needed - keep as is)
# The utils.py file can remain the same since it contains utility functions
# that don't depend on Flask/FastAPI specifically

# 4. UPDATED: Import in app/__init__.py 
# Change this line in app/__init__.py:
# from .api.auth.routes import auth_router  # ✅ This is correct now