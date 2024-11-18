# app/schemas/workout_plan.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum
from datetime import date

# Schema for individual workout plan days
class WorkoutDaySchema(BaseModel):
    exercises: List[str]



# # Schema for the complete workout plan
# class WorkoutPlanSchema(BaseModel):
#     start_date: str  # Use str instead of datetime
#     end_date: str    # Use str instead of datetime
#     current_weight: float
#     end_weight: float
#     Monday: Optional[WorkoutDaySchema] = None
#     Tuesday: Optional[WorkoutDaySchema] = None
#     Wednesday: Optional[WorkoutDaySchema] = None
#     Thursday: Optional[WorkoutDaySchema] = None
#     Friday: Optional[WorkoutDaySchema] = None
#     Saturday: Optional[WorkoutDaySchema] = None
#     Sunday: Optional[WorkoutDaySchema] = None

# # Schema for updating the workout plan
# class WorkoutPlanUpdateSchema(BaseModel):
#     start_date: Optional[str] = None  # Use str instead of datetime
#     end_date: Optional[str] = None    # Use str instead of datetime
#     current_weight: Optional[float] = None
#     end_weight: Optional[float] = None
#     Monday: Optional[WorkoutDaySchema] = None
#     Tuesday: Optional[WorkoutDaySchema] = None
#     Wednesday: Optional[WorkoutDaySchema] = None
#     Thursday: Optional[WorkoutDaySchema] = None
#     Friday: Optional[WorkoutDaySchema] = None
#     Saturday: Optional[WorkoutDaySchema] = None
#     Sunday: Optional[WorkoutDaySchema] = None

# Enum for days of the week to ensure validation
class DayOfWeek(str, Enum):
    monday = "Monday"
    tuesday = "Tuesday"
    wednesday = "Wednesday"
    thursday = "Thursday"
    friday = "Friday"
    saturday = "Saturday"
    sunday = "Sunday"

# Workout Plan Schema with only exercise IDs
class WorkoutPlan(BaseModel):
    workout_plan_name: str
    # Dictionary of days, each containing a list of exercise IDs
    schedule: dict[DayOfWeek, List[str]] = {
        DayOfWeek.monday: [],
        DayOfWeek.tuesday: [],
        DayOfWeek.wednesday: [],
        DayOfWeek.thursday: [],
        DayOfWeek.friday: [],
        DayOfWeek.saturday: [],
        DayOfWeek.sunday: [],
    }

    class Config:
        use_enum_values = True  # Automatically convert Enums to their string values when serialized to JSON


class WorkoutPlanUpdateSchema(BaseModel):
    workout_plan_name: Optional[str] = None  # Make workout_plan_name optional
    schedule: Optional[Dict[str, List[str]]] = None  # Make schedule optional

    class Config:
        use_enum_values = True  # Automatically convert Enums to their string values when serialized to JSON


# Pydantic model to represent Exercise with only ID and Name
class ExerciseOut(BaseModel):
    exercise_id: str  # ID converted to string
    name: str

    # Convert MongoDB's ObjectId to string
    @classmethod
    def from_mongo(cls, exercise: dict):
        return cls(
            exercise_id=str(exercise["_id"]),  # Convert ObjectId to string
            name=exercise["name"]
        )
    

# Assigning workout plan to users
class WorkoutPlanDetails(BaseModel):
    start_date: date  # Start date of the workout plan
    end_date: date  # End date of the workout plan
    current_weight: float  # The user's current weight
    end_weight: float  # Target weight to achieve
    workout_plan_id: str  # The ID of the workout plan
    class Config:
        # Ensure dates are correctly formatted (optional depending on your use case)
        json_encoders = {
            date: lambda v: v.isoformat()
        }


class UpdateWorkoutPlanDetails(BaseModel):
    start_date: Optional[date] = None  # Start date of the workout plan
    end_date: Optional[date] = None  # End date of the workout plan
    current_weight: Optional[float] = None  # The user's current weight
    end_weight: Optional[float] = None  # Target weight to achieve
    workout_plan_id: Optional[str] = None  # The ID of the workout plan

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }



# Schema for assigning and modifying workouts to user 
class ModifyWorkoutsUserResponse(BaseModel):
    user_id : str
    message: str = None
    workout_plan_details: WorkoutPlanDetails 

