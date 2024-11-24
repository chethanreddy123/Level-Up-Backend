# app/schemas/screening.py

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from enum import Enum

# Enums for select box fields
class FoodPreferences(str, Enum):
    VEGETARIAN = "vegetarian"
    NON_VEGETARIAN = "non-vegetarian"
    OVO_VEGETARIAN = "ovo vegetarian"
    JAIN_FOOD = "jain food"

class YesNo(str, Enum):
    YES = "Yes"
    NO = "No"

class TrainingIntensity(int, Enum):
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10

class ScreeningFormSchema(BaseModel):
    user_id : str
    # Text fields
    occupation: Optional[str] = None
    nutrition_goals: Optional[str] = None
    breakfast: Optional[str] = None
    snacks: Optional[str] = None
    lunch: Optional[str] = None
    dinner: Optional[str] = None
    blood_pressure_check: Optional[str] = None
    drink_or_smoke: Optional[str] = None
    training_goal: Optional[str] = None
    training_expectations: Optional[str] = None
    blood_glucose_level: Optional[str] = None
    surgeries: Optional[str] = None
    workout_time: Optional[str] = None
    lifting_experience: Optional[str] = None
    current_water_intake: Optional[str] = None
    steroids_or_drugs: Optional[str] = None
    supplements_usage: Optional[str] = None
    lowest_weight: Optional[float] = None
    highest_weight: Optional[float] = None
    dizziness_balance_loss: Optional[str] = None
    food_allergies: Optional[str] = None
    
    # Number fields
    height: Optional[float] = None
    weight: Optional[float] = None
    age: Optional[int] = None
    workout_days_per_week: Optional[int] = None

    # # Select Box fields
    # food_preferences: Optional[FoodPreferences] = None
    # skip_meals: Optional[YesNo] = None
    # dine_out_frequency: Optional[str] = None
    # heart_trouble: Optional[YesNo] = None
    # chest_pain: Optional[YesNo] = None
    # injuries: Optional[YesNo] = None
    # committed: Optional[YesNo] = None
    # gap_in_lifting: Optional[YesNo] = None
    # back_or_knees_problem: Optional[YesNo] = None
    # steroids_or_drugs: Optional[YesNo] = None
    # supplements_usage: Optional[YesNo] = None
    # okay_with_six_day_workout: Optional[YesNo] = None
    
    # Select Box with numerical values (for rating or scale)
    training_intensity: Optional[TrainingIntensity] = None

    class Config:
        orm_mode = True
