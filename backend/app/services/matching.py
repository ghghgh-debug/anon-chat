"""
Matching service — Redis-based matchmaking queue.

Implements the two-sided filter matching algorithm:
1. User requests a match with filters (gender, age range, topic).
2. We scan existing waiting rooms in Redis.
3. If a mutual match is found (both sides' filters satisfy each other), pair them.
4. If no match, create a new waiting room.
5. Notify both users via Centrifugo when matched.
"""

import json
import uuid
import time
from typing import Optional, Tuple
import redis.asyncio as aioredis

from app.core.config import get_settings
from app.services.centrifugo import centrifugo_service


ROOM_PREFIX = "room:"
WAITING_CHANNEL_PREFIX = "waiting:"


class MatchingService:
    def __init__(self):
        self.settings = get_settings()
        self.redis: Optional[aioredis.Redis] = None

    async def init_redis(self):
        if self.redis is None:
            self.redis = aioredis.from_url(
                self.settings.REDIS_URL,
                decode_responses=True,
            )

    async def close(self):
        if self.redis:
            await self.redis.close()

    def _check_mutual_match(self, seeker: dict, candidate: dict) -> bool:
        """
        Two-sided matching check:
        - Seeker's desired gender matches candidate's actual gender (or 'any')
        - Candidate's desired gender matches seeker's actual gender (or 'any')
        - Seeker's desired age category matches candidate's actual category (or 'any')
        - Candidate's desired age category matches seeker's actual category (or 'any')
        - Seeker's age is within candidate's age range
        - Candidate's age is within seeker's age range
        - At least one topic overlaps (if topics provided)
        """
        # Gender check (bidirectional)
        if seeker.get("find_gender", "any") != "any":
            if seeker["find_gender"] != candidate["gender"]:
                return False

        if candidate.get("find_gender", "any") != "any":
            if candidate["find_gender"] != seeker["gender"]:
                return False

        # Age category check (bidirectional)
        if seeker.get("find_age_category", "any") != "any":
            if seeker["find_age_category"] != candidate.get("age_category", "adult"):
                return False

        if candidate.get("find_age_category", "any") != "any":
            if candidate["find_age_category"] != seeker.get("age_category", "adult"):
                return False

        # Age check (bidirectional)
        seeker_age = seeker.get("age", 0)
        candidate_age = candidate.get("age", 0)

        if seeker.get("age_from") and candidate_age < seeker["age_from"]:
            return False
        if seeker.get("age_to") and candidate_age > seeker["age_to"]:
            return False

        if candidate.get("age_from") and seeker_age < candidate["age_from"]:
            return False
        if candidate.get("age_to") and seeker_age > candidate["age_to"]:
            return False

        # Topic overlap (at least one shared topic)
        seeker_topics = set(seeker.get("topics", []))
        candidate_topics = set(candidate.get("topics", []))
        if seeker_topics and candidate_topics:
            if not seeker_topics.intersection(candidate_topics):
                return False

        # Chat language is deliberately separate from the interface language.
        if seeker.get("chat_language", "ru") != candidate.get("chat_language", "ru"):
            return False

        # VIP check: if seeker wants VIP, candidate must be premium too
        if seeker.get("vip_only") and not candidate.get("is_premium"):
            return False
        if candidate.get("vip_only") and not seeker.get("is_premium"):
            return False

        return True

    async def find_or_create_room(
        self,
        user_id: int,
        nickname: str,
        gender: str,
        age: int,
        age_category: str = "adult",
        find_gender: str = "any",
        find_age_category: str = "any",
        age_from: int = 14,
        age_to: int = 99,
        topics: list[str] = None,
        chat_language: str = "ru",
        is_premium: bool = False,
        vip_only: bool = False,
        blacklist: list[int] = None,
    ) -> Tuple[Optional[str], Optional[str], bool]:
        """
        Find a matching room or create a new one.

        Returns:
            (room_key, centrifugo_token, matched)
            - If matched: room_key and token for the matched channel, matched=True
            - If waiting: room_key for status polling, token for waiting notification channel, matched=False
        """
        await self.init_redis()

        seeker = {
            "id": user_id,
            "nickname": nickname,
            "gender": gender,
            "age": age,
            "age_category": age_category,
            "find_gender": find_gender,
            "find_age_category": find_age_category,
            "age_from": age_from,
            "age_to": age_to,
            "topics": topics or [],
            "chat_language": chat_language,
            "is_premium": is_premium,
            "vip_only": vip_only,
        }

        blacklist_set = set(blacklist or [])

        # Scan all waiting rooms
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=f"{ROOM_PREFIX}*", count=100)
            for room_key in keys:
                room_data = await self.redis.get(room_key)
                if not room_data:
                    continue

                room = json.loads(room_data)
                if room["status"] != "waiting":
                    continue

                candidate = room["partners"][0]

                # Don't match with self
                if candidate["id"] == user_id:
                    continue

                # Don't match with blacklisted users
                if candidate["id"] in blacklist_set:
                    continue

                # Two-sided filter check
                if not self._check_mutual_match(seeker, candidate):
                    continue

                # --- MATCH FOUND ---
                # Generate tokens for both users
                channel = f"chat:{room_key.replace(ROOM_PREFIX, '')}"
                token_seeker = centrifugo_service.generate_subscription_token(user_id, channel)
                token_candidate = centrifugo_service.generate_subscription_token(candidate["id"], channel)

                # Update room
                seeker["token"] = token_seeker
                candidate["token"] = token_candidate
                room["status"] = "matched"
                room["partners"].append(seeker)
                room["matched_at"] = time.time()

                await self.redis.set(
                    room_key,
                    json.dumps(room),
                    ex=self.settings.CENTRIFUGO_TOKEN_TTL,
                )

                # Notify the waiting user via their waiting channel
                await centrifugo_service.publish(
                    f"{WAITING_CHANNEL_PREFIX}{candidate['id']}",
                    {
                        "event": "matched",
                        "room_key": room_key,
                        "channel": channel,
                        "token": token_candidate,
                        "partner": {
                            "nickname": seeker["nickname"],
                            "age": seeker["age"],
                            "gender": seeker["gender"],
                            "is_premium": seeker["is_premium"],
                        },
                    },
                )

                return room_key, token_seeker, True

            if cursor == 0:
                break

        # --- NO MATCH: Create a new waiting room ---
        room_id = str(uuid.uuid4())[:8]
        room_key = f"{ROOM_PREFIX}{room_id}"

        # Generate a waiting notification token so client can be notified of match
        waiting_channel = f"{WAITING_CHANNEL_PREFIX}{user_id}"
        waiting_token = centrifugo_service.generate_subscription_token(user_id, waiting_channel)

        room = {
            "status": "waiting",
            "created_at": time.time(),
            "partners": [seeker],
        }

        await self.redis.set(
            room_key,
            json.dumps(room),
            ex=self.settings.ROOM_TTL_SECONDS,
        )

        return room_key, waiting_token, False

    async def cancel_search(self, user_id: int) -> bool:
        """Cancel a user's pending search by removing their waiting room."""
        await self.init_redis()

        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=f"{ROOM_PREFIX}*", count=100)
            for room_key in keys:
                room_data = await self.redis.get(room_key)
                if not room_data:
                    continue
                room = json.loads(room_data)
                if room["status"] == "waiting" and room["partners"][0]["id"] == user_id:
                    await self.redis.delete(room_key)
                    return True
            if cursor == 0:
                break
        return False

    async def get_room(self, room_key: str) -> Optional[dict]:
        """Get room data by key."""
        await self.init_redis()
        data = await self.redis.get(room_key)
        if data:
            return json.loads(data)
        return None

    async def set_chat_id(self, room_key: str, chat_id: int) -> None:
        """Attach the persistent chat id so both clients use one live channel."""
        await self.init_redis()
        data = await self.redis.get(room_key)
        if not data:
            return
        room = json.loads(data)
        room["chat_id"] = chat_id
        await self.redis.set(room_key, json.dumps(room), ex=self.settings.CENTRIFUGO_TOKEN_TTL)

    async def get_online_count(self) -> int:
        """
        Get approximate online user count.
        Uses Redis keys with TTL set by heartbeat pings from clients.
        """
        await self.init_redis()
        cursor = 0
        count = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match="online:*", count=200)
            count += len(keys)
            if cursor == 0:
                break
        return count

    async def heartbeat(self, user_id: int) -> None:
        """Record a user heartbeat for online presence tracking."""
        await self.init_redis()
        await self.redis.set(f"online:{user_id}", "1", ex=30)

    async def remove_online(self, user_id: int) -> None:
        """Remove user from online tracking."""
        await self.init_redis()
        await self.redis.delete(f"online:{user_id}")


matching_service = MatchingService()
