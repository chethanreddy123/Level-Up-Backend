# app/routers/food_item.py

from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from bson.objectid import ObjectId
from typing import List
from loguru import logger
from pymongo import ReturnDocument

from app.database import FoodItems
from app.schemas.food_item import FoodItemSchema
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
    If a food item with the same name (case-insensitive) already exists, raise a warning.
    """
    with handle_errors():
        logger.info(f"Creating a new food item: {payload.food_name} by user ID: {user_id}")

        # Check if the food item already exists (case-insensitive)
        existing_food_item = await FoodItems.find_one(
            {"food_name": {"$regex": f"^{payload.food_name}$", "$options": "i"}}
        )
        
        if existing_food_item:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"The food item '{payload.food_name.title()}' already exists."
            )

        # Prepare the food item data from the payload
        food_item_data = payload.dict()

        # Insert the new food item into the FoodItems collection
        result = await FoodItems.insert_one(food_item_data)
        
        # Fetch the newly inserted food item, including the inserted _id
        new_food_item = await FoodItems.find_one({'_id': result.inserted_id})
        
        # Convert _id from ObjectId to string
        if new_food_item:
            new_food_item['_id'] = str(new_food_item['_id'])

        return {
            "id": new_food_item['_id'],  # Return the food item with its inserted data
            "message": "Food item added successfully!",
        }


# Retrieve a single food item by its ID
@router.get('/food-item/{food_item_id}', response_model=FoodItemSchema)
async def get_food_item_by_id(
    food_item_id: str,
):
    """
    Retrieve a single food item by its ID.
    """
    with handle_errors():
        # Convert food_item_id to ObjectId for MongoDB operations
        try:
            food_item_obj_id = ObjectId(food_item_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid food item ID format.")
        
        # Fetch the food item from the database
        food_item = await FoodItems.find_one({"_id": food_item_obj_id})
        
        if not food_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Food item not found."
            )

        # Convert the _id from ObjectId to string for the response
        food_item['_id'] = str(food_item['_id'])

        return food_item

# Retrieve food items with pagination
@router.get('/food-items', response_model=dict)
async def get_food_items(
    page: int = Query(1, ge=1, description="Page number, starting from 1"),  # Default to page 1, must be >= 1
    items_per_page: int = Query(10, le=100, description="Number of items per page, max 100")  # Max of 100 items per page
):
    """
    Retrieve food items with pagination.
    Returns the total number of items, current page, total pages, and the list of food items.
    """
    with handle_errors():
        # Calculate the number of items to skip for pagination
        skip = (page - 1) * items_per_page

        # Fetch the total number of food items
        total_items = await FoodItems.count_documents({})

        # Calculate total pages based on the total items and items per page
        total_pages = ceil(total_items / items_per_page)

        # Fetch the paginated food items
        food_items_cursor = FoodItems.find().skip(skip).limit(items_per_page)
        food_items = await food_items_cursor.to_list(length=items_per_page)

        # Convert _id to string for each food item in the response
        for item in food_items:
            item['_id'] = str(item['_id'])

        return {
            "total_items": total_items,
            "current_page": page,
            "total_pages": total_pages,
            "food_items": food_items
        }

# Update an existing food item
@router.put('/food-item/{food_item_id}', status_code=status.HTTP_200_OK)
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
        update_result = await FoodItems.update_one(
            {"_id": food_item_obj_id},
            {"$set": update_data}
        )

        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Food item not found or no updates made."
            )

        # Return a success message with the food item's id
        return {
            "id": food_item_id,  # Returning the food_item_id in the response
            "message": "Food item updated successfully"
        }


# Delete a food item
@router.delete('/food-item/{food_item_id}', status_code=status.HTTP_200_OK)
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

        # Fetch the food item before deletion to return its ID
        food_item = await FoodItems.find_one({"_id": food_item_obj_id})
        if not food_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Food item not found."
            )

        # Delete the food item from the collection
        delete_result = await FoodItems.delete_one({"_id": food_item_obj_id})
        if delete_result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete food item."
            )

        # Return the ID of the deleted food item
        return {
            "id": food_item_id,  # Return the ID of the deleted item
            "message": "Food item deleted successfully!"
        }
