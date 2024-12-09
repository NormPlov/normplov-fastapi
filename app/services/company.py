import os

from fastapi import UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Company
import uuid
from app.core.config import settings
from app.schemas.company import CompanyCreateRequest, CompanyResponse
from app.schemas.payload import BaseResponse
from datetime import datetime
from app.utils.pagination import paginate_results


async def load_company_by_uuid(db: AsyncSession, company_uuid: uuid.UUID) -> BaseResponse:
    try:
        stmt = select(Company).where(Company.is_deleted == False, Company.uuid == company_uuid)
        result = await db.execute(stmt)
        company = result.scalars().first()

        if not company:
            raise HTTPException(status_code=404, detail="Company not found.")

        company_data = CompanyResponse(
            company_uuid=company.uuid,
            company_name=company.name,
            company_address=company.address,
            company_logo=company.logo,
            company_website=company.website,
            company_linkedin=company.linkedin,
            company_twitter=company.twitter,
            company_facebook=company.facebook,
            company_instagram=company.instagram,
        )

        response = BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="Company loaded successfully.",
            payload={"company": company_data}
        )

        return response

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading company: {str(e)}")


async def load_all_companies(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10
) -> BaseResponse:
    try:

        stmt = select(Company).where(Company.is_deleted == False)
        result = await db.execute(stmt)
        companies = result.scalars().all()

        if not companies:
            raise HTTPException(status_code=404, detail="No companies found.")

        paginated_companies = paginate_results(companies, page, page_size)

        companies_data = [
            CompanyResponse(
                company_uuid=company.uuid,
                company_name=company.name,
                company_address=company.address,
                company_logo=company.logo,
                company_website=company.website,
                company_linkedin=company.linkedin,
                company_twitter=company.twitter,
                company_facebook=company.facebook,
                company_instagram=company.instagram,
            )
            for company in paginated_companies['items']
        ]

        response = BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="Companies loaded successfully.",
            payload={"companies": companies_data, "metadata": paginated_companies["metadata"]}
        )

        return response

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading companies: {str(e)}")


async def delete_company(db: AsyncSession, company_uuid: uuid.UUID) -> BaseResponse:
    try:
        stmt = select(Company).where(Company.uuid == company_uuid)
        result = await db.execute(stmt)
        company = result.scalars().first()

        if not company:
            raise HTTPException(status_code=404, detail="Company not found.")

        company.is_deleted = True
        db.add(company)
        await db.commit()

        response = BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="Company deleted successfully.",
            payload={"company_uuid": company.uuid, "company_name": company.name}
        )

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting the company: {str(e)}")


async def update_company(db: AsyncSession, company_uuid: uuid.UUID, company_data: CompanyCreateRequest) -> BaseResponse:
    try:
        stmt = select(Company).where(Company.uuid == company_uuid)
        result = await db.execute(stmt)
        company = result.scalars().first()

        if not company:
            raise HTTPException(status_code=404, detail="Company not found.")

        company.name = company_data.name or company.name
        company.address = company_data.address or company.address
        company.linkedin = company_data.linkedin or company.linkedin
        company.twitter = company_data.twitter or company.twitter
        company.facebook = company_data.facebook or company.facebook
        company.instagram = company_data.instagram or company.instagram
        company.website = company_data.website or company.website

        db.add(company)
        await db.commit()
        await db.refresh(company)

        response = BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="Company updated successfully.",
            payload={"company_uuid": company.uuid, "company_name": company.name}
        )

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating the company: {str(e)}")


async def upload_company_logo(
        db: AsyncSession,
        company_uuid: uuid.UUID,
        file: UploadFile = File(...)
) -> BaseResponse:
    try:
        file_location = os.path.join(settings.BASE_UPLOAD_FOLDER, "companies", f"{company_uuid}_{file.filename}")

        with open(file_location, "wb") as buffer:
            buffer.write(file.file.read())

        stmt = select(Company).filter(Company.uuid == company_uuid)
        result = await db.execute(stmt)
        company = result.scalars().first()

        if not company:
            raise HTTPException(status_code=404, detail="Company not found.")

        company.logo = f"/uploads/companies/{company_uuid}_{file.filename}"
        db.add(company)
        await db.commit()
        await db.refresh(company)

        response = BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=200,
            message="Company logo uploaded successfully.",
            payload={"logo_url": company.logo}
        )
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading the company logo: {str(e)}")


async def create_company(db: AsyncSession, company_data: CompanyCreateRequest) -> BaseResponse:
    try:
        new_company = Company(
            name=company_data.name,
            address=company_data.address,
            linkedin=company_data.linkedin,
            twitter=company_data.twitter,
            facebook=company_data.facebook,
            instagram=company_data.instagram,
            website=company_data.website,
        )

        db.add(new_company)
        await db.commit()
        await db.refresh(new_company)

        response = BaseResponse(
            date=datetime.utcnow().strftime("%d-%B-%Y"),
            status=201,
            message="Company created successfully.",
            payload={"company_uuid": new_company.uuid, "company_name": new_company.name}
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating company: {str(e)}")