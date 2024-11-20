# app/schemas/exercise.py

from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from bson import ObjectId

class ExerciseSchema(BaseModel):
    exercise_id: str  # This should reference an existing exercise ID in the database
    completed: bool = False
    sets: Optional[int] = None
    reps: Optional[int] = None

class DayProgressSchema(BaseModel):
    day: str  # E.g., "Monday", "Tuesday", etc.
    exercises: List[ExerciseSchema]  # List of exercises performed on this day

class WorkoutPlanSchema(BaseModel):
    start_date: date
    end_date: date
    progress: Optional[List[DayProgressSchema]] = []  # List of progress entries by day

class WorkoutPlanUpdateSchema(BaseModel):
    progress: Optional[List[DayProgressSchema]] = None  # Allows partial updates

class ExerciseCreateSchema(BaseModel):
    name: str
    sets: int
    reps: int
    type: str  # E.g., Strength, Cardio, etc.
    category: str  # E.g., Beginner, Intermediate, Advanced

class ExerciseUpdateSchema(BaseModel):
    name: Optional[str] = None
    sets: Optional[int] = None
    reps: Optional[int] = None
    type: Optional[str] = None
    category: Optional[str] = None

class ExerciseResponseSchema(ExerciseCreateSchema):
    id: str  # This will be the MongoDB ObjectId

    class Config:
        orm_mode = True
        json_encoders = {ObjectId: str}
