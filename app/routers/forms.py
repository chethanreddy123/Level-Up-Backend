from fastapi import APIRouter, Depends, HTTPException, status
from bson.objectid import ObjectId
from datetime import datetime
from app.database import Forms
from app.schemas import forms as form_schema
from app.utilities.error_handler import handle_errors
from app.serializers.formSerializers import formResponseEntity
from .. import oauth2

router = APIRouter()


@router.get('/', response_model=list[form_schema.FormResponseSchema])
def get_all_forms(user: dict = Depends(oauth2.require_admin)):
    """Retrieve all forms. Only accessible by admin users."""
    with handle_errors():
        forms = list(Forms.find())
        return [formResponseEntity(form) for form in forms]


@router.get('/{form_id}', response_model=form_schema.FormResponseSchema)
def get_form(form_id: str, user: dict = Depends(oauth2.require_admin)):
    """Retrieve a single form by its ID. Only accessible by admin users."""
    with handle_errors():
        form = Forms.find_one({"_id": ObjectId(form_id)})
        if not form:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form not found")
        return formResponseEntity(form)


@router.post('/', response_model=form_schema.FormResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_form(payload: form_schema.FormCreateSchema, user: dict = Depends(oauth2.require_admin)):
    """Create a new form. Only accessible by admin users."""
    with handle_errors():
        # Add timestamps to the form data
        payload.created_at = datetime.utcnow()
        payload.updated_at = datetime.utcnow()
        
        # Insert new form into the database
        form_data = payload.dict()
        result = Forms.insert_one(form_data)
        new_form = Forms.find_one({'_id': result.inserted_id})

        return formResponseEntity(new_form)


@router.put('/{form_id}', response_model=form_schema.FormResponseSchema)
async def edit_form(form_id: str, payload: form_schema.FormUpdateSchema, user: dict = Depends(oauth2.require_admin)):
    """Edit an existing form by its ID. Only accessible by admin users."""
    with handle_errors():
        # Update the updated_at timestamp
        payload.updated_at = datetime.utcnow()
        
        # Remove None fields from update data
        update_data = {k: v for k, v in payload.dict().items() if v is not None}
        
        # Find and update the form
        updated_form = Forms.find_one_and_update(
            {"_id": ObjectId(form_id)},
            {"$set": update_data},
            return_document=True
        )
        
        if not updated_form:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form not found")

        return formResponseEntity(updated_form)


@router.delete('/{form_id}', response_model=dict)
async def delete_form(form_id: str, user: dict = Depends(oauth2.require_admin)):
    """Delete a form by its ID. Only accessible by admin users."""
    with handle_errors():
        result = Forms.delete_one({"_id": ObjectId(form_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form not found")
        return {"message": "Form deleted successfully"}
