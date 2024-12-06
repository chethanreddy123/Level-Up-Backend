from fastapi import File, UploadFile
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class FoodItemSchema(BaseModel):
    food_name: str  # Required field
    energy_kcal: Optional[str] = None
    quantity: Optional[str] = None
    units: Optional[str] = None
    carbohydrates: Optional[str] = None
    protein: Optional[str] = None
    fat: Optional[str] = None
    fiber: Optional[str] = None
    calcium: Optional[str] = None
    phosphorous: Optional[str] = None
    iron: Optional[str] = None
    vitamin_a: Optional[int] = None
    vitamin_b1: Optional[str] = None
    vitamin_b2: Optional[str] = None
    vitamin_b3: Optional[str] = None
    vitamin_b6: Optional[str] = None
    vitamin_b9: Optional[str] = None
    vitamin_c: Optional[str] = None
    magnesium: Optional[str] = None
    sodium: Optional[str] = None
    potassium: Optional[str] = None
    food_image_url: Optional[str] = None,
    class Config:
        orm_mode = True

# Menu schema to define the food items at specific times
class MenuItem(BaseModel):
    menu: List[str]  # List of food_ids for the menu at a given time

class MenuPlan(BaseModel):
    # Use time strings (e.g., "6:00AM", "6:30AM") as keys, each containing a list of food_ids
    timings: Dict[str, MenuItem]

class DetoxPlan(BaseModel):
    # Similar structure to the menu plan, for the detox day
    menu: Dict[str, MenuItem]

class DietPlan(BaseModel):
    diet_name: str  # Name of the diet plan
    bmi: str  # BMI of the user
    desired_weight: str  # Desired weight (e.g., "55 kg")
    desired_calories: str  # Desired daily calories (e.g., "1700 kcal/day")
    desired_proteins: str  # Desired daily proteins (e.g., "50 gms/day")
    
    menu_plan: MenuPlan  # The user's menu plan (e.g., meals throughout the day)
    
    guidelines: List[str]  # Guidelines for following the diet plan
    
    one_day_detox_plan: DetoxPlan  # The detox plan for a day

    class Config:
        orm_mode = True