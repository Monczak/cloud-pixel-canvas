from abc import ABC, abstractmethod
import base64
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import hmac
import secrets
from typing import Dict, Optional
import uuid

from botocore.exceptions import ClientError
from keycloak import KeycloakAdmin, KeycloakError, KeycloakOpenID
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
    async def refresh_token(self, email: str, refresh_token: str) -> tuple[User, AuthToken]:
        pass

    @abstractmethod
    async def logout(self, access_token: str) -> bool:
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

class CognitoAuthAdapter(AuthAdapter):
    def __init__(self, cognito_client):
        self.cognito = cognito_client
        self.user_pool_id = config.cognito_user_pool_id
        self.client_id = config.cognito_client_id
        self.client_secret = config.cognito_client_secret
    
    def _get_secret_hash(self, username: str) -> str:
        message = username + self.client_id
        digest = hmac.new(
            str(self.client_secret).encode("utf-8"),
            msg=str(message).encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(digest).decode()

    async def username_exists(self, username: str) -> bool:
        try:
            response = await self.cognito.list_users(
                UserPoolId=self.user_pool_id,
                Filter=f'preferred_username = "{username}"'
            )
            return len(response.get("Users", [])) > 0
        except ClientError as e:
            print(f"Error checking username: {e}")
            return False
        
    async def register(self, email: str, username: str, password: str) -> Dict:
        if await self.username_exists(username):
            raise ValueError("Username already taken")
        
        try:
            response = await self.cognito.sign_up(
                ClientId=self.client_id,
                SecretHash=self._get_secret_hash(email),
                Username=email,
                Password=password,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "preferred_username", "Value": username}
                ]
            )

            return {
                "requires_verification": True,
                "user_id": response["UserSub"]
            }
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "UsernameExistsException":
                raise ValueError("Email already registered")
            elif error_code == "InvalidPasswordException":
                raise ValueError("Password does not meet requirements")
            else:
                raise ValueError(f"Registration failed: {e.response["Error"]["Message"]}")
    
    async def verify_email(self, email: str, code: str) -> User:
        try:
            await self.cognito.confirm_sign_up(
                ClientId=self.client_id,
                SecretHash=self._get_secret_hash(email),
                Username=email,
                ConfirmationCode=code
            )
            
            response = await self.cognito.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=email
            )
            
            username = email
            user_id = None
            created_at = response.get("UserCreateDate", datetime.now())
            
            for attr in response.get("UserAttributes", []):
                if attr["Name"] == "preferred_username":
                    username = attr["Value"]
                elif attr["Name"] == "sub":
                    user_id = attr["Value"]
            
            return User(
                user_id=user_id or response["Username"],
                email=email,
                username=username,
                email_verified=True,
                created_at=created_at
            )
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "CodeMismatchException":
                raise ValueError("Invalid verification code")
            elif error_code == "ExpiredCodeException":
                raise ValueError("Verification code has expired")
            else:
                raise ValueError(f"Verification failed: {e.response["Error"]["Message"]}")
    
    async def login(self, email: str, password: str) -> tuple[User, AuthToken]:
        try:
            response = await self.cognito.initiate_auth(
                ClientId=self.client_id,
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters={
                    "USERNAME": email,
                    "PASSWORD": password,
                    "SECRET_HASH": self._get_secret_hash(email),
                }
            )
            
            auth_result = response["AuthenticationResult"]
            access_token = auth_result["AccessToken"]
            refresh_token = auth_result.get("RefreshToken")
            
            user_response = await self.cognito.get_user(AccessToken=access_token)
            
            username = email
            user_id = None
            email_verified = False
            
            for attr in user_response.get("UserAttributes", []):
                if attr["Name"] == "preferred_username":
                    username = attr["Value"]
                elif attr["Name"] == "sub":
                    user_id = attr["Value"]
                elif attr["Name"] == "email_verified":
                    email_verified = attr["Value"].lower() == "true"
            
            user = User(
                user_id=user_id or user_response["Username"],
                email=email,
                username=username,
                email_verified=email_verified,
                created_at=datetime.now()
            )
            
            token = AuthToken(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=auth_result.get("ExpiresIn", 3600)
            )
            
            return user, token
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NotAuthorizedException":
                raise ValueError("Invalid credentials")
            elif error_code == "UserNotConfirmedException":
                raise ValueError("Email not verified")
            else:
                raise ValueError(f"Login failed: {e.response["Error"]["Message"]}")
    
    async def refresh_token(self, email: str, refresh_token: str) -> tuple[User, AuthToken]:
        try:
            response = await self.cognito.initiate_auth(
                ClientId=self.client_id,
                AuthFlow="REFRESH_TOKEN_AUTH",
                AuthParameters={
                    "REFRESH_TOKEN": refresh_token,
                    "SECRET_HASH": self._get_secret_hash(email),
                }
            )

            auth_result = response["AuthenticationResult"]
            access_token = auth_result["AccessToken"]
            new_refresh_token = auth_result.get("RefreshToken") # Cognito may rotate the token or not

            user = await self.get_user_from_token(access_token)
            if not user:
                raise ValueError("Failed to retrieve user info from refreshed token")
            
            token = AuthToken(
                access_token=access_token,
                refresh_token=new_refresh_token,
                expires_in=auth_result.get("ExpiredIn", 3600)
            )

            return user, token
        except ClientError as e:
            raise ValueError(f"Token refresh failed: {e.response["Error"]["Message"]}")

    async def logout(self, access_token: str) -> bool:
        try:
            await self.cognito.global_sign_out(AccessToken=access_token)
            return True
        except ClientError as e:
            print(f"Logout error: {e}")
            return False
            
    async def get_user_from_token(self, access_token: str) -> Optional[User]:
        try:
            response = await self.cognito.get_user(AccessToken=access_token)
            
            username = None
            user_id = None
            email = None
            email_verified = False
            
            for attr in response.get("UserAttributes", []):
                if attr["Name"] == "preferred_username":
                    username = attr["Value"]
                elif attr["Name"] == "sub":
                    user_id = attr["Value"]
                elif attr["Name"] == "email":
                    email = attr["Value"]
                elif attr["Name"] == "email_verified":
                    email_verified = attr["Value"].lower() == "true"
            
            return User(
                user_id=user_id or response["Username"],
                email=email or response["Username"],
                username=username or email or response["Username"],
                email_verified=email_verified,
                created_at=datetime.now()
            )
        except ClientError as e:
            print(f"Token validation error: {e}")
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        try:
            response = await self.cognito.list_users(
                UserPoolId=self.user_pool_id,
                Filter=f'sub = "{user_id}"'
            )
            
            users = response.get("Users", [])
            if not users:
                return None
            
            user_data = users[0]
            username = user_id
            email = user_data.get("Username", "")
            created_at = user_data.get("UserCreateDate", datetime.now())
            
            for attr in user_data.get("Attributes", []):
                if attr["Name"] == "preferred_username":
                    username = attr["Value"]
                elif attr["Name"] == "email":
                    email = attr["Value"]
            
            return User(
                user_id=user_id,
                email=email,
                username=username,
                email_verified=True,
                created_at=created_at
            )
        except ClientError as e:
            print(f"Error getting user by id: {e}")
            return None

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
        
        now = datetime.now()
        expires_at = now + timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        await self.tokens_collection.insert_one({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": user_doc["user_id"],
            "expires_at": expires_at,
            "refresh_expires_at": refresh_expires_at,
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
    
    async def refresh_token(self, email: str, refresh_token: str) -> tuple[User, AuthToken]:
        token_doc = await self.tokens_collection.find_one({"refresh_token": refresh_token})
        if not token_doc:
            raise ValueError("Invalid refresh token")
        
        if token_doc.get("refresh_expires_at") and token_doc["refresh_expires_at"] < datetime.now():
            await self.tokens_collection.delete_one({"_id": token_doc["_id"]})
            raise ValueError("Refresh token expired")
        
        user_doc = await self.users_collection.find_one({"user_id": token_doc["user_id"]})
        if not user_doc:
            raise ValueError("User not found")
        
        new_access_token = self._generate_token()
        new_expires_at = datetime.now() + timedelta(hours=1)
        
        await self.tokens_collection.update_one(
            {"_id": token_doc["_id"]},
            {
                "$set": {
                    "access_token": new_access_token,
                    "expires_at": new_expires_at
                }
            }
        )

        user = User(
            user_id=user_doc["user_id"],
            email=user_doc["email"],
            username=user_doc["username"],
            email_verified=user_doc["email_verified"],
            created_at=user_doc["created_at"],
        )

        token = AuthToken(
            access_token=new_access_token,
            refresh_token=None, # Do not rotate refresh token for now
            expires_in=3600
        )

        return user, token

    async def logout(self, access_token: str) -> bool:
        result = await self.tokens_collection.delete_one({"access_token": access_token})
        return result.deleted_count > 0
    
    async def get_user_from_token(self, access_token: str) -> User | None:
        token_doc = await self.tokens_collection.find_one({"access_token": access_token})
        if not token_doc:
            return None

        if token_doc["expires_at"] < datetime.now():
            # Allow refresh token to persist
            # await self.tokens_collection.delete_one({"access_token": access_token})
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

class KeycloakAuthAdapter(AuthAdapter):
    def __init__(self):
        self.server_url = config.keycloak_url
        self.realm = config.keycloak_realm
        self.client_id = config.keycloak_client_id
        self.client_secret = config.keycloak_client_secret

        self.openid = KeycloakOpenID(
            server_url=self.server_url,
            client_id=self.client_id,
            realm_name=self.realm,
            client_secret_key=self.client_secret,
            verify=True,
        )

    async def _get_admin(self, realm: str = "master") -> KeycloakAdmin:
        return KeycloakAdmin(
            server_url=self.server_url,
            username=config.keycloak_admin_username,
            password=config.keycloak_admin_password,
            realm_name=realm,
            user_realm_name="master", # Admin users usually live in master
            verify=True,
        )

    async def register(self, email: str, username: str, password: str) -> Dict:
        try:
            admin = await self._get_admin(realm=self.realm)
            user_id = await admin.a_create_user({
                "email": email,
                "username": username,
                "enabled": True,
                "emailVerified": True,
                # [HACK] Working around https://github.com/keycloak/keycloak/issues/36108
                "requiredActions": [],
                "firstName": username,
                "lastName": username,
            })
            
            await admin.a_set_user_password(user_id, password, temporary=False)
            
            return {
                "requires_verification": False,
                "user_id": user_id
            }
        except KeycloakError as e:
            if e.response_code == 409:
                raise ValueError("Username or email already exists")
            raise ValueError(f"Registration failed: {e}")

    async def verify_email(self, email: str, code: str) -> User:
        raise NotImplementedError("Email verification out of scope for KeycloakAuthAdapter")

    async def login(self, email: str, password: str) -> tuple[User, AuthToken]:
        try:
            token_data = await self.openid.a_token(username=email, password=password)
            user_info = await self.openid.a_userinfo(token_data["access_token"])
            
            user = User(
                user_id=user_info["sub"],
                email=user_info.get("email", ""),
                username=user_info.get("preferred_username", ""),
                email_verified=user_info.get("email_verified", False),
                created_at=datetime.now()
            )
            
            token = AuthToken(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                expires_in=token_data.get("expires_in")
            )
            
            return user, token
        except KeycloakError as e:
            raise ValueError("Invalid credentials")

    async def refresh_token(self, email: str, refresh_token: str) -> tuple[User, AuthToken]:
        try:
            token_data = await self.openid.a_refresh_token(refresh_token)
            
            user = await self.get_user_from_token(token_data["access_token"])
            if not user:
                raise ValueError("Could not validate refreshed user")

            token = AuthToken(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                expires_in=token_data.get("expires_in")
            )
            return user, token
        except Exception:
            raise ValueError("Token refresh failed")

    async def logout(self, access_token: str) -> bool:
        try:
            await self.openid.a_logout(access_token)
            return True
        except Exception:
            return False

    async def get_user_from_token(self, access_token: str) -> Optional[User]:
        try:
            user_info = await self.openid.a_userinfo(access_token)
            return User(
                user_id=user_info["sub"],
                email=user_info.get("email", ""),
                username=user_info.get("preferred_username", ""),
                email_verified=user_info.get("email_verified", False),
                created_at=datetime.now()
            )
        except Exception:
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        try:
            admin = await self._get_admin(realm=self.realm)
            user_data = await admin.a_get_user(user_id)
            if not user_data:
                return None
            
            return User(
                user_id=user_data["id"],
                email=user_data.get("email", ""),
                username=user_data.get("username", ""),
                email_verified=user_data.get("emailVerified", False),
                created_at=datetime.fromtimestamp(user_data.get("createdTimestamp", 0) / 1000)
            )
        except Exception:
            return None
        
    async def username_exists(self, username: str) -> bool:
        try:
            admin = await self._get_admin(realm=self.realm)
            users = await admin.a_get_users({"username": username})
            return len(users) > 0
        except Exception:
            return False

def get_auth_adapter() -> AuthAdapter:
    from deps import manager

    if not manager.auth:
        raise RuntimeError("Auth adapter not initialized")
    return manager.auth
