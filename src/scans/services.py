from src.scans.models import Scan
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, desc
import uuid
from datetime import datetime
from typing import List, Optional


class ScanService:
    """Handles all database operations related to Scan objects."""

    async def create_scan(
        self,
        user_id: uuid.UUID,
        scan_data,
        image_url: str,
        session: AsyncSession
    ) -> Scan:
        """
        Create a new scan entry for the given user.
        """
        scan = Scan(
            user_id=user_id,
            disease_name=scan_data.disease_name,
            confidence=scan_data.confidence,
            image_url=image_url,
            created_at=datetime.utcnow(),  # ensure UTC timestamp
        )

        session.add(scan)
        await session.commit()
        await session.refresh(scan)
        return scan

    async def get_user_scans(
        self,
        user_id: uuid.UUID,
        session: AsyncSession
    ) -> List[Scan]:
        """
        Retrieve all scans for a given user, sorted by newest first.
        """
        statement = (
            select(Scan)
            .where(Scan.user_id == user_id)
            .order_by(desc(Scan.created_at))  # ✅ latest first
        )
        result = await session.exec(statement)
        scans = result.all()

        # ✅ return an empty list if user has no scans
        return scans or []

    async def get_single_scan(
        self,
        scan_id: uuid.UUID,
        session: AsyncSession
    ) -> Optional[Scan]:
        """
        Retrieve one specific scan by its ID.
        """
        statement = select(Scan).where(Scan.id == scan_id)
        result = await session.exec(statement)
        scan = result.first()
        return scan

    async def delete_scan(
        self,
        scan_id: uuid.UUID,
        user_id: uuid.UUID,
        session: AsyncSession
    ) -> bool:
        """
        Delete a specific scan if it belongs to the user.
        """
        statement = select(Scan).where(Scan.id == scan_id, Scan.user_id == user_id)
        result = await session.exec(statement)
        scan = result.first()

        if not scan:
            return False

        await session.delete(scan)
        await session.commit()
        return True

    async def delete_all_user_scans(
        self,
        user_id: uuid.UUID,
        session: AsyncSession
    ) -> int:
        """
        Delete ALL scans for a specific user.
        Returns the number of scans deleted.
        """
        statement = select(Scan).where(Scan.user_id == user_id)
        result = await session.exec(statement)
        scans = result.all()

        count = len(scans)
        
        for scan in scans:
            await session.delete(scan)
        
        await session.commit()
        return count
