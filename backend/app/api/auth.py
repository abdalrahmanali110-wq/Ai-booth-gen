from fastapi import APIRouter, HTTPException

from app.schemas.user import UserRegister, UserLogin
from app.core.database import supabase

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register")
def register(user: UserRegister):

    try:

        auth_response = supabase.auth.sign_up(
            {
                "email": user.email,
                "password": user.password
            }
        )

        if auth_response.user:

            supabase.table("users").insert(
                {
                    "id": str(auth_response.user.id),
                    "full_name": user.full_name
                }
            ).execute()

        return {
            "message": "User registered successfully",
            "user_id": auth_response.user.id
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@router.post("/login")
def login(user: UserLogin):

    try:

        auth_response = supabase.auth.sign_in_with_password(
            {
                "email": user.email,
                "password": user.password
            }
        )

        return {
            "access_token": auth_response.session.access_token,
            "refresh_token": auth_response.session.refresh_token,
            "user": auth_response.user
        }

    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )


@router.get("/profiles")
def get_users():

    response = supabase.table("users").select("*").execute()

    return response.data

