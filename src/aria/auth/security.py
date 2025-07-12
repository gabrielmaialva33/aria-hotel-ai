"""Authentication and authorization system."""

import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from uuid import UUID
from enum import Enum
from dataclasses import dataclass

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import redis.asyncio as redis

from aria.core.logging import get_logger
from aria.core.config import settings

logger = get_logger(__name__)


class UserRole(Enum):
    """User roles in the system."""
    GUEST = "guest"  # Hotel guest
    STAFF = "staff"  # Hotel staff
    MANAGER = "manager"  # Hotel manager
    ADMIN = "admin"  # System administrator
    SUPER_ADMIN = "super_admin"  # Super administrator


class Permission(Enum):
    """System permissions."""
    # Guest permissions
    VIEW_OWN_RESERVATIONS = "view_own_reservations"
    CREATE_RESERVATION = "create_reservation"
    MODIFY_OWN_RESERVATION = "modify_own_reservation"
    CANCEL_OWN_RESERVATION = "cancel_own_reservation"
    VIEW_OWN_PROFILE = "view_own_profile"
    UPDATE_OWN_PROFILE = "update_own_profile"
    
    # Staff permissions
    VIEW_ALL_RESERVATIONS = "view_all_reservations"
    MODIFY_ANY_RESERVATION = "modify_any_reservation"
    CHECK_IN_GUEST = "check_in_guest"
    CHECK_OUT_GUEST = "check_out_guest"
    VIEW_GUEST_PROFILES = "view_guest_profiles"
    SEND_MESSAGES = "send_messages"
    VIEW_REPORTS = "view_reports"
    
    # Manager permissions
    CANCEL_ANY_RESERVATION = "cancel_any_reservation"
    ISSUE_REFUNDS = "issue_refunds"
    MANAGE_ROOMS = "manage_rooms"
    MANAGE_RATES = "manage_rates"
    VIEW_FINANCIAL_REPORTS = "view_financial_reports"
    MANAGE_STAFF = "manage_staff"
    
    # Admin permissions
    MANAGE_SYSTEM = "manage_system"
    MANAGE_INTEGRATIONS = "manage_integrations"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_AI_SETTINGS = "manage_ai_settings"
    
    # Super admin permissions
    DELETE_DATA = "delete_data"
    MANAGE_ADMINS = "manage_admins"
    SYSTEM_MAINTENANCE = "system_maintenance"


# Role-Permission mapping
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.GUEST: {
        Permission.VIEW_OWN_RESERVATIONS,
        Permission.CREATE_RESERVATION,
        Permission.MODIFY_OWN_RESERVATION,
        Permission.CANCEL_OWN_RESERVATION,
        Permission.VIEW_OWN_PROFILE,
        Permission.UPDATE_OWN_PROFILE,
    },
    UserRole.STAFF: {
        # Inherits guest permissions
        Permission.VIEW_OWN_RESERVATIONS,
        Permission.CREATE_RESERVATION,
        Permission.VIEW_OWN_PROFILE,
        Permission.UPDATE_OWN_PROFILE,
        # Staff-specific
        Permission.VIEW_ALL_RESERVATIONS,
        Permission.MODIFY_ANY_RESERVATION,
        Permission.CHECK_IN_GUEST,
        Permission.CHECK_OUT_GUEST,
        Permission.VIEW_GUEST_PROFILES,
        Permission.SEND_MESSAGES,
        Permission.VIEW_REPORTS,
    },
    UserRole.MANAGER: {
        # Inherits all staff permissions
        Permission.VIEW_OWN_RESERVATIONS,
        Permission.CREATE_RESERVATION,
        Permission.VIEW_OWN_PROFILE,
        Permission.UPDATE_OWN_PROFILE,
        Permission.VIEW_ALL_RESERVATIONS,
        Permission.MODIFY_ANY_RESERVATION,
        Permission.CHECK_IN_GUEST,
        Permission.CHECK_OUT_GUEST,
        Permission.VIEW_GUEST_PROFILES,
        Permission.SEND_MESSAGES,
        Permission.VIEW_REPORTS,
        # Manager-specific
        Permission.CANCEL_ANY_RESERVATION,
        Permission.ISSUE_REFUNDS,
        Permission.MANAGE_ROOMS,
        Permission.MANAGE_RATES,
        Permission.VIEW_FINANCIAL_REPORTS,
        Permission.MANAGE_STAFF,
    },
    UserRole.ADMIN: {
        # Has all permissions except super admin ones
        Permission.VIEW_OWN_RESERVATIONS,
        Permission.CREATE_RESERVATION,
        Permission.MODIFY_OWN_RESERVATION,
        Permission.CANCEL_OWN_RESERVATION,
        Permission.VIEW_OWN_PROFILE,
        Permission.UPDATE_OWN_PROFILE,
        Permission.VIEW_ALL_RESERVATIONS,
        Permission.MODIFY_ANY_RESERVATION,
        Permission.CHECK_IN_GUEST,
        Permission.CHECK_OUT_GUEST,
        Permission.VIEW_GUEST_PROFILES,
        Permission.SEND_MESSAGES,
        Permission.VIEW_REPORTS,
        Permission.CANCEL_ANY_RESERVATION,
        Permission.ISSUE_REFUNDS,
        Permission.MANAGE_ROOMS,
        Permission.MANAGE_RATES,
        Permission.VIEW_FINANCIAL_REPORTS,
        Permission.MANAGE_STAFF,
        Permission.MANAGE_SYSTEM,
        Permission.MANAGE_INTEGRATIONS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.MANAGE_AI_SETTINGS,
    },
    UserRole.SUPER_ADMIN: {
        # Has all permissions
        permission for permission in Permission
    }
}


