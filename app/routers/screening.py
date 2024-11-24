from fastapi import APIRouter, Depends, HTTPException, status
from app.database import User
from app.schemas.screening import ScreeningFormSchema
from app.utilities.error_handler import handle_errors
from bson import ObjectId
from datetime import datetime
from loguru import logger
from .. import oauth2

router = APIRouter()

@router.post('/screening', status_code=status.HTTP_201_CREATED)
async def submit_screening_form(
    payload: ScreeningFormSchema, 
    user_id: str = Depends(oauth2.require_user)  # `user_id` is now a string returned by `require_user`
):
    """
    Route for users to submit their screening form.
    The form responses will be saved and linked to the authenticated user within the user document.
    """
    with handle_errors():
        
        # Convert `user_id` to ObjectId for MongoDB operations
        try:
            # Taking the user_id from the payload and converting it to ObjectId as it's customer id
            user_id = ObjectId(payload.dict().get("user_id"))
        except Exception as e:
            logger.error(f"Error converting user ID to ObjectId: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format."
            )

        # Check if the user exists in the database
        existing_user = User.find_one({"_id": user_id})
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if the user already has a screening field
        if "screening" in existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Screening form has already been submitted."
            )
        
        # Prepare screening data
        screening_data = payload.dict()
        screening_data["submitted_at"] = datetime.utcnow()

        # Update user document with screening data in MongoDB
        update_result = User.update_one(
            {"_id": user_id},  # Use `_id` for MongoDB operations
            {"$set": {"screening": screening_data}}
        )

        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user with screening form data."
            )

        return {"message": "Screening form submitted successfully!"}

@router.get('/screening/details/{user_id}', response_model=ScreeningFormSchema)
async def get_screening_details(
    user_id: str , 
    auth_user_id : str = Depends(oauth2.require_user)):
    """
    Retrieve the screening form details of the authenticated user.
    """
    with handle_errors():
        # Log the user ID for debugging
        logger.info(f"Retrieving screening details for user ID: {user_id}")
        
        # Convert `user_id` to ObjectId for MongoDB operations
        try:
            user_id = ObjectId(user_id)
        except Exception as e:
            logger.error(f"Error converting user ID to ObjectId: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format."
            )

        # Fetch the user document from the database
        existing_user = User.find_one({"_id": user_id})
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if the user has a screening field
        if "screening" not in existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Screening form not found for the user."
            )

        # Return the screening data
        return existing_user["screening"]

@router.put('/screening/edit', status_code=status.HTTP_200_OK, response_model=ScreeningFormSchema)
async def edit_screening_form(
    payload: ScreeningFormSchema,
    user_id: str = Depends(oauth2.require_user)  # `user_id` is a string returned by `require_user`
):
    """
    Route for users to edit their existing screening form.
    The changes will be updated within the user document.
    """
    with handle_errors():
      
        try:
            user_id = ObjectId(payload.dict().get("user_id")) # taking the user_id from the payload and converting it to ObjectId as it's customer id
        except Exception as e:
            logger.error(f"Error converting user ID to ObjectId: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format."
            )

        # Check if the user exists in the database
        existing_user = User.find_one({"_id": user_id})
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if the user has a screening field to update
        if "screening" not in existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Screening form not found for the user."
            )
        
        # Prepare updated screening data by merging with the existing data
        screening_data = existing_user["screening"]
        updated_screening_data = {**screening_data, **payload.dict(exclude_unset=True)}
        updated_screening_data["updated_at"] = datetime.utcnow()

        # Update the user document with the modified screening data in MongoDB
        update_result = User.update_one(
            {"_id": user_id},  # Use `_id` for MongoDB operations
            {"$set": {"screening": updated_screening_data}}
        )

        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user with screening form data."
            )

        return updated_screening_data
