import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.database import supabase
from app.schemas.booth import BoothRequestCreate
from app.services.prompt_service import build_booth_prompt
from app.services.image_service import generate_booth_image
from app.services.cloudinary_service import upload_image
from app.services.supplier_service import (
        recommend_suppliers
    )
from app.services.budget_service import (
        calculate_budget
    )

from app.services.proposal_service import (
        generate_proposal
    )
from app.services.pdf_service import generate_pdf


router = APIRouter(
    prefix="/booths",
    tags=["Booths"]
)

def _raise_api_error(error: Exception):
    message = str(error)

    if (
        "Pollinations" in message
        or "Hugging Face" in message
        or "Queue full" in message
        or "rate limit" in message.lower()
        or "credits exhausted" in message.lower()
    ):
        raise HTTPException(status_code=502, detail=message)

    if "row-level security" in message.lower():
        raise HTTPException(status_code=403, detail=message)

    raise HTTPException(status_code=400, detail=message)


@router.post("/generate")
def create_booth_request(booth: BoothRequestCreate):

    booth_id = None

    try:

        booth_response = supabase.table(
            "booth_requests"
        ).insert(
            {
                "user_id": "032f3894-2957-428b-8342-cfff63c9da47",
                "industry": booth.industry,
                "booth_theme": booth.booth_theme,
                "booth_size": booth.booth_size,
                "colors": booth.colors,
                "prompt": booth.prompt,
                "status": "pending"
            }
        ).execute()

        booth_record = booth_response.data[0]
        booth_id = booth_record["id"]

        ai_prompt = build_booth_prompt(
            industry=booth.industry,
            booth_theme=booth.booth_theme,
            booth_size=booth.booth_size,
            colors=booth.colors
        )

        image_result = generate_booth_image(
            ai_prompt
        )

        image_response = supabase.table(
            "generated_images"
        ).insert(
            {
                "booth_request_id": booth_record["id"],
                "image_url": image_result["image_url"],
                "image_provider": image_result["provider"],
                "prompt_used": ai_prompt
            }
        ).execute()

        suppliers = recommend_suppliers(
            booth.industry
        )

        saved_suppliers = []

        for supplier in suppliers:

            supplier_response = (
                supabase.table(
                    "supplier_recommendations"
                )
                .insert(
                    {
                        "booth_request_id":
                            booth_record["id"],

                        "company_name":
                            supplier["name"],

                        "website_url":
                            supplier["website"],

                        "location":
                            supplier["location"],

                        "estimated_cost":
                            supplier["estimated_cost"],

                        "description":
                            supplier["category"],

                        "source":
                            "rules-based"
                    }
                )
                .execute()
            )
            saved_suppliers.append(
                supplier_response.data[0]
            )

        return {
            "success": True,
            "booth_request": booth_record,
            "generated_image": image_response.data[0],
            "suppliers": saved_suppliers
        }
    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
        

