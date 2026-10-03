from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole, UserStatus

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    role: UserRole
    display_name: Optional[str] = None # for contributor
    company_name: Optional[str] = None # for agency
    terms_accepted: Optional[bool] = None
    privacy_accepted: Optional[bool] = None
    terms_accepted_version: Optional[str] = None
    privacy_accepted_version: Optional[str] = None
    is_adult_confirmed: Optional[bool] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenRefresh(BaseModel):
    refresh_token: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class ContributorProfileOut(BaseModel):
    id: int
    display_name: str
    reputation_score: float

    class Config:
        from_attributes = True

class AgencyProfileOut(BaseModel):
    id: int
    company_name: str

    class Config:
        from_attributes = True

class UserOut(BaseModel):
    id: int
    email: str
    role: UserRole
    status: UserStatus
    terms_accepted_version: Optional[str] = None
    privacy_accepted_version: Optional[str] = None
    is_adult_confirmed: bool = False
    contributor_profile: Optional[ContributorProfileOut] = None
    agency_profile: Optional[AgencyProfileOut] = None

    class Config:
        from_attributes = True
