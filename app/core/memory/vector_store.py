"""Vector store for long-term memory and semantic search."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import faiss
import numpy as np
import redis.asyncio as redis
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Memory:
    """A memory entry in the vector store."""
    id: str
    guest_id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}
        if self.id is None:
            self.id = str(uuid4())


@dataclass
class SearchResult:
    """Result from vector similarity search."""
    memory: Memory
    score: float
    relevance: str  # high, medium, low


class VectorMemoryStore:
    """
    Vector-based memory store for semantic search and long-term memory.
    
    Uses FAISS for efficient similarity search and Redis for persistence.
    """

    def __init__(self, dimension: int = 384):
        """
        Initialize vector store.
        
        Args:
            dimension: Embedding dimension (384 for MiniLM)
        """
        self.dimension = dimension
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

        # Initialize FAISS index
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity

        # Memory storage (id -> Memory)
        self.memories: Dict[str, Memory] = {}

        # Guest index (guest_id -> List[memory_ids])
        self.guest_index: Dict[str, List[str]] = {}

        # Redis for persistence
        self.redis_client = None
        self._initialized = False

    async def initialize(self):
        """Initialize connections and load existing memories."""
        if self._initialized:
            return

        try:
            # Connect to Redis
            self.redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )

            # Load existing memories
            await self._load_from_redis()

            self._initialized = True
            logger.info("Vector memory store initialized",
                        total_memories=len(self.memories))

        except Exception as e:
            logger.error("Failed to initialize vector store", error=str(e))
            # Continue without persistence
            self._initialized = True

    async def add_memory(
            self,
            guest_id: str,
            content: str,
            metadata: Optional[Dict] = None
    ) -> Memory:
        """
        Add a new memory to the store.
        
        Args:
            guest_id: Guest identifier
            content: Memory content
            metadata: Additional metadata
            
        Returns:
            Created memory
        """
        # Create memory object
        memory = Memory(
            id=str(uuid4()),
            guest_id=guest_id,
            content=content,
            metadata=metadata or {}
        )

        # Generate embedding
        embedding = self.model.encode(content)
        memory.embedding = embedding.tolist()

        # Add to FAISS index
        self.index.add(np.array([embedding]))

        # Store memory
        self.memories[memory.id] = memory

        # Update guest index
        if guest_id not in self.guest_index:
            self.guest_index[guest_id] = []
        self.guest_index[guest_id].append(memory.id)

        # Persist to Redis
        await self._save_memory_to_redis(memory)

        logger.debug(
            "Memory added",
            memory_id=memory.id,
            guest_id=guest_id,
            content_preview=content[:50]
        )

        return memory

    async def search_memories(
            self,
            query: str,
            guest_id: Optional[str] = None,
            k: int = 5,
            threshold: float = 0.7
    ) -> List[SearchResult]:
        """
        Search for similar memories.
        
        Args:
            query: Search query
            guest_id: Filter by guest (optional)
            k: Number of results
            threshold: Minimum similarity score
            
        Returns:
            List of search results
        """
        if not self.memories:
            return []

        # Generate query embedding
        query_embedding = self.model.encode(query)

        # Search in FAISS
        scores, indices = self.index.search(
            np.array([query_embedding]),
            min(k * 2, len(self.memories))  # Search more to filter later
        )

        results = []
        memory_ids = list(self.memories.keys())

        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or score < threshold:
                continue

            memory_id = memory_ids[idx]
            memory = self.memories[memory_id]

            # Filter by guest if specified
            if guest_id and memory.guest_id != guest_id:
                continue

            # Determine relevance
            if score > 0.9:
                relevance = "high"
            elif score > 0.8:
                relevance = "medium"
            else:
                relevance = "low"

            results.append(SearchResult(
                memory=memory,
                score=float(score),
                relevance=relevance
            ))

            if len(results) >= k:
                break

        return results

    async def get_guest_memories(
            self,
            guest_id: str,
            limit: int = 50
    ) -> List[Memory]:
        """
        Get all memories for a guest.
        
        Args:
            guest_id: Guest identifier
            limit: Maximum memories to return
            
        Returns:
            List of memories
        """
        memory_ids = self.guest_index.get(guest_id, [])
        memories = []

        for memory_id in memory_ids[-limit:]:
            if memory_id in self.memories:
                memories.append(self.memories[memory_id])

        # Sort by timestamp
        memories.sort(key=lambda m: m.timestamp, reverse=True)

        return memories

    async def get_guest_profile(self, guest_id: str) -> Dict:
        """
        Build guest profile from memories.
        
        Args:
            guest_id: Guest identifier
            
        Returns:
            Guest profile with preferences and patterns
        """
        memories = await self.get_guest_memories(guest_id)

        if not memories:
            return {
                "guest_id": guest_id,
                "total_interactions": 0,
                "preferences": {},
                "topics": [],
                "sentiment": "neutral"
            }

        # Analyze memories
        profile = {
            "guest_id": guest_id,
            "total_interactions": len(memories),
            "first_interaction": memories[-1].timestamp.isoformat(),
            "last_interaction": memories[0].timestamp.isoformat(),
            "preferences": {},
            "topics": [],
            "sentiment": "neutral",
            "patterns": {}
        }

        # Extract preferences
        preferences = {
            "room_type": [],
            "meal_plan": [],
            "activities": [],
            "special_requests": []
        }

        sentiments = []
        topics = set()

        for memory in memories:
            content = memory.content.lower()
            metadata = memory.metadata

            # Room preferences
            if "superior" in content:
                preferences["room_type"].append("superior")
            elif "térreo" in content or "terreo" in content:
                preferences["room_type"].append("terreo")

            # Meal preferences
            if "pensão completa" in content:
                preferences["meal_plan"].append("pensao_completa")
            elif "meia pensão" in content:
                preferences["meal_plan"].append("meia_pensao")

            # Activities
            if "piscina" in content:
                preferences["activities"].append("piscina")
            if "rodízio" in content or "massa" in content:
                preferences["activities"].append("rodizio_massas")

            # Sentiment
            if metadata.get("sentiment"):
                sentiments.append(metadata["sentiment"])

            # Topics
            if metadata.get("intent"):
                topics.add(metadata["intent"])

        # Aggregate preferences
        for key, values in preferences.items():
            if values:
                # Most common preference
                profile["preferences"][key] = max(set(values), key=values.count)

        # Overall sentiment
        if sentiments:
            sentiment_counts = {s: sentiments.count(s) for s in set(sentiments)}
            profile["sentiment"] = max(sentiment_counts, key=sentiment_counts.get)

        profile["topics"] = list(topics)

        # Patterns
        profile["patterns"] = {
            "avg_message_length": np.mean([len(m.content) for m in memories]),
            "prefers_weekends": self._prefers_weekends(memories),
            "advance_booking_days": self._avg_advance_booking(memories),
            "repeat_guest": len(memories) > 10
        }

        return profile

    async def find_similar_guests(
            self,
            guest_id: str,
            k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Find guests with similar preferences.
        
        Args:
            guest_id: Guest to compare
            k: Number of similar guests
            
        Returns:
            List of (guest_id, similarity_score)
        """
        # Get guest profile
        profile = await self.get_guest_profile(guest_id)

        if not profile["preferences"]:
            return []

        # Create profile embedding
        profile_text = json.dumps(profile["preferences"])
        profile_embedding = self.model.encode(profile_text)

        similar_guests = []

        # Compare with other guests
        for other_guest_id in self.guest_index:
            if other_guest_id == guest_id:
                continue

            other_profile = await self.get_guest_profile(other_guest_id)
            if not other_profile["preferences"]:
                continue

            # Calculate similarity
            other_text = json.dumps(other_profile["preferences"])
            other_embedding = self.model.encode(other_text)

            similarity = np.dot(profile_embedding, other_embedding) / (
                    np.linalg.norm(profile_embedding) * np.linalg.norm(other_embedding)
            )

            similar_guests.append((other_guest_id, float(similarity)))

        # Sort by similarity
        similar_guests.sort(key=lambda x: x[1], reverse=True)

        return similar_guests[:k]

    async def add_interaction(
            self,
            guest_id: str,
            message: str,
            response: str,
            metadata: Optional[Dict] = None
    ):
        """
        Add a conversation interaction to memory.
        
        Args:
            guest_id: Guest identifier
            message: User message
            response: System response
            metadata: Additional context
        """
        # Create interaction summary
        interaction = f"Guest: {message}\nAna: {response}"

        # Merge metadata
        interaction_metadata = {
            "type": "interaction",
            "user_message": message,
            "system_response": response
        }

        if metadata:
            interaction_metadata.update(metadata)

        # Add to memory
        await self.add_memory(guest_id, interaction, interaction_metadata)

    # Persistence methods

    async def _save_memory_to_redis(self, memory: Memory):
        """Save memory to Redis."""
        if not self.redis_client:
            return

        try:
            # Save memory data
            key = f"memory:{memory.id}"
            await self.redis_client.hset(
                key,
                mapping={
                    "id": memory.id,
                    "guest_id": memory.guest_id,
                    "content": memory.content,
                    "embedding": json.dumps(memory.embedding),
                    "metadata": json.dumps(memory.metadata),
                    "timestamp": memory.timestamp.isoformat()
                }
            )

            # Update guest index
            await self.redis_client.sadd(f"guest:{memory.guest_id}:memories", memory.id)

            # Set expiration (90 days)
            await self.redis_client.expire(key, 90 * 24 * 60 * 60)

        except Exception as e:
            logger.error("Failed to save memory to Redis", error=str(e))

    async def _load_from_redis(self):
        """Load memories from Redis."""
        if not self.redis_client:
            return

        try:
            # Get all memory keys
            memory_keys = await self.redis_client.keys("memory:*")

            for key in memory_keys:
                data = await self.redis_client.hgetall(key)

                if data:
                    memory = Memory(
                        id=data["id"],
                        guest_id=data["guest_id"],
                        content=data["content"],
                        embedding=json.loads(data["embedding"]),
                        metadata=json.loads(data["metadata"]),
                        timestamp=datetime.fromisoformat(data["timestamp"])
                    )

                    # Add to index
                    self.memories[memory.id] = memory

                    # Add to FAISS
                    embedding = np.array(memory.embedding)
                    self.index.add(np.array([embedding]))

                    # Update guest index
                    if memory.guest_id not in self.guest_index:
                        self.guest_index[memory.guest_id] = []
                    self.guest_index[memory.guest_id].append(memory.id)

            logger.info(f"Loaded {len(self.memories)} memories from Redis")

        except Exception as e:
            logger.error("Failed to load memories from Redis", error=str(e))

    # Analysis helper methods

    def _prefers_weekends(self, memories: List[Memory]) -> bool:
        """Check if guest prefers weekend stays."""
        weekend_count = 0

        for memory in memories:
            content = memory.content.lower()
            if any(day in content for day in ["sexta", "sábado", "domingo", "fim de semana"]):
                weekend_count += 1

        return weekend_count > len(memories) * 0.3

    def _avg_advance_booking(self, memories: List[Memory]) -> int:
        """Calculate average advance booking days."""
        # This would need actual booking data
        # For now, return a reasonable default
        return 14

    async def cleanup_old_memories(self, days: int = 90):
        """Remove memories older than specified days."""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        removed = 0

        for memory_id, memory in list(self.memories.items()):
            if memory.timestamp.timestamp() < cutoff:
                # Remove from FAISS (would need to rebuild index)
                # Remove from memory
                del self.memories[memory_id]

                # Remove from guest index
                if memory.guest_id in self.guest_index:
                    self.guest_index[memory.guest_id].remove(memory_id)

                # Remove from Redis
                if self.redis_client:
                    await self.redis_client.delete(f"memory:{memory_id}")

                removed += 1

        if removed > 0:
            logger.info(f"Cleaned up {removed} old memories")

            # Rebuild FAISS index
            await self._rebuild_index()

    async def _rebuild_index(self):
        """Rebuild FAISS index from current memories."""
        self.index = faiss.IndexFlatIP(self.dimension)

        embeddings = []
        for memory in self.memories.values():
            if memory.embedding:
                embeddings.append(memory.embedding)

        if embeddings:
            self.index.add(np.array(embeddings))


# Singleton instance
_memory_store = None


async def get_memory_store() -> VectorMemoryStore:
    """Get or create memory store instance."""
    global _memory_store

    if _memory_store is None:
        _memory_store = VectorMemoryStore()
        await _memory_store.initialize()

    return _memory_store
