from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class FoodItemSchema(BaseModel):
    food_name: str  # Required field
    energy_kcal: Optional[str] = Field(None, description="Energy value in kcal.")
    quantity: Optional[str] = Field(None, description="Quantity of the food item.")
    units: Optional[str] = Field(None, description="Units in which it is measured.")
    carbohydrates: Optional[str] = Field(None, description="Carbohydrates in grams.")
    protein: Optional[str] = Field(None, description="Protein in grams.")
    fat: Optional[str] = Field(None, description="Fat in grams.")
    fiber: Optional[str] = Field(None, description="Fiber in grams.")
    calcium: Optional[str] = Field(None, description="Calcium in mg.")
    phosphorous: Optional[str] = Field(None, description="Phosphorous in mg.")
    iron: Optional[str] = Field(None, description="Iron in mg.")
    vitamin_a: Optional[str] = Field(None, description="Vitamin A in µg.")
    vitamin_b1: Optional[str] = Field(None, description="Vitamin B1 in mg.")
    vitamin_b2: Optional[str] = Field(None, description="Vitamin B2 in mg.")
    vitamin_b3: Optional[str] = Field(None, description="Vitamin B3 in mg.")
    vitamin_b9: Optional[str] = Field(None, description="Vitamin B9 in mg.")
    vitamin_c: Optional[str] = Field(None, description="Vitamin C in mg.")
    magnesium: Optional[str] = Field(None, description="Magnesium in mg.")
    sodium: Optional[str] = Field(None, description="Sodium in mg.")
    potassium: Optional[str] = Field(None, description="Potassium in mg.")

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