@dataclass
class User:
    """User model for authentication."""
    id: UUID
    email: str
    name: str
    role: UserRole
    is_active: bool = True
    is_verified: bool = False
    phone: Optional[str] = None
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    metadata: Optional[Dict] = None


@dataclass
class TokenData:
    """JWT token payload data."""
    sub: str  # Subject (user ID)
    email: str
    role: str
    permissions: List[str]
    exp: datetime
    iat: datetime
    jti: Optional[str] = None  # JWT ID for revocation


class AuthService:
    """Authentication and authorization service."""
    
    def __init__(self):
        """Initialize auth service."""
        # Password hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # JWT settings
        self.secret_key = settings.jwt_secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
        
        # Redis for token blacklist and sessions
        self.redis_client = None
        
        # API key management
        self.api_keys: Dict[str, Dict] = {}  # In production, use database
    
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Auth service initialized")
        except Exception as e:
            logger.error("Failed to initialize auth service", error=str(e))
    
    # Password management
    
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    # Token management
    
    def create_access_token(
        self,
        user: User,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        # Get user permissions
        permissions = list(ROLE_PERMISSIONS.get(user.role, set()))
        
        # Create token data
        token_data = TokenData(
            sub=str(user.id),
            email=user.email,
            role=user.role.value,
            permissions=[p.value for p in permissions],
            exp=expire,
            iat=datetime.utcnow(),
            jti=secrets.token_urlsafe(16)
        )
        
        # Encode token
        token = jwt.encode(
            {
                "sub": token_data.sub,
                "email": token_data.email,
                "role": token_data.role,
                "permissions": token_data.permissions,
                "exp": token_data.exp,
                "iat": token_data.iat,
                "jti": token_data.jti
            },
            self.secret_key,
            algorithm=self.algorithm
        )
        
        return token
    
    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token."""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        token = jwt.encode(
            {
                "sub": str(user.id),
                "type": "refresh",
                "exp": expire,
                "iat": datetime.utcnow(),
                "jti": secrets.token_urlsafe(16)
            },
            self.secret_key,
            algorithm=self.algorithm
        )
        
        return token
    
    async def decode_token(self, token: str) -> TokenData:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token is blacklisted
            jti = payload.get("jti")
            if jti and await self._is_token_blacklisted(jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked"
                )
            
            # Create token data
            token_data = TokenData(
                sub=payload["sub"],
                email=payload["email"],
                role=payload["role"],
                permissions=payload["permissions"],
                exp=datetime.fromtimestamp(payload["exp"]),
                iat=datetime.fromtimestamp(payload["iat"]),
                jti=jti
            )
            
            return token_data
            
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    async def revoke_token(self, token: str):
        """Revoke a token by adding to blacklist."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            jti = payload.get("jti")
            
            if jti and self.redis_client:
                # Add to blacklist with expiration
                exp = datetime.fromtimestamp(payload["exp"])
                ttl = int((exp - datetime.utcnow()).total_seconds())
                
                if ttl > 0:
                    await self.redis_client.setex(
                        f"blacklist:{jti}",
                        ttl,
                        "1"
                    )
                    
            logger.info("Token revoked", jti=jti)
            
        except Exception as e:
            logger.error("Failed to revoke token", error=str(e))
    
    async def _is_token_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted."""
        if not self.redis_client:
            return False
        
        try:
            result = await self.redis_client.get(f"blacklist:{jti}")
            return result is not None
        except Exception:
            return False
    
    # Session management
    
    async def create_session(self, user: User, device_info: Optional[Dict] = None) -> str:
        """Create user session."""
        session_id = secrets.token_urlsafe(32)
        
        session_data = {
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "created_at": datetime.utcnow().isoformat(),
            "device_info": device_info or {}
        }
        
        if self.redis_client:
            # Store session with 24 hour expiration
            await self.redis_client.setex(
                f"session:{session_id}",
                86400,
                json.dumps(session_data)
            )
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data."""
        if not self.redis_client:
            return None
        
        try:
            data = await self.redis_client.get(f"session:{session_id}")
            return json.loads(data) if data else None
        except Exception:
            return None
    
    async def delete_session(self, session_id: str):
        """Delete user session."""
        if self.redis_client:
            await self.redis_client.delete(f"session:{session_id}")
    
    # API Key management
    
    def generate_api_key(self) -> str:
        """Generate new API key."""
        return f"aria_{secrets.token_urlsafe(32)}"
    
    async def create_api_key(
        self,
        name: str,
        permissions: List[Permission],
        expires_in_days: Optional[int] = None
    ) -> Dict:
        """Create new API key with permissions."""
        api_key = self.generate_api_key()
        
        key_data = {
            "key": api_key,
            "name": name,
            "permissions": [p.value for p in permissions],
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (
                datetime.utcnow() + timedelta(days=expires_in_days)
            ).isoformat() if expires_in_days else None,
            "last_used": None,
            "is_active": True
        }
        
        # Store API key (in production, use database)
        self.api_keys[api_key] = key_data
        
        if self.redis_client:
            await self.redis_client.hset(
                "api_keys",
                api_key,
                json.dumps(key_data)
            )
        
        logger.info("API key created", name=name)
        
        return key_data
    
    async def validate_api_key(self, api_key: str) -> Optional[Dict]:
        """Validate API key and return its data."""
        # Check in-memory first
        if api_key in self.api_keys:
            key_data = self.api_keys[api_key]
        elif self.redis_client:
            # Check Redis
            data = await self.redis_client.hget("api_keys", api_key)
            if not data:
                return None
            key_data = json.loads(data)
        else:
            return None
        
        # Check if active
        if not key_data.get("is_active"):
            return None
        
        # Check expiration
        if key_data.get("expires_at"):
            expires_at = datetime.fromisoformat(key_data["expires_at"])
            if expires_at < datetime.utcnow():
                return None
        
        # Update last used
        key_data["last_used"] = datetime.utcnow().isoformat()
        
        if self.redis_client:
            await self.redis_client.hset(
                "api_keys",
                api_key,
                json.dumps(key_data)
            )
        
        return key_data
    
    async def revoke_api_key(self, api_key: str):
        """Revoke an API key."""
        if api_key in self.api_keys:
            self.api_keys[api_key]["is_active"] = False
        
        if self.redis_client:
            key_data = await self.redis_client.hget("api_keys", api_key)
            if key_data:
                data = json.loads(key_data)
                data["is_active"] = False
                await self.redis_client.hset(
                    "api_keys",
                    api_key,
                    json.dumps(data)
                )
        
        logger.info("API key revoked", api_key=api_key[:10] + "...")
    
    # Permission checking
    
    def has_permission(
        self,
        user_role: UserRole,
        permission: Permission
    ) -> bool:
        """Check if role has permission."""
        return permission in ROLE_PERMISSIONS.get(user_role, set())
    
    def check_permissions(
        self,
        user_role: UserRole,
        required_permissions: List[Permission]
    ) -> bool:
        """Check if role has all required permissions."""
        user_permissions = ROLE_PERMISSIONS.get(user_role, set())
        return all(perm in user_permissions for perm in required_permissions)


# FastAPI dependencies

security = HTTPBearer()
auth_service = AuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> TokenData:
    """Get current user from JWT token."""
    token = credentials.credentials
    
    try:
        token_data = await auth_service.decode_token(token)
        return token_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


def require_permissions(*permissions: Permission):
    """Decorator to require specific permissions."""
    async def permission_checker(
        current_user: TokenData = Depends(get_current_user)
    ):
        user_permissions = [Permission(p) for p in current_user.permissions]
        
        for permission in permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permission: {permission.value}"
                )
        
        return current_user
    
    return permission_checker


