from pydantic import BaseModel
from bson import ObjectId
from typing import List, Optional
from datetime import datetime

# Define a custom PyObjectId class with JSON Schema logic
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

# Define Pydantic Schemas using the custom PyObjectId class
class Field(BaseModel):
    field_name: str
    field_type: str

class FormCreateSchema(BaseModel):
    form_name: str
    fields: List[Field]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class FormUpdateSchema(BaseModel):
    form_name: Optional[str] = None
    fields: Optional[List[Field]] = None
    updated_at: Optional[datetime] = None

class FormResponseSchema(FormCreateSchema):
    id: PyObjectId

    class Config:
        orm_mode = True
        json_encoders = {ObjectId: str}
