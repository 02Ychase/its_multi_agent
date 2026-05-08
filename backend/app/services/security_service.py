from fastapi import HTTPException


def require_current_user_id(current_user: dict) -> int:
    user_id = current_user.get("user_id")
    if not isinstance(user_id, int):
        try:
            return int(user_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=401, detail="无效用户身份")
    return user_id
