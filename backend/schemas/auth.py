from typing import Optional

from pydantic import BaseModel


class UserSignup(BaseModel):
    """Schema for user signup request."""

    email: str
    password: str
    name: str


class UserProfileUpdate(BaseModel):
    """Schema for user profile update request."""

    name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None


class UserProfile(BaseModel):
    """Schema for user profile response."""

    id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
