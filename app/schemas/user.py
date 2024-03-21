from datetime import datetime
from pydantic import BaseModel, EmailStr, constr
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    GENERAL = "GENERAL"

class UserBaseSchema(BaseModel):
    name: str
    email: EmailStr
    photo: str
    role: UserRole | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True

class UserBaseSchema(BaseModel):
    name: str
    email: EmailStr
    photo: str
    role: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    registration_id: str | None = None

    class Config:
        orm_mode = True


class CreateUserSchema(UserBaseSchema):
    password: constr(min_length=8)
    password_confirm: str
    verified: bool = False


class LoginUserSchema(BaseModel):
    email: EmailStr
    password: constr(min_length=8)


class UserResponseSchema(UserBaseSchema):
    id: str
    pass


class UserResponse(BaseModel):
    status: str
    user: UserResponseSchema

class UserRegistration(BaseModel):
    name: str
    address: str
    email: EmailStr
    phone_no: str
    previous_gym: str
    slot_preference: str
    created_at: datetime = None
    updated_at: datetime = None

    class Config:
        orm_mode = True

    def set_created_timestamp(self):
        self.created_at = datetime.utcnow()

    def set_updated_timestamp(self):
        self.updated_at = datetime.utcnow()

