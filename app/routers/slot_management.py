# app/routers/slot_management.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, File, UploadFile, Body
from bson.objectid import ObjectId
from typing import List, Optional
from datetime import datetime
from loguru import logger

from app.database import User, DietPlans, WorkoutandDietTracking, FoodItems, UserSlots
from app.schemas.slot__management import SlotManagementRequest
from app.utilities.error_handler import handle_errors
from .. import oauth2
from app.utilities.utils import get_current_ist_time
from pymongo.errors import PyMongoError

router = APIRouter()

@router.post('/slot-management', status_code=status.HTTP_201_CREATED)
async def add_user_to_slots(
    payload: SlotManagementRequest = Body(...),
    auth_user_id: str = Depends(oauth2.require_user)
):
    """
    Add a user to specific slots across multiple days.
    """
    user_id = payload.user_id

    try:
        # Fetch user details from Users collection
        user = await User.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        user_name = user.get("name")
        if not user_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User name not found.")

        # Iterate over each day in the day_range and add the user to the corresponding slots
        for day in payload.day_range:
            query = {
                "days.day_of_week": day,
                "days.slots": {
                    "$elemMatch": {
                        "start_time": payload.slot_time.start_time,
                        "end_time": payload.slot_time.end_time
                    }
                }
            }
            update = {
                "$addToSet": {
                    "days.$.slots.$[slot].allocated_users": {
                        "user_id": user_id,
                        "name": user_name
                    }
                }
            }
            array_filters = [{"slot.start_time": payload.slot_time.start_time, "slot.end_time": payload.slot_time.end_time}]
            
            result = await UserSlots.update_one(query, update, array_filters=array_filters)
            
            if result.modified_count == 0:
                logger.warning(f"No slots were updated for day {day}. Possible slot not found.")

        # Add slot details to the User instance
        slot_details = {
            "day_range": payload.day_range,
            "slot_time": {
                "start_time": payload.slot_time.start_time,
                "end_time": payload.slot_time.end_time
            }
        }
        await User.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"slot_details": slot_details}}
        )

        return {"message": "User successfully added to specified slots."}
    except Exception as e:
        logger.error(f"Error adding user to slots: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add user to slots.")
    

@router.get('/user-slot-details/{user_id}', status_code=status.HTTP_200_OK)
async def get_user_slot_details(
    user_id: str,
    auth_user_id: str = Depends(oauth2.require_user)
):
    """
    Get slot details for a specific user.
    """
    try:
        # Fetch user details from Users collection
        user = await User.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        # Get the slot details from the user document
        slot_details = user.get("slot_details")
        if not slot_details:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot details not found.")

        return {"user_id": user_id, "slot_details": slot_details}
    except Exception as e:
        logger.error(f"Error fetching slot details for user: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get slot details.")
    

@router.put('/user-slot-details/{user_id}', status_code=status.HTTP_200_OK)
async def update_user_slot_details(
    user_id: str,
    payload: SlotManagementRequest = Body(...),
    auth_user_id: str = Depends(oauth2.require_user)
):
    """
    Update slot details for a specific user.
    """
    try:
        # Fetch user details from Users collection
        user = await User.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        user_name = user.get("name")
        if not user_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User name not found.")

        # Remove the user from any existing slots in UserSlots
        remove_query = {
            "days.slots.allocated_users.user_id": user_id
        }
        remove_update = {
            "$pull": {
                "days.$[].slots.$[].allocated_users": {"user_id": user_id}
            }
        }
        await UserSlots.update_many(remove_query, remove_update)

        # Update the slot details in the user document
        slot_details = {
            "day_range": payload.day_range,
            "slot_time": {
                "start_time": payload.slot_time.start_time,
                "end_time": payload.slot_time.end_time
            }
        }
        result = await User.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"slot_details": slot_details}}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No changes were made.")

        # Add the user to the new slots in UserSlots
        for day in payload.day_range:
            query = {
                "days.day_of_week": day,
                "days.slots": {
                    "$elemMatch": {
                        "start_time": payload.slot_time.start_time,
                        "end_time": payload.slot_time.end_time
                    }
                }
            }
            update = {
                "$addToSet": {
                    "days.$.slots.$[slot].allocated_users": {
                        "user_id": user_id,
                        "name": user_name
                    }
                }
            }
            array_filters = [{"slot.start_time": payload.slot_time.start_time, "slot.end_time": payload.slot_time.end_time}]

            result = await UserSlots.update_one(query, update, array_filters=array_filters)

            if result.modified_count == 0:
                logger.warning(f"No slots were updated for day {day}. Possible slot not found or user not allocated.")

        return {"message": "User slot details successfully updated."}
    except Exception as e:
        logger.error(f"Error updating slot details for user: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update slot details.")


@router.delete('/user-slot-details/{user_id}', status_code=status.HTTP_200_OK)
async def delete_user_slot_details(
    user_id: str,
    auth_user_id: str = Depends(oauth2.require_user)
):
    """
    Delete slot details for a specific user.
    """
    try:
        # Fetch user details from Users collection
        user = await User.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        # Remove the user's slot details from UserSlots collection
        remove_query = {
            "days.slots.allocated_users.user_id": user_id
        }
        remove_update = {
            "$pull": {
                "days.$[].slots.$[].allocated_users": {"user_id": user_id}
            }
        }
        await UserSlots.update_many(remove_query, remove_update)

        # Remove slot details from User document
        result = await User.update_one(
            {"_id": ObjectId(user_id)},
            {"$unset": {"slot_details": ""}}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No slot details were found to delete.")

        return {"message": "User slot details successfully deleted."}
    except Exception as e:
        logger.error(f"Error deleting slot details for user: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete slot details.")
