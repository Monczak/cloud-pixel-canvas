from typing import Optional

from fastapi import Cookie, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from adapters.auth import AuthAdapter, User, get_auth_adapter

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth_token", auto_error=False)

async def get_token(
    bearer_token: Optional[str] = Depends(oauth2_scheme),
    cookie_token: Optional[str] = Cookie(default=None, alias="auth_token"),
) -> Optional[str]:
    return bearer_token or cookie_token

async def get_current_user(
        token: str = Depends(get_token),
        auth: AuthAdapter = Depends(get_auth_adapter)
) -> Optional[User]:
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user = await auth.get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user
