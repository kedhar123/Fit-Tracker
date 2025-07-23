from fastapi import FastAPI, APIRouter, HTTPException, status
from fastapi.security import HTTPBearer
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime
import hashlib
import secrets


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="FitTracker API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

security = HTTPBearer()

# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

# User Models
class UserProfile(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    height: Optional[int] = None  # in cm
    weight: Optional[float] = None  # in kg
    activity_level: Optional[str] = "sedentary"
    goal: Optional[str] = "maintain"

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirmPassword: str
    age: Optional[int] = None
    gender: Optional[str] = None
    height: Optional[int] = None
    weight: Optional[float] = None
    activity_level: Optional[str] = "sedentary"
    goal: Optional[str] = "maintain"

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: EmailStr
    password_hash: str
    profile: UserProfile
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    profile: UserProfile
    created_at: datetime

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    message: str
    user: UserResponse
    token: Optional[str] = None

# Utility functions
def hash_password(password: str) -> str:
    """Hash a password with salt"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${password_hash}"

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash"""
    try:
        salt, stored_hash = password_hash.split('$')
        password_hash_check = hashlib.sha256((password + salt).encode()).hexdigest()
        return password_hash_check == stored_hash
    except:
        return False

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "FitTracker API is running"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Authentication Routes
@api_router.post("/register", response_model=AuthResponse)
async def register_user_direct(user_data: UserCreate):
    """Register a new user - direct endpoint that frontend expects"""
    return await register_user(user_data)

@api_router.post("/auth/register", response_model=AuthResponse)
async def register_user(user_data: UserCreate):
    """Register a new user"""
    try:
        # Validate password confirmation
        if user_data.password != user_data.confirmPassword:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match"
            )
        
        # Check if user already exists
        existing_user = await db.users.find_one({
            "$or": [
                {"email": user_data.email},
                {"username": user_data.username}
            ]
        })
        
        if existing_user:
            if existing_user.get("email") == user_data.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # Create user profile
        profile = UserProfile(
            age=user_data.age,
            gender=user_data.gender,
            height=user_data.height,
            weight=user_data.weight,
            activity_level=user_data.activity_level or "sedentary",
            goal=user_data.goal or "maintain"
        )
        
        # Create user object
        user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            profile=profile
        )
        
        # Insert user into database
        result = await db.users.insert_one(user.dict())
        
        if result.inserted_id:
            # Return success response
            user_response = UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                profile=user.profile,
                created_at=user.created_at
            )
            
            return AuthResponse(
                message="User registered successfully",
                user=user_response
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )

@api_router.post("/auth/login", response_model=AuthResponse) 
async def login_user(login_data: LoginRequest):
    """Login a user"""
    try:
        # Find user by email
        user_doc = await db.users.find_one({"email": login_data.email})
        
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(login_data.password, user_doc["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create response
        user_response = UserResponse(
            id=user_doc["id"],
            username=user_doc["username"],
            email=user_doc["email"],
            profile=UserProfile(**user_doc["profile"]),
            created_at=user_doc["created_at"]
        )
        
        return AuthResponse(
            message="Login successful",
            user=user_response,
            token=f"token_{user_doc['id']}"  # Simple token for now
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

@api_router.get("/auth/me")
async def get_current_user():
    """Get current user profile - placeholder for now"""
    return {"message": "Authentication endpoint working"}

@api_router.get("/users", response_model=List[UserResponse])
async def get_users():
    """Get all users - for testing purposes"""
    try:
        users = await db.users.find({}, {"password_hash": 0}).to_list(1000)
        return [
            UserResponse(
                id=user["id"],
                username=user["username"],
                email=user["email"],
                profile=UserProfile(**user["profile"]),
                created_at=user["created_at"]
            ) for user in users
        ]
    except Exception as e:
        logging.error(f"Get users error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch users"
        )

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