@router.get("/{booth_id:uuid}")
def get_booth(booth_id: str):

    try:

        booth_response = (
            supabase.table("booth_requests")
            .select("*")
            .eq("id", booth_id)
            .execute()
        )

        if not booth_response.data:
            raise HTTPException(
                status_code=404,
                detail="Booth request not found"
            )

        booth = booth_response.data[0]

        images_response = (
            supabase.table("generated_images")
            .select("*")
            .eq("booth_request_id", booth_id)
            .execute()
        )

        suppliers_response = (
            supabase.table("supplier_recommendations")
            .select("*")
            .eq("booth_request_id", booth_id)
            .execute()
        )

        return {
            "success": True,
            "booth": booth,
            "images": images_response.data,
            "suppliers": suppliers_response.data
        }

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@router.get("/")
def get_all_booths():

    response = (
        supabase.table("booth_requests")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    return {
        "success": True,
        "data": response.data
    }

@router.get("/cloudinary-test")
def cloudinary_test():
    return {
        "status": "Cloudinary configured"
    }

@router.get("/cloudinary-upload-test")
def cloudinary_upload_test():

    try:
        test_image = "https://picsum.photos/1024/1024"
        uploaded_url = upload_image(test_image)

        return {
            "success": True,
            "cloudinary_url": uploaded_url,
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Cloudinary upload failed. Check CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET in backend/.env. Error: {e}",
        )

@router.get("/ai-test")
def ai_test():

    result = generate_booth_image(
        "Futuristic technology exhibition booth with blue LED screens and modern architecture"
    )

    return result

@router.get("/{booth_id}/suppliers")
def get_suppliers(booth_id: str):

    response = (
        supabase.table(
            "supplier_recommendations"
        )
        .select("*")
        .eq(
            "booth_request_id",
            booth_id
        )
        .execute()
    )

    return {
        "success": True,
        "data": response.data
    }

@router.get("/{booth_id}/budget")
def get_budget(booth_id: str):

    booth_response = (
        supabase.table("booth_requests")
        .select("*")
        .eq("id", booth_id)
        .execute()
    )

    if not booth_response.data:
        raise HTTPException(
            status_code=404,
            detail="Booth not found"
        )

    booth = booth_response.data[0]

    supplier_response = (
            supabase.table(
                "supplier_recommendations"
            )
            .select("*")
            .eq(
                "booth_request_id",
                booth_id
            )
            .execute()
        )

    
    suppliers = supplier_response.data

    budget = calculate_budget(
        suppliers,
        booth["booth_size"]
    )


    return {
        "success": True,
        "booth_id": booth_id,
        "budget": budget
    }

@router.post("/{booth_id}/proposal")
def create_proposal(booth_id: str):

    booth_response = (
        supabase.table("booth_requests")
        .select("*")
        .eq("id", booth_id)
        .execute()
    )

    if not booth_response.data:
        raise HTTPException(
            status_code=404,
            detail="Booth not found"
        )

    booth = booth_response.data[0]

    supplier_response = (
        supabase.table(
            "supplier_recommendations"
        )
        .select("*")
        .eq(
            "booth_request_id",
            booth_id
        )
        .execute()
    )

    suppliers = supplier_response.data

    budget = calculate_budget(
        suppliers,
        booth["booth_size"]
    )

    proposal_text = generate_proposal(
        booth,
        suppliers,
        budget
    )

    proposal_response = (
        supabase.table(
            "project_proposals"
        )
        .insert(
            {
                "booth_request_id":
                    booth_id,

                "proposal_title":
                    f"{booth['industry']} Exhibition Proposal",

                "proposal_summary":
                    proposal_text,

                "estimated_budget":
                    budget["grand_total"]
            }
        )
        .execute()
    )

    return {
        "success": True,
        "proposal": proposal_response.data[0]
    }

@router.get("/{booth_id}/proposal")
def get_proposal(booth_id: str):

    response = (
        supabase.table(
            "project_proposals"
        )
        .select("*")
        .eq(
            "booth_request_id",
            booth_id
        )
        .execute()
    )

    return {
        "success": True,
        "data": response.data
    }


@router.get("/{booth_id}/proposal/pdf")
def generate_proposal_pdf(booth_id: str):

    # Load proposal
    proposal_response = (
        supabase.table("project_proposals")
        .select("*")
        .eq("booth_request_id", booth_id)
        .execute()
    )

    if not proposal_response.data:
        raise HTTPException(
            status_code=404,
            detail="Proposal not found"
        )

    proposal = proposal_response.data[0]

    # Load booth
    booth_response = (
        supabase.table("booth_requests")
        .select("*")
        .eq("id", booth_id)
        .execute()
    )

    booth = booth_response.data[0]

    # Load generated image
    image_response = (
        supabase.table("generated_images")
        .select("*")
        .eq(
            "booth_request_id",
            booth_id
        )
        .execute()
    )

    image_url = image_response.data[0]["image_url"]

    file_path = (
        f"generated_pdfs/proposal-{booth_id}.pdf"
    )

    pdf_path = generate_pdf(
        proposal,
        booth,
        image_url,
        file_path
    )

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"proposal-{booth_id}.pdf"
    )


