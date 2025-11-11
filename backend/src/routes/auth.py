from typing import Annotated, Optional
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field

from adapters.auth import AuthAdapter, get_auth_adapter
from utils.auth import oauth2_scheme
from config import config

auth_router = APIRouter(prefix="/auth")

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=20)
    password: str

class VerifyRequest(BaseModel):
    email: EmailStr
    code: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

@auth_router.post("/register")
async def register(request: RegisterRequest, auth: AuthAdapter = Depends(get_auth_adapter)):
    try:
        result = await auth.register(email=request.email, username=request.username, password=request.password)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@auth_router.post("/verify")
async def verify_email(request: VerifyRequest, response: Response, auth: AuthAdapter = Depends(get_auth_adapter)):
    try:
        user = await auth.verify_email(email=request.email, code=request.code) # [TODO] Log in automatically after verifying
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@auth_router.post("/login")
async def login(request: LoginRequest, response: Response, auth: AuthAdapter = Depends(get_auth_adapter)):
    try:
        user, token = await auth.login(email=request.email, password=request.password)

        response.set_cookie(
            key="auth_token",
            value=token.access_token,
            httponly=True,
            secure=not config.is_local(),
            samesite="lax",
            max_age=token.expires_in,
        )

        if token.refresh_token:
            response.set_cookie(
                key="refresh_token",
                value=token.refresh_token,
                httponly=True,
                secure=not config.is_local(),
                samesite="lax",
                max_age=token.expires_in,
            )

        return {
            "user": {
                "user_id": user.user_id,
                "email": user.email,
                "username": user.username,
            },
            "token": {
                "access_token": token.access_token,
                "refresh_token": token.refresh_token,
                "expires_in": token.expires_in
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    
@auth_router.post("/logout")
async def logout(response: Response, auth_token: Annotated[str, Depends(oauth2_scheme)], auth: AuthAdapter = Depends(get_auth_adapter)):
    if auth_token:
        await auth.logout(auth_token)

    response.delete_cookie(key="auth_token")
    return {"message": "Logged out successfully"}

@auth_router.get("/me")
async def get_current_user(auth_token: Annotated[str, Depends(oauth2_scheme)], auth: AuthAdapter = Depends(get_auth_adapter)):
    if not auth_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = await auth.get_user_from_token(auth_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {
        "user_id": user.user_id,
        "email": user.email,
        "username": user.username,
        "email_verified": user.email_verified,
    }

@auth_router.post("/refresh")
async def refresh_token( request: RefreshRequest, response: Response, auth: AuthAdapter = Depends(get_auth_adapter)):
    try:
        token = await auth.refresh_token(request.refresh_token)
        
        response.set_cookie(
            key="auth_token",
            value=token.access_token,
            httponly=True,
            secure=not config.is_local(),
            samesite="lax",
            max_age=token.expires_in,
        )
        
        return {
            "access_token": token.access_token,
            "expires_in": token.expires_in,
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
