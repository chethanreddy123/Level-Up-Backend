import base64
from typing import List
from fastapi import Depends, HTTPException, status
from fastapi_jwt_auth import AuthJWT
from pydantic import BaseModel
from bson.objectid import ObjectId
from loguru import logger
from app.serializers.userSerializers import userEntity
from app.database import User
from config import settings


# Function to decode base64 keys with proper padding handling
def decode_base64_key(key: str) -> str:
    """Decode the base64-encoded key and return the PEM format as a string."""
    # Ensure the key length is a multiple of 4 by adding necessary padding
    padding = len(key) % 4
    if padding != 0:
        key += '=' * (4 - padding)  # Add the correct number of '=' to pad the key
    decoded_key = base64.b64decode(key).decode("utf-8")
    return decoded_key


class Settings(BaseModel):
    authjwt_algorithm: str
    authjwt_decode_algorithms: List[str]
    authjwt_token_location: set
    authjwt_access_cookie_key: str
    authjwt_refresh_cookie_key: str
    authjwt_cookie_csrf_protect: bool
    authjwt_public_key: str
    authjwt_private_key: str

    @classmethod
    def from_settings(cls, settings):
        """Create the settings instance from the loaded settings"""
        return cls(
            authjwt_algorithm=settings.JWT_ALGORITHM,
            authjwt_decode_algorithms=[settings.JWT_ALGORITHM],
            authjwt_token_location={'cookies', 'headers'},
            authjwt_access_cookie_key='access_token',
            authjwt_refresh_cookie_key='refresh_token',
            authjwt_cookie_csrf_protect=False,
            authjwt_public_key=decode_base64_key(settings.JWT_PUBLIC_KEY),  # Decode the public key
            authjwt_private_key=decode_base64_key(settings.JWT_PRIVATE_KEY),  # Decode the private key
        )


# Get the settings from the environment
settings_instance = Settings.from_settings(settings)

@AuthJWT.load_config
def get_config():
    # Return the settings instance for AuthJWT to use
    return settings_instance


class NotVerified(Exception):
    pass


class UserNotFound(Exception):
    pass


async def require_user(Authorize: AuthJWT = Depends()):
    """
    Dependency to check if the user is authenticated.
    Returns the user ID if the user is authenticated and verified.
    """
    try:
        # Ensure the user is authenticated
        Authorize.jwt_required()
        
        # Retrieve the user ID from the JWT token's subject (sub)
        user_id = Authorize.get_jwt_subject()
        
        # Fetch the user document using the user_id synchronously
        db_user =  User.find_one({'_id': ObjectId(str(user_id))})
        user = userEntity(db_user) if db_user else None

        # Check if the user exists in the database
        if not user:
            raise UserNotFound('User no longer exists')

        # Check if the user's email is verified
        if not user["verified"]:
            raise NotVerified('You are not verified')

    except Exception as e:
        error = e.__class__.__name__
        logger.error(f"Authorization error: {error}")
        if error == 'MissingTokenError':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail='You are not logged in')
        if error == 'UserNotFound':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail='User no longer exists')
        if error == 'NotVerified':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail='Please verify your account')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Token is invalid or has expired')

    # Return only the user ID instead of the entire user object
    return user_id


def require_admin(user: dict = Depends(require_user)):
    """
    Dependency to check if the user is an admin.
    Requires the user to be authenticated and have the role of 'ADMIN'.
    """
    if user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have the required permissions. Admin access is required."
        )
    return user
