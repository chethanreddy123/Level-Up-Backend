from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timedelta
from app.database import UserAttendance, User  # MongoDB collection for attendance
from app import oauth2
from bson import ObjectId
from app.utilities.utils import get_current_ist_time
from loguru import logger
from app.utilities.error_handler import handle_errors
from pymongo import ASCENDING

router = APIRouter()

# Create a compound index on user_id and date fields in the UserAttendance collection (for fast quering of the db)
UserAttendance.create_index([("user_id", ASCENDING), ("date", ASCENDING)], unique=True)

@router.post('/mark-attendance', status_code=status.HTTP_201_CREATED)
def mark_attendance(
    user_id: str = Depends(oauth2.require_user)  # Getting authenticated user
):
    """
    Mark the user's attendance for the current day.
    The attendance is automatically marked as 'present' (status = True).
    """
    with handle_errors():  # Custom error handling context
        # Log the action of marking attendance
        logger.info(f"Marking attendance for user ID: {user_id}.")

        try:
            # Get the current date in 'yyyy-mm-dd' format (ISODate format)
            current_date = datetime.utcnow().date()  # Get current UTC date
            current_date_str = current_date.isoformat()  # Convert to string (yyyy-mm-dd)

            # Check if the attendance for today already exists for this user
            existing_attendance = UserAttendance.find_one({"user_id": user_id, "date": current_date_str})
            if existing_attendance:
                # Log the condition where attendance already exists
                logger.info(f"Attendance already exists for user ID: {user_id} on {current_date_str}.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Attendance already recorded for user ID: {user_id} on {current_date_str}."
                )

            # Create the attendance record
            attendance_record = {
                "user_id": user_id,  # The authenticated user's ID
                "date": current_date_str,  # The current date as a string
                "status": True  # Status set to True (present)
            }

            # Insert the attendance record into the UserAttendance collection
            result = UserAttendance.insert_one(attendance_record)

            if result.acknowledged:
                # Log successful attendance marking
                logger.info(f"Attendance marked for user ID: {user_id} on {current_date_str}.")
                return {"message": "Attendance recorded successfully!"}
            else:
                # Log failure to insert attendance
                logger.error(f"Failed to record attendance for user ID: {user_id}.")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to record attendance."
                )

        except HTTPException as http_exc:
            # Log and raise the HTTPException with its original message
            logger.warning(f"HTTPException: {http_exc.detail}")
            raise http_exc

        except Exception as e:
            # Log the full exception with stack trace
            logger.error(f"Exception occurred: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing your request."
            )


@router.post('/mark-absent', status_code=status.HTTP_201_CREATED)
def mark_absent(
    auth_user_id: str = Depends(oauth2.require_user)  # Getting authenticated user
):
    """
    Mark all users as absent if they haven't been marked present for the current day.
    Will be handled by cron-job at 11:30 PM everyday.
    """
    with handle_errors():  # Custom error handling context
        try:
            # Get the current date in 'yyyy-mm-dd' format
            current_date = datetime.utcnow().date()
            current_date_str = current_date.isoformat()  # Convert to string format (yyyy-mm-dd)

            # Fetch all user IDs from the User collection
            all_users = list(User.find({}, {"_id": 1}))  # Retrieve only user IDs
            all_user_ids = {str(user["_id"]) for user in all_users}

            # Fetch all user IDs that have already marked attendance for the current date
            present_users = list(UserAttendance.find({"date": current_date_str}, {"user_id": 1}))
            present_user_ids = {attendance["user_id"] for attendance in present_users}

            # Determine the user IDs that are not marked present (absent users)
            absent_user_ids = all_user_ids - present_user_ids

            if not absent_user_ids:
                return {"message": "All users have been marked for today. No absent users to mark."}

            # Insert attendance records for absent users
            absent_attendance_records = [
                {
                    "user_id": user_id,
                    "date": current_date_str,
                    "status": False  # Mark status as False for absent
                }
                for user_id in absent_user_ids
            ]

            # Insert absent records into UserAttendance collection
            if absent_attendance_records:
                result = UserAttendance.insert_many(absent_attendance_records)

                if result.acknowledged:
                    logger.info(f"Marked absent for users: {absent_user_ids}")
                    return {"message": "Absent users have been marked successfully."}
                else:
                    logger.error("Failed to insert absent attendance records.")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to mark absent users."
                    )

        except HTTPException as http_exc:
            # Log and raise the HTTPException with its original message
            logger.warning(f"HTTPException: {http_exc.detail}")
            raise http_exc

        except Exception as e:
            # Log the full exception with stack trace
            logger.error(f"Exception occurred: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing your request."
            )
        

@router.get('/get-attendance/{user_id}', status_code=status.HTTP_200_OK)
def get_attendance(
    user_id: str,
    auth_user_id: str = Depends(oauth2.require_user)  # Getting authenticated user
):
    """
    Get attendance details for the user from the start of the current month to the current day.
    Returns the number of present days, total days, and attendance percentage.
    """
    try:
        # Check if the user exists in the User collection
        user_exists = User.find_one({"_id": ObjectId(user_id)})
        if not user_exists:
            logger.warning(f"User with ID: {user_id} not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID: {user_id} not found."
            )

        # Calculate the start of the current month and the current date
        current_date = datetime.utcnow().date()
        start_of_month = current_date.replace(day=1)

        # Query attendance records for the given user from the start of the month to today
        attendance_records = list(UserAttendance.find({
            "user_id": user_id,
            "date": {"$gte": start_of_month.isoformat(), "$lte": current_date.isoformat()}
        }))

        # Calculate total days and present days
        total_days = len(attendance_records)  # Count all records, both present and absent
        present_days = sum(1 for record in attendance_records if record.get("status") == True)

        # Calculate attendance percentage
        attendance_percentage = (present_days / total_days) * 100 if total_days > 0 else 0

        return {
            "user_id": user_id,
            "total_days": total_days,
            "present_days": present_days,
            "attendance_percentage": round(attendance_percentage, 2)
        }
    
    except HTTPException as http_exc:
        # Log and raise the HTTPException with its original message
        logger.warning(f"HTTPException: {http_exc.detail}")
        raise http_exc

    except Exception as e:
        # Log the full exception with stack trace
        logger.error(f"Exception occurred: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request."
        )