# app/schemas/diet.py

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime

# Schema for a food item
class FoodItemSchema(BaseModel):
    food_name: str
    energy_kcal: float = Field(..., description="Energy value in kcal.")
    quantity: str = Field(..., description="Quantity of the food item.")
    carbohydrates: float = Field(..., description="Carbohydrates in grams.")
    protein: float = Field(..., description="Protein in grams.")
    fat: float = Field(..., description="Fat in grams.")
    fiber: float = Field(..., description="Fiber in grams.")
    calcium: float = Field(..., description="Calcium in mg.")
    phosphorous: float = Field(..., description="Phosphorous in mg.")
    iron: float = Field(..., description="Iron in mg.")
    vitamin_a: float = Field(..., description="Vitamin A in µg.")
    vitamin_b1: float = Field(..., description="Vitamin B1 in mg.")
    vitamin_b2: float = Field(..., description="Vitamin B2 in mg.")
    vitamin_b3: float = Field(..., description="Vitamin B3 in mg.")
    vitamin_b9: float = Field(..., description="Vitamin B9 in mg.")
    vitamin_c: float = Field(..., description="Vitamin C in mg.")
    magnesium: float = Field(..., description="Magnesium in mg.")
    sodium: float = Field(..., description="Sodium in mg.")
    potassium: float = Field(..., description="Potassium in mg.")

    class Config:
        orm_mode = True

# Schema for a diet plan's details
class DietPlanSchema(BaseModel):
    user_id: Optional[str] = None  # User ID as a string
    start_date: Optional[str] = Field(None, description="Start date of the diet plan in 'YYYY-MM-DD' format.")
    end_date: Optional[str] = Field(None, description="End date of the diet plan in 'YYYY-MM-DD' format.")
    desired_weight: Optional[float] = Field(None, description="Target weight in kgs.")
    desired_calories: Optional[float] = Field(None, description="Target daily calories intake in kcal.")
    desired_proteins: Optional[float] = Field(None, description="Target daily protein intake in grams.")
    meals: Optional[List[FoodItemSchema]] = Field([], description="List of meals included in the diet plan.")
    created_at: Optional[str] = None  # Creation timestamp as a string
    updated_at: Optional[str] = None  # Update timestamp as a string

    class Config:
        orm_mode = True

# Response schema for a diet plan
class DietPlanResponseSchema(DietPlanSchema):
    id: Optional[str] = Field(None, description="Diet Plan ID")

    class Config:
        orm_mode = True
