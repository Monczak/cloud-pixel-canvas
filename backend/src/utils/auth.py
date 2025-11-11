from typing import Annotated, Optional

from fastapi import Cookie, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from adapters.auth import AuthAdapter, User, get_auth_adapter

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth_token")

async def get_current_user(auth_token: Optional[str] = None, auth: AuthAdapter = Depends(get_auth_adapter)) -> Optional[User]:
    if not auth_token:
        return None
    
    user = await auth.get_user_from_token(auth_token)
    return user


async def require_auth(auth_token: Annotated[str, Depends(oauth2_scheme)], auth: AuthAdapter = Depends(get_auth_adapter)) -> User:
    if not auth_token:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user = await auth.get_user_from_token(auth_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user
