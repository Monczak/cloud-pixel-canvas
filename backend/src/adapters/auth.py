from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import secrets
from typing import Dict, Optional
import uuid

from pymongo import AsyncMongoClient

from config import config

@dataclass
class User:
    user_id: str
    email: str
    username: str
    email_verified: bool
    created_at: datetime

@dataclass
class AuthToken:
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None

class AuthAdapter(ABC):
    @abstractmethod
    async def register(self, email: str, username: str, password: str) -> Dict:
        pass

    @abstractmethod
    async def verify_email(self, email: str, code: str) -> User:
        pass

    @abstractmethod
    async def login(self, email: str, password: str) -> tuple[User, AuthToken]:
        pass

    @abstractmethod
    async def logout(self, access_token: str) -> bool:
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> AuthToken:
        pass

    @abstractmethod
    async def get_user_from_token(self, access_token: str) -> Optional[User]:
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        pass

    @abstractmethod
    async def username_exists(self, username: str) -> bool:
        pass

class LocalMongoAuthAdapter(AuthAdapter):
    def __init__(self, mongo_uri: str, mongo_db: str):
        self.client = AsyncMongoClient(mongo_uri)
        self.db = self.client[mongo_db]
        self.users_collection = self.db.users
        self.tokens_collection = self.db.tokens
        self.pending_verifications = self.db.pending_verifications

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _generate_token(self) -> str:
        return secrets.token_urlsafe(32)
    
    async def username_exists(self, username: str) -> bool:
        count = await self.users_collection.count_documents(
            {"username_lower": username.lower()}
        )
        return count > 0
    
    async def register(self, email: str, username: str, password: str) -> Dict:
        email_exists = await self.users_collection.find_one({"email": email})
        if email_exists:
            raise ValueError("Email already registered")
        
        if await self.username_exists(username):
            raise ValueError("Username already taken")
            
        user_id = str(uuid.uuid4())
        password_hash = self._hash_password(password)

        await self.pending_verifications.update_one(
            {"email": email},
            {
                "$set": {
                    "user_id": user_id,
                    "email": email,
                    "username": username,
                    "username_lower": username.lower(),
                    "password_hash": password_hash,
                    "created_at": datetime.now()
                }
            },
            upsert=True,
        )

        return {"requires_verification": True, "user_id": user_id}
    
    async def verify_email(self, email: str, code: str) -> User:
        pending = await self.pending_verifications.find_one({"email": email})
        if not pending:
            raise ValueError("No pending registration found")
        
        # Locally: we don't care about the code

        user_doc = {
            "user_id": pending["user_id"],
            "email": pending["email"],
            "username": pending["username"],
            "username_lower": pending["username_lower"],
            "password_hash": pending["password_hash"],
            "email_verified": True,
            "created_at": pending["created_at"],
        }

        await self.users_collection.insert_one(user_doc)
        await self.pending_verifications.delete_one({"email": email})

        return User(
            user_id=user_doc["user_id"],
            email=user_doc["email"],
            username=user_doc["username"],
            email_verified=True,
            created_at=user_doc["created_at"],
        )
    
    async def login(self, email: str, password: str) -> tuple[User, AuthToken]:
        user_doc = await self.users_collection.find_one({"email": email})
        if not user_doc:
            raise ValueError("Invalid credentials")
        
        password_hash = self._hash_password(password)
        if user_doc["password_hash"] != password_hash:
            raise ValueError("Invalid credentials")
        
        if not user_doc.get("email_verified", False):
            raise ValueError("Email not verified")
        
        access_token = self._generate_token()
        refresh_token = self._generate_token()
        expires_at = datetime.now() + timedelta(hours=24)

        await self.tokens_collection.insert_one({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": user_doc["user_id"],
            "expires_at": expires_at,
            "created_at": datetime.now(),
        })

        user = User(
            user_id=user_doc["user_id"],
            email=user_doc["email"],
            username=user_doc["username"],
            email_verified=user_doc["email_verified"],
            created_at=user_doc["created_at"],
        )

        token = AuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=86400,  # 24 hours
        )

        return user, token
    
    async def logout(self, access_token: str) -> bool:
        result = await self.tokens_collection.delete_one({"access_token": access_token})
        return result.deleted_count > 0
    
    async def refresh_token(self, refresh_token: str) -> AuthToken:
        token_doc = await self.tokens_collection.find_one({"refresh_token": refresh_token})
        if not token_doc:
            raise ValueError("Invalid refresh token")

        access_token = self._generate_token()
        expires_at = datetime.now() + timedelta(hours=24)

        await self.tokens_collection.update_one(
            {"refresh_token": refresh_token},
            {
                "$set": {
                    "access_token": access_token,
                    "expires_at": expires_at,
                }
            },
        )

        return AuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=86400,
        )
    
    async def get_user_from_token(self, access_token: str) -> User | None:
        token_doc = await self.tokens_collection.find_one({"access_token": access_token})
        if not token_doc:
            return None

        if token_doc["expires_at"] < datetime.now():
            await self.tokens_collection.delete_one({"access_token": access_token})
            return None

        user_doc = await self.users_collection.find_one(
            {"user_id": token_doc["user_id"]}
        )
        if not user_doc:
            return None

        return User(
            user_id=user_doc["user_id"],
            email=user_doc["email"],
            username=user_doc["username"],
            email_verified=user_doc["email_verified"],
            created_at=user_doc["created_at"],
        )

    async def get_user_by_id(self, user_id: str) -> User | None:
        user_doc = await self.users_collection.find_one({"user_id": user_id})
        if not user_doc:
            return None

        return User(
            user_id=user_doc["user_id"],
            email=user_doc["email"],
            username=user_doc["username"],
            email_verified=user_doc["email_verified"],
            created_at=user_doc["created_at"],
        )


def get_auth_adapter() -> AuthAdapter:
    match config.environment:
        case "local":
            return LocalMongoAuthAdapter(config.mongo_uri, config.mongo_db)
    
    raise ValueError(f"Unknown environment: {config.environment}")
