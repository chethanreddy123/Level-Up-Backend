from datetime import datetime
from pydantic import BaseModel, EmailStr, constr, Field
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    CUSTOMER = "CUSTOMER"
    TRAINER = "TRAINER"
    DIETITIAN = "DIETITIAN"


class UserBaseSchema(BaseModel):
    name: str
    email: EmailStr
    photo: Optional[str] = None
    role: Optional[UserRole] = None
    phone_no: str = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    registration_id: Optional[str] = None

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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

    def set_created_timestamp(self):
        self.created_at = datetime.utcnow()

    def set_updated_timestamp(self):
        self.updated_at = datetime.utcnow()

# To upload user diet logs in mongodb
class UploadFoodRequest(BaseModel):
    food_name: str = Field(..., title="Food Name", description="Name of the food item")
    quantity: float = Field(..., title="Quantity", description="Quantity of the food item")
    unit: Optional[str] = Field(None, title="Unit", description="Unit of the quantity (e.g., grams, ml, pieces)")

    class Config:
        schema_extra = {
            "example": {
                "food_name": "Banana",
                "quantity": 1,
                "unit": None  # No unit needed for fruits like banana
            }
        }