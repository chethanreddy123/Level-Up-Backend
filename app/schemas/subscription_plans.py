from pydantic import BaseModel
from typing import Literal, Optional

class GymPlanSchema(BaseModel):
    plan_name: str
    duration: Literal[1, 3, 6, 12]  # Only allows 1, 3, 6, or 12 months
    price: float
    
    class Config:
        orm_mode = True

class GymPlanUpdateSchema(BaseModel):
    plan_name: Optional[str] = None
    duration: Optional[Literal[1, 3, 6, 12]] = None  # Optional duration field
    price: Optional[float] = None
    
    class Config:
        orm_mode = True