# app/routers/food_item.py

from fastapi import APIRouter, Depends, HTTPException, status
from bson.objectid import ObjectId
from typing import List
from loguru import logger

from app.database import FoodItems
from app.schemas.diet_plan import FoodItemSchema
from app.utilities.error_handler import handle_errors
from .. import oauth2

router = APIRouter()

# Create a new food item
@router.post('/food-item', status_code=status.HTTP_201_CREATED)
async def create_food_item(
    payload: FoodItemSchema,
    user_id: str = Depends(oauth2.require_user)
):
    """
    Create a new food item entry.
    """
    with handle_errors():
        logger.info(f"Creating a new food item: {payload.food_name} by user ID: {user_id}")

        # Prepare the food item data
        food_item_data = payload.dict()

        # Insert new food item into the FoodItems collection
        result = FoodItems.insert_one(food_item_data)
        new_food_item = FoodItems.find_one({'_id': result.inserted_id})

        return {"message": "Food item added successfully!", "food_item": new_food_item}


# Retrieve all food items
@router.get('/food-items', response_model=List[FoodItemSchema])
async def get_all_food_items():
    """
    Retrieve all food items from the collection.
    """
    with handle_errors():
        # Fetch all food items from the collection
        food_items = list(FoodItems.find())
        return food_items


# Update an existing food item
@router.put('/food-item/{food_item_id}', status_code=status.HTTP_200_OK, response_model=FoodItemSchema)
async def update_food_item(
    food_item_id: str,
    payload: FoodItemSchema,
    user_id: str = Depends(oauth2.require_user)
):
    """
    Update an existing food item by its ID.
    """
    with handle_errors():
        logger.info(f"Updating food item ID: {food_item_id} by user ID: {user_id}")

        # Convert food_item_id to ObjectId for MongoDB operations
        try:
            food_item_obj_id = ObjectId(food_item_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid food item ID format.")

        # Remove None fields from the update payload
        update_data = {k: v for k, v in payload.dict().items() if v is not None}

        # Update food item in the collection
        update_result = FoodItems.find_one_and_update(
            {"_id": food_item_obj_id},
            {"$set": update_data},
            return_document=True
        )

        if not update_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Food item not found."
            )

        return update_result


# Delete a food item
@router.delete('/food-item/{food_item_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_food_item(
    food_item_id: str,
    user_id: str = Depends(oauth2.require_user)
):
    """
    Delete a food item by its ID.
    """
    with handle_errors():
        logger.info(f"Deleting food item ID: {food_item_id} by user ID: {user_id}")

        # Convert food_item_id to ObjectId for MongoDB operations
        try:
            food_item_obj_id = ObjectId(food_item_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid food item ID format.")

        # Delete the food item from the collection
        delete_result = FoodItems.delete_one({"_id": food_item_obj_id})
        if delete_result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Food item not found."
            )

        return {"message": "Food item deleted successfully!"}
