from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import app.database

from config import settings
from app.routers import auth, user, forms, screening, exercise, workout_plan, diet_plan, food_item

app = FastAPI()

origins = [
    settings.CLIENT_ORIGIN,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router, tags=['Auth'], prefix='/api/auth')
app.include_router(user.router, tags=['Users'], prefix='/api/users')
app.include_router(forms.router, tags=['Forms'], prefix='/api/forms')
app.include_router(screening.router, tags=['Screening'], prefix='/api')
app.include_router(exercise.router, tags=['Exercises'], prefix='/api')
app.include_router(workout_plan.router, tags=['Workout Plan'], prefix='/api')
app.include_router(diet_plan.router, tags=['Diet Plan'], prefix='/api')
app.include_router(food_item.router, tags=['Food Items'], prefix='/api')

@app.get("/api/healthchecker")
def root():
    return {"message": "Welcome to Level Up Fitness APIs!"}
