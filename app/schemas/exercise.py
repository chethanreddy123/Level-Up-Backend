# app/schemas/exercise.py

from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from bson import ObjectId
from enum import Enum


# Constraints for exercise types and level

# Enum for Exercise Type
class ExerciseType(Enum):
    bodyweight = 'bodyweight'
    core = 'cardio'
    strength = 'strength'

# Enum for Category Level
class ExerciseLevel(Enum):
    beginner = 'beginner'
    intermediate = 'intermediate'
    advanced = 'advanced'


class ExerciseSchema(BaseModel):
    exercise_id: str  # This should reference an existing exercise ID in the database
    completed: bool = False
    sets: Optional[int] = None
    reps: Optional[int] = None
    calories: Optional[int] = None

class DayProgressSchema(BaseModel):
    day: str  # E.g., "Monday", "Tuesday", etc.
    exercises: List[ExerciseSchema]  # List of exercises performed on this day

class WorkoutPlanSchema(BaseModel):
    start_date: date
    end_date: date
    progress: Optional[List[DayProgressSchema]] = []  # List of progress entries by day

class WorkoutPlanUpdateSchema(BaseModel):
    progress: Optional[List[DayProgressSchema]] = None  # Allows partial updates

# Schema for exercise creation
class ExerciseCreateSchema(BaseModel):
    name: str
    sets: int
    reps: int
    calories: int
    type: ExerciseType  # Enum restricts this to only 'bodyweight', 'cardio', 'strength'
    level: ExerciseLevel  # Enum restricts this to 'beginner', 'intermediate', 'advanced'

    class Config:
        # Automatically convert Enums to their string values when serialized to JSON
        use_enum_values = True

# Schema to get exercises with pagination
class GetExercises(BaseModel):
    type: Optional[ExerciseType] = None
    level: Optional[ExerciseLevel] = None

    class Config:
        # Automatically convert Enums to their string values when serialized to JSON
        use_enum_values = True



class ExerciseUpdateSchema(BaseModel):
    name: Optional[str] = None
    sets: Optional[int] = None
    reps: Optional[int] = None
    calories: Optional[int] = None
    type: Optional[str] = None
    level: Optional[str] = None

class ExerciseResponseSchema(ExerciseCreateSchema):
    id: str  # This will be the MongoDB ObjectId
    message: str
    class Config:
        orm_mode = True
        json_encoders = {ObjectId: str}


# For uploading the workout performance by the user from the mobile app 

class WorkoutEntry(BaseModel):
    workout_name: str  
    sets_assigned: int  
    sets_done: int 
    reps_assigned: int  
    reps_done: int  
    weight: Optional[float] = 1  

    @property
    def load_assigned(self) -> float:
        """Calculate the load assigned to the user for the exercise"""
        return self.sets_assigned * self.reps_assigned * self.weight

    @property
    def load_done(self) -> float:
        """Calculate the load completed by the user"""
        return self.sets_done * self.reps_done * self.weight

    @property
    def performance(self) -> float:
        """Calculate the performance percentage (load_done / load_assigned)"""
        return (self.load_done / self.load_assigned) * 100

class UploadWorkoutRequest(BaseModel):
    workout: WorkoutEntry  # A single workout entry (one exercise)