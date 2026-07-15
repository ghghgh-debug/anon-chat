"""
Centrifugo integration service.

Handles:
- JWT token generation for client connections (scoped to specific channels)
- Publishing messages to channels via Centrifugo HTTP API
- Presence tracking
"""

import time
import json
from typing import Optional
import httpx
from jose import jwt

from app.core.config import get_settings


class CentrifugoService:
    def __init__(self):
        self.settings = get_settings()
        self.api_url = f"{self.settings.CENTRIFUGO_URL}/api"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"apikey {self.settings.CENTRIFUGO_API_KEY}",
        }

    def generate_connection_token(self, user_id: int, channel: str) -> str:
        """
        Generate a JWT token for a user to connect to Centrifugo
        and subscribe to a specific channel.
        
        The token is scoped: the user can ONLY subscribe to the specified channel.
        This prevents users from eavesdropping on other chat rooms.
        """
        now = int(time.time())
        claims = {
            "sub": str(user_id),
            "exp": now + self.settings.CENTRIFUGO_TOKEN_TTL,
            "iat": now,
            "channels": [channel],  # Channel-level scoping for security
        }
        return jwt.encode(
            claims,
            self.settings.CENTRIFUGO_HMAC_SECRET,
            algorithm="HS256",
        )

    def generate_subscription_token(self, user_id: int, channel: str) -> str:
        """
        Generate a subscription token for a specific channel.
        This ensures the user can only subscribe to their own chat room.
        """
        now = int(time.time())
        claims = {
            "sub": str(user_id),
            "channel": channel,
            "exp": now + self.settings.CENTRIFUGO_TOKEN_TTL,
            "iat": now,
        }
        return jwt.encode(
            claims,
            self.settings.CENTRIFUGO_HMAC_SECRET,
            algorithm="HS256",
        )

    async def publish(self, channel: str, data: dict) -> bool:
        """Publish a message to a Centrifugo channel via HTTP API."""
        payload = {
            "method": "publish",
            "params": {
                "channel": channel,
                "data": data,
            },
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                timeout=5.0,
            )
            return resp.status_code == 200

    async def broadcast(self, channels: list[str], data: dict) -> bool:
        """Broadcast a message to multiple Centrifugo channels."""
        payload = {
            "method": "broadcast",
            "params": {
                "channels": channels,
                "data": data,
            },
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                timeout=5.0,
            )
            return resp.status_code == 200

    async def presence(self, channel: str) -> dict:
        """Get presence information for a channel (who is currently subscribed)."""
        payload = {
            "method": "presence",
            "params": {
                "channel": channel,
            },
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                timeout=5.0,
            )
            if resp.status_code == 200:
                return resp.json().get("result", {})
            return {}

    async def disconnect_user(self, user_id: int) -> bool:
        """Force-disconnect a user from Centrifugo (e.g. on ban)."""
        payload = {
            "method": "disconnect",
            "params": {
                "user": str(user_id),
            },
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                timeout=5.0,
            )
            return resp.status_code == 200


centrifugo_service = CentrifugoService()
