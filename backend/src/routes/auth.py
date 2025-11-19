from typing import Optional
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field

from adapters.auth import AuthAdapter, User, get_auth_adapter
from utils.auth import get_token, get_current_user as auth_get_current_user
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
                "expires_in": token.expires_in
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    
@auth_router.post("/logout")
async def logout(response: Response, auth_token: Optional[str] = Depends(get_token), auth: AuthAdapter = Depends(get_auth_adapter)):
    if auth_token:
        await auth.logout(auth_token)

    response.delete_cookie(key="auth_token")
    return {"message": "Logged out successfully"}

@auth_router.get("/me")
async def get_current_user(user: User = Depends(auth_get_current_user)):
    return user
    
@auth_router.get("/user/{id}")
async def get_user_by_id(id: str, auth: AuthAdapter = Depends(get_auth_adapter)):
    user = await auth.get_user_by_id(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": user.user_id,
        "username": user.username,
        "created_at": user.created_at
    }
