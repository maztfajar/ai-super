from fastapi import APIRouter

router = APIRouter()

@router.get("/export")
async def export_data():
    """
    Endpoint untuk export data.
    Implementasi minimal untuk menghindari error import.
    """
    return {"message": "Export endpoint - implementasi belum lengkap"}