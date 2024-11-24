def userEntity(user) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "photo": user["photo"],
        "verified": user["verified"],
        "password": user["password"],
        "created_at": user["created_at"],
        "updated_at": user["updated_at"]
    }


def userResponseEntity(user):
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "photo": user.get("photo"),  # Use .get() to avoid KeyError if the field is missing
        "role": user.get("role"),
        "phone_no": user.get("phone_no"),
        "address": user.get("address"),
        "slot_preference": user.get("slot_preference"),
        "previous_gym": user.get("previous_gym"),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
        "registration_id": user.get("registration_id")
    }

def embeddedUserResponse(user) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "photo": user["photo"]
    }


def userListEntity(users) -> list:
    return [userEntity(user) for user in users]

def userRegistrationEntity(user) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "address": user["address"],
        "email": user["email"],
        "phone_no": user["phone_no"],
        "previous_gym": user["previous_gym"],
        "slot_preference": user["slot_preference"],
        "phone_no": user["phone_no"],
        "created_at": user["created_at"],
        "updated_at": user["updated_at"]
    }

def serialize_user(user: dict) -> dict:
    """
    Serializes the MongoDB user document, converting ObjectId to string and removing sensitive fields.
    """
    user["id"] = str(user["_id"])  # Convert ObjectId to string
    del user["_id"]  # Optionally remove the _id field if it's not needed in the response
    user.pop("password", None)  # Remove sensitive fields like password
    return user

def serialize_users(users: list) -> list:
    """
    Serializes a list of MongoDB user documents.
    """
    return [serialize_user(user) for user in users]