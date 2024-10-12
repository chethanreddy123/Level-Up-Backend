# app/schemas/workout_plan.py

from pydantic import BaseModel
from typing import Optional, List

# Schema for individual workout plan days
class WorkoutDaySchema(BaseModel):
    exercises: List[str]

# Schema for the complete workout plan
class WorkoutPlanSchema(BaseModel):
    start_date: str  # Use str instead of datetime
    end_date: str    # Use str instead of datetime
    current_weight: float
    end_weight: float
    Monday: Optional[WorkoutDaySchema] = None
    Tuesday: Optional[WorkoutDaySchema] = None
    Wednesday: Optional[WorkoutDaySchema] = None
    Thursday: Optional[WorkoutDaySchema] = None
    Friday: Optional[WorkoutDaySchema] = None
    Saturday: Optional[WorkoutDaySchema] = None
    Sunday: Optional[WorkoutDaySchema] = None

# Schema for updating the workout plan
class WorkoutPlanUpdateSchema(BaseModel):
    start_date: Optional[str] = None  # Use str instead of datetime
    end_date: Optional[str] = None    # Use str instead of datetime
    current_weight: Optional[float] = None
    end_weight: Optional[float] = None
    Monday: Optional[WorkoutDaySchema] = None
    Tuesday: Optional[WorkoutDaySchema] = None
    Wednesday: Optional[WorkoutDaySchema] = None
    Thursday: Optional[WorkoutDaySchema] = None
    Friday: Optional[WorkoutDaySchema] = None
    Saturday: Optional[WorkoutDaySchema] = None
    Sunday: Optional[WorkoutDaySchema] = None
