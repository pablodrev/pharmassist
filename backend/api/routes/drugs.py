"""Drug routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from uuid import UUID

from db import get_session
from models.schemas_db import Drug
from auth import get_current_user
from api_schemas import DrugSearchResponse, DrugResponse

router = APIRouter(prefix="/api/v1/drugs", tags=["drugs"])


@router.get("", response_model=DrugSearchResponse)
async def search_drugs(
    search: str = Query(..., min_length=2),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Search drugs by name."""
    # Simple substring search using ILIKE for case-insensitive matching
    search_pattern = f"%{search}%"
    
    stmt = select(Drug).where(
        or_(
            Drug.name_ru.ilike(search_pattern),
            Drug.name_en.ilike(search_pattern)
        )
    ).limit(10)
    
    result = await session.execute(stmt)
    drugs = result.scalars().all()
    
    items = [
        DrugResponse(
            id=drug.id,
            name_ru=drug.name_ru,
            name_en=drug.name_en,
            atc_code=drug.atc_code
        )
        for drug in drugs
    ]
    
    return DrugSearchResponse(items=items)
