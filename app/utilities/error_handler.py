from contextlib import contextmanager
from typing import Dict, Any, Callable
from sqlalchemy.exc import SQLAlchemyError
from pymongo import errors as pymongo_errors
from app.schemas.error import ErrorResponse
from fastapi import HTTPException
from loguru import logger


@contextmanager
def handle_errors():
    try:
        yield
    except SQLAlchemyError as e:
        logger.error(f"Database error occurred: {e}")
        response = ErrorResponse(
            status_code=400, status="DatabaseError", message=str(e)
        )
    except pymongo_errors.PyMongoError as e:
        logger.error(f"MongoDB error occurred: {e}")
        response = ErrorResponse(
            status_code=500, status="MongoDBError", message=str(e)
        )
    except Exception as e:
        logger.error(f"Internal server error: {e}")
        response = ErrorResponse(
            status_code=500, status="InternalServerError", message=str(e)
        )
    else:
        response = None

    if response is not None:
        # Log the response details before raising the exception
        logger.error(
            f"Raising HTTP exception with response: {response.status_code} - {response.message}"
        )
        raise HTTPException(status_code=response.status_code, detail=vars(response))
