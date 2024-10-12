def formResponseEntity(form) -> dict:
    return {
        "id": str(form["_id"]),
        "form_name": form["form_name"],
        "fields": form["fields"],
        "created_at": form["created_at"],
        "updated_at": form["updated_at"]
    }
