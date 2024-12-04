from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import is_admin_user
from app.schemas.payload import BaseResponse
from app.schemas.faculty import CreateFacultyRequest, FacultyListResponse, FacultyDetail, FacultyUpdateRequest
from app.services.faculty import create_faculty, get_all_faculties, delete_faculty, update_faculty
from datetime import datetime

faculty_router = APIRouter()


@faculty_router.delete(
    "/{faculty_uuid}",
    summary="Delete a faculty",
    response_model=BaseResponse,
    dependencies=[Depends(is_admin_user)],
)
async def delete_faculty_route(faculty_uuid: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await delete_faculty(faculty_uuid, db)
        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=status.HTTP_200_OK,
            message=result["message"],
            payload={"uuid": result["uuid"], "name": result["name"]},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )


@faculty_router.put(
    "/{faculty_uuid}",
    summary="Update a faculty",
    response_model=BaseResponse,
    dependencies=[Depends(is_admin_user)],
)
async def update_faculty_route(
    faculty_uuid: str,
    data: FacultyUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        updated_faculty = await update_faculty(faculty_uuid, data.dict(exclude_unset=True), db)
        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=status.HTTP_200_OK,
            message=updated_faculty["message"],
            payload={
                "uuid": updated_faculty["uuid"],
                "name": updated_faculty["name"],
                "description": updated_faculty["description"],
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )


@faculty_router.get(
    "/",
    summary="Fetch all faculties with pagination, filtering, and sorting",
    response_model=BaseResponse,
    dependencies=[Depends(is_admin_user)],
)
async def fetch_all_faculties_route(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    search: str = Query(None, description="Search faculty by name"),
    is_deleted: bool = Query(False, description="Filter by deletion status"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order: 'asc' or 'desc'"),
    db: AsyncSession = Depends(get_db),
):
    try:
        faculties, metadata = await get_all_faculties(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            is_deleted=is_deleted,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        faculty_details = [
            FacultyDetail(
                uuid=faculty["uuid"],
                name=faculty["name"],
                description=faculty["description"],
                school_name=faculty["school_name"],
                created_at=faculty["created_at"],
                updated_at=faculty["updated_at"],
            )
            for faculty in faculties
        ]
        payload = FacultyListResponse(
            faculties=faculty_details,
            metadata=metadata,
        )
        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=status.HTTP_200_OK,
            message="Faculties retrieved successfully",
            payload=payload.dict(),
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )


@faculty_router.post("/", response_model=BaseResponse, summary="Create a new faculty", tags=["Faculty"])
async def create_faculty_route(
    data: CreateFacultyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(is_admin_user)
):
    try:
        faculty = await create_faculty(data, db)
        return BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=status.HTTP_201_CREATED,
            payload=faculty,
            message="Faculty created successfully."
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the faculty: {str(e)}"
        )
