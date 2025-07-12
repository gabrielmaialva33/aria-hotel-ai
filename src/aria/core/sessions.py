"""Session management for conversations using Redis."""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import redis.asyncio as redis
import redis.exceptions

from aria.core.config import settings
from aria.core.logging import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Manage user sessions in Redis or memory."""

    def __init__(self, ttl_hours: int = 24):
        """
        Initialize session manager.

        Args:
            ttl_hours: Session time-to-live in hours
        """
        self.redis: Optional[redis.Redis] = None
        self.ttl = timedelta(hours=ttl_hours)
        self._connected = False
        self._memory_store: Dict[str, Dict[str, Any]] = {}  # Fallback for when Redis is unavailable

    async def connect(self):
        """Connect to Redis."""
        if self._connected:
            return

        try:
            # Parse Redis URL to check for password
            redis_url = str(settings.redis_url)

            # If Redis URL has password, use it
            if "@" in redis_url and ":" in redis_url.split("@")[0].split("//")[-1]:
                self.redis = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    health_check_interval=30
                )
            else:
                # Try without password first
                self.redis = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    health_check_interval=30,
                    password=None
                )

            # Test connection
            await self.redis.ping()
            self._connected = True

            logger.info("Connected to Redis", url=redis_url.split("@")[-1] if "@" in redis_url else redis_url)

        except redis.exceptions.AuthenticationError:
            logger.warning("Redis requires authentication, running in memory-only mode")
            self._connected = False
            self.redis = None
        except Exception as e:
            logger.warning(f"Redis not available ({str(e)}), running in memory-only mode")
            self._connected = False
            self.redis = None

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis and self._connected:
            await self.redis.close()
            self._connected = False
            logger.info("Disconnected from Redis")

    async def get_session(self, phone: str) -> Dict[str, Any]:
        """
        Get session data for a phone number.

        Args:
            phone: Phone number (without whatsapp: prefix)

        Returns:
            Session data dictionary
        """
        key = self._get_session_key(phone)

        # Use memory store if Redis not available
        if not self._connected or not self.redis:
            session = self._memory_store.get(key)
            if session:
                # Check if session expired
                last_activity = datetime.fromisoformat(session.get("last_activity", datetime.now().isoformat()))
                if datetime.now() - last_activity > self.ttl:
                    del self._memory_store[key]
                    return self._create_default_session(phone)
                return session
            return self._create_default_session(phone)

        # Use Redis if available
        try:
            data = await self.redis.get(key)

            if data:
                session = json.loads(data)
                logger.debug("Session retrieved from Redis", phone=phone)
                return session
            else:
                logger.debug("No session found", phone=phone)
                return self._create_default_session(phone)

        except Exception as e:
            logger.error(
                "Error retrieving session from Redis",
                phone=phone,
                error=str(e)
            )
            # Fallback to memory
            return self._memory_store.get(key, self._create_default_session(phone))

    async def save_session(self, phone: str, data: Dict[str, Any]):
        """
        Save session data.

        Args:
            phone: Phone number
            data: Session data to save
        """
        key = self._get_session_key(phone)

        # Update last activity
        data["last_activity"] = datetime.now().isoformat()

        # Use memory store if Redis not available
        if not self._connected or not self.redis:
            self._memory_store[key] = data
            logger.debug("Session saved to memory", phone=phone)
            return

        # Use Redis if available
        try:
            # Save with TTL
            await self.redis.setex(
                key,
                self.ttl,
                json.dumps(data, default=str)
            )

            logger.debug("Session saved to Redis", phone=phone)

        except Exception as e:
            logger.error(
                "Error saving session to Redis, using memory",
                phone=phone,
                error=str(e)
            )
            # Fallback to memory
            self._memory_store[key] = data

    async def delete_session(self, phone: str):
        """Delete session for a phone number."""
        key = self._get_session_key(phone)

        # Delete from memory store
        if key in self._memory_store:
            del self._memory_store[key]
            logger.info("Session deleted from memory", phone=phone)

        # Delete from Redis if available
        if self._connected and self.redis:
            try:
                await self.redis.delete(key)
                logger.info("Session deleted from Redis", phone=phone)
            except Exception as e:
                logger.error(
                    "Error deleting session from Redis",
                    phone=phone,
                    error=str(e)
                )

    async def extend_session(self, phone: str):
        """Extend session TTL."""
        if not self._connected:
            await self.connect()

        key = self._get_session_key(phone)

        try:
            await self.redis.expire(key, self.ttl)
            logger.debug("Session extended", phone=phone)
        except Exception as e:
            logger.error(
                "Error extending session",
                phone=phone,
                error=str(e)
            )

    async def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        # Count from memory store
        if not self._connected or not self.redis:
            # Clean expired sessions first
            now = datetime.now()
            expired_keys = []
            for key, session in self._memory_store.items():
                last_activity = datetime.fromisoformat(session.get("last_activity", now.isoformat()))
                if now - last_activity > self.ttl:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._memory_store[key]

            return len(self._memory_store)

        # Count from Redis if available
        try:
            pattern = "session:whatsapp:*"
            cursor = 0
            count = 0

            while True:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match=pattern,
                    count=100
                )
                count += len(keys)

                if cursor == 0:
                    break

            return count

        except Exception as e:
            logger.error("Error counting sessions", error=str(e))
            return len(self._memory_store)

    def _get_session_key(self, phone: str) -> str:
        """Get Redis key for session."""
        # Remove any whatsapp: prefix
        phone = phone.replace("whatsapp:", "")
        return f"session:whatsapp:{phone}"

    def _create_default_session(self, phone: str) -> Dict[str, Any]:
        """Create default session data."""
        return {
            "phone": phone,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "conversation_count": 0,
            "guest_name": None,
            "guest_id": None,
            "preferences": {},
            "context": {
                "current_flow": None,
                "reservation_data": None
            }
        }

    async def update_guest_info(
        self,
        phone: str,
        name: Optional[str] = None,
        guest_id: Optional[str] = None,
        preferences: Optional[Dict] = None
    ):
        """Update guest information in session."""
        session = await self.get_session(phone)

        if name:
            session["guest_name"] = name
        if guest_id:
            session["guest_id"] = guest_id
        if preferences:
            session["preferences"].update(preferences)

        await self.save_session(phone, session)

        logger.info(
            "Guest info updated",
            phone=phone,
            has_name=bool(name),
            has_id=bool(guest_id)
        )

    async def track_conversation(self, phone: str):
        """Track conversation count."""
        session = await self.get_session(phone)
        session["conversation_count"] = session.get("conversation_count", 0) + 1
        await self.save_session(phone, session)