def require_role(*roles: UserRole):
    """Decorator to require specific roles."""
    async def role_checker(
        current_user: TokenData = Depends(get_current_user)
    ):
        user_role = UserRole(current_user.role)
        
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role. Required: {[r.value for r in roles]}"
            )
        
        return current_user
    
    return role_checker


# Rate limiting
class RateLimiter:
    """Rate limiter for API endpoints."""
    
    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    async def __call__(
        self,
        current_user: TokenData = Depends(get_current_user)
    ):
        """Check rate limit for user."""
        if not auth_service.redis_client:
            return current_user
        
        key = f"rate_limit:{current_user.sub}"
        
        try:
            # Increment counter
            count = await auth_service.redis_client.incr(key)
            
            # Set expiration on first request
            if count == 1:
                await auth_service.redis_client.expire(key, self.window_seconds)
            
            # Check limit
            if count > self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds} seconds"
                )
            
            return current_user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Rate limiter error", error=str(e))
            return current_user


# Example usage in FastAPI
"""
from fastapi import APIRouter, Depends
from aria.auth.security import (
    get_current_user, 
    require_permissions, 
    require_role,
    Permission,
    UserRole,
    RateLimiter
)

router = APIRouter()

@router.get("/reservations")
async def list_reservations(
    current_user: TokenData = Depends(
        require_permissions(Permission.VIEW_ALL_RESERVATIONS)
    )
):
    # Only users with VIEW_ALL_RESERVATIONS permission can access
    pass

@router.post("/refund")
async def issue_refund(
    current_user: TokenData = Depends(
        require_role(UserRole.MANAGER, UserRole.ADMIN)
    )
):
    # Only managers and admins can issue refunds
    pass

@router.get("/protected", dependencies=[Depends(RateLimiter(max_requests=10))])
async def rate_limited_endpoint(
    current_user: TokenData = Depends(get_current_user)
):
    # Rate limited to 10 requests per minute
    pass
"""
