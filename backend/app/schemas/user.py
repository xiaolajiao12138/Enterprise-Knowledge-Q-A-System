from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    role: str = Field(default="employee", description="角色: admin / employee")
    is_active: bool = Field(default=True, description="是否启用")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100, description="登录密码")


class UserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


class PasswordReset(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None
