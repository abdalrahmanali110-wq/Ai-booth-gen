from fastapi import APIRouter
from app.core.database import supabase

router = APIRouter()


@router.get("/users/test")
def test_users_table():
    response = supabase.table("users").select("*").execute()

    return {
        "success": True,
        "data": response.data
    }