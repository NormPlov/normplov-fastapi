from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Province
from app.schemas.payload import BaseResponse
from app.schemas.province import ProvinceResponse, ProvinceListResponse
from datetime import datetime
from fastapi import HTTPException, status


async def load_provinces(db: AsyncSession) -> BaseResponse:
    try:
        query = select(Province).where(Province.is_deleted == False)
        result = await db.execute(query)
        provinces = result.scalars().all()

        province_responses = [
            ProvinceResponse(
                uuid=str(province.uuid),
                name=province.name,
                created_at=province.created_at,
                updated_at=province.updated_at,
            )
            for province in provinces
        ]

        response_payload = ProvinceListResponse(provinces=province_responses)

        return BaseResponse(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            status=status.HTTP_200_OK,
            message="Provinces loaded successfully.",
            payload=response_payload.dict(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while loading provinces: {str(e)}",
        )
