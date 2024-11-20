from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import time

# Menu schema to define the food items at specific times
class MenuItem(BaseModel):
    menu: List[str]  # List of food_ids for the menu at a given time

class MenuPlan(BaseModel):
    # Use time strings (e.g., "6:00AM", "6:30AM") as keys, each containing a list of food_ids
    timings: Dict[str, MenuItem]

class DetoxPlan(BaseModel):
    __root__: Dict[str, MenuItem]  # Timings directly without an additional "menu" key

class DietPlan(BaseModel):
    user_id: str
    diet_name: str
    bmi: str
    desired_weight: str
    desired_calories: str
    desired_proteins: str
    menu_plan: Optional[MenuPlan]
    guidelines: List[str]
    one_day_detox_plan: Optional[Dict[str, MenuItem]]  # Matches input structure

    class Config:
        orm_mode = True


class DietPlanResponseSchema(BaseModel):
    diet_id: str  # Converted ObjectId to string
    diet_name: str
    bmi: str
    desired_weight: str
    desired_calories: str
    desired_proteins: str
    menu_plan: Optional[dict]  # Or a nested schema, depending on your design
    guidelines: List[str]
    one_day_detox_plan: Optional[dict]  # Or nested schema
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True

class UpdateDietPlanSchema(BaseModel):
    diet_name: Optional[str]
    bmi: Optional[str]
    desired_weight: Optional[str]
    desired_calories: Optional[str]
    desired_proteins: Optional[str]
    menu_plan: Optional[Dict]
    guidelines: Optional[List[str]]
    one_day_detox_plan: Optional[Dict]

    class Config:
        orm_mode = True
