# src/scans/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_session
from src.auth.dependencies import AccessTokenBearer
from src.db.redis import is_jti_blacklisted
from src.scans.schemas import ScanCreate, ScanRead
from src.scans.services import ScanService
import uuid

router = APIRouter(prefix="/scans", tags=["scans"])
scan_service = ScanService()


# simulate image storage — later replace with S3 or Firebase
async def save_image(image_base64: str) -> str:
    """simulate storing an image and returning a URL"""
    if not image_base64:
        return "https://example-bucket.s3.amazonaws.com/default.jpg"
    file_id = uuid.uuid4().hex
    return f"https://example-bucket.s3.amazonaws.com/{file_id}.jpg"


@router.post("/upload", response_model=ScanRead)
async def upload_scan(
    scan_data: ScanCreate,
    token_data: dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session)
):
    # 1️⃣ check if token has been revoked (logout or refresh)
    if await is_jti_blacklisted(token_data["jti"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    # 2️⃣ extract user_id from token payload (nested inside 'user')
    user_id = uuid.UUID(token_data["user"]["user_id"])

    # 3️⃣ simulate saving image
    image_url = await save_image(scan_data.image_base64)

    # 4️⃣ create new scan record
    scan = await scan_service.create_scan(user_id, scan_data, image_url, session)
    return scan


@router.get("/history", response_model=list[ScanRead])
async def get_scan_history(
    token_data: dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session)
):
    # 1️⃣ check if token has been revoked
    if await is_jti_blacklisted(token_data["jti"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    # 2️⃣ extract user_id correctly
    user_id = uuid.UUID(token_data["user"]["user_id"])

    # 3️⃣ fetch all user scans
    scans = await scan_service.get_user_scans(user_id, session)
    return scans


@router.delete("/{scan_id}")
async def delete_single_scan(
    scan_id: uuid.UUID,
    token_data: dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a specific scan by ID.
    Only the scan owner can delete it.
    """
    # 1️⃣ check if token has been revoked
    if await is_jti_blacklisted(token_data["jti"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    # 2️⃣ extract user_id
    user_id = uuid.UUID(token_data["user"]["user_id"])

    print(f"🔍 DELETE REQUEST - Scan ID: {scan_id}, User ID: {user_id}")

    # 🔍 Debug: Check if scan exists at all
    scan = await scan_service.get_single_scan(scan_id, session)
    
    print(f"🔍 SCAN FOUND: {scan}")
    
    if not scan:
        print(f"❌ Scan {scan_id} NOT FOUND in database")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID {scan_id} does not exist"
        )
    
    print(f"🔍 SCAN USER ID: {scan.user_id}, REQUEST USER ID: {user_id}")
    
    if scan.user_id != user_id:
        print(f"❌ Permission denied - scan belongs to {scan.user_id}, requester is {user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this scan"
        )

    # 3️⃣ delete the scan
    deleted = await scan_service.delete_scan(scan_id, user_id, session)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete scan"
        )

    print(f"✅ Scan {scan_id} deleted successfully")
    return {"message": "Scan deleted successfully", "scan_id": str(scan_id)}


@router.delete("/history/clear")
async def clear_scan_history(
    token_data: dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete ALL scans for the current user.
    Only deletes the authenticated user's own scan history.
    """
    # 1️⃣ check if token has been revoked
    if await is_jti_blacklisted(token_data["jti"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    # 2️⃣ extract user_id
    user_id = uuid.UUID(token_data["user"]["user_id"])

    # 3️⃣ delete all user's scans
    deleted_count = await scan_service.delete_all_user_scans(user_id, session)

    return {
        "message": "Scan history cleared successfully",
        "deleted_count": deleted_count
    }
