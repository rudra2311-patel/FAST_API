from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.main import get_session
from .models import Farm
from .schemas import FarmCreate, FarmResponse
from src.auth.dependencies import AccessTokenBearer

router = APIRouter()


# ---------------------- Add Farm ----------------------
@router.post("/add", response_model=FarmResponse)
async def add_farm(
    data: FarmCreate,
    session: AsyncSession = Depends(get_session),
    token_data: dict = Depends(AccessTokenBearer())
):
    user_id = token_data["user"]["user_id"]

    farm = Farm(
        user_id=user_id,
        name=data.name,  # ADDED: Save farm name
        lat=data.lat,
        lon=data.lon,
        crop=data.crop,
    )

    session.add(farm)
    await session.commit()
    await session.refresh(farm)

    return farm


# ---------------------- Get My Farms ----------------------
@router.get("/my", response_model=list[FarmResponse])
async def get_my_farms(
    session: AsyncSession = Depends(get_session),
    token_data: dict = Depends(AccessTokenBearer())
):
    user_id = token_data["user"]["user_id"]

    query = select(Farm).where(Farm.user_id == user_id)
    result = await session.exec(query)  # MUST await
    farms = result.all()

    return farms


# ---------------------- Delete Farm ----------------------
@router.delete("/{farm_id}")
async def delete_farm(
    farm_id: str,
    session: AsyncSession = Depends(get_session),
    token_data: dict = Depends(AccessTokenBearer())
):
    user_id = token_data["user"]["user_id"]

    farm = await session.get(Farm, farm_id)

    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    if str(farm.user_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to delete this farm")

    # ✅ Close any active WebSocket connections for this farm
    try:
        from src.weather.websocket_manager import manager
        disconnected = await manager.disconnect_by_user_and_location(
            user_id=str(user_id),
            lat=farm.lat,
            lon=farm.lon,
            crop=farm.crop
        )
        if disconnected > 0:
            print(f"🔌 Closed {disconnected} WebSocket connection(s) for deleted farm")
    except Exception as e:
        print(f"⚠️ Warning: Could not close WebSocket connections: {e}")
        # Continue with deletion even if WebSocket cleanup fails

    await session.delete(farm)
    await session.commit()

    return {
        "message": "Farm deleted successfully",
        "websocket_connections_closed": disconnected if 'disconnected' in locals() else 0
    }
