from fastapi import APIRouter, status, Body, HTTPException
from bson import ObjectId
from pymongo import MongoClient
from pydantic import BaseModel, Field
from typing import List, Dict


class SlotTime(BaseModel):
    start_time: str
    end_time: str


class SlotManagementRequest(BaseModel):
    day_range: List[str] = Field(..., example=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
    slot_time: SlotTime
    user_id: str