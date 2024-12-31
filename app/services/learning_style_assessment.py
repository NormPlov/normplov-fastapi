import pandas as pd
import logging
import json
import uuid
import os

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.core.config import settings
from fastapi import HTTPException, UploadFile
from app.exceptions.file_exceptions import FileExtensionError, FileSizeError, handle_file_error
from app.models import (
    AssessmentType, Major, CareerMajor, SchoolMajor, School, UserResponse, UserAssessmentScore,
    LearningStyleStudyTechnique, Dimension, Question, DimensionCareer, UserTest
)
from app.schemas.learning_style_assessment import LearningStyleChart, LearningStyleResponse
from app.services.test import create_user_test
from ml_models.model_loader import load_vark_model

logger = logging.getLogger(__name__)
vark_model = load_vark_model()


async def upload_technique_image(db: AsyncSession, technique_uuid: str, file: UploadFile):
    try:

        extension = file.filename.split(".")[-1].lower()
        if extension not in settings.ALLOWED_EXTENSIONS:
            raise FileExtensionError(settings.ALLOWED_EXTENSIONS)

        file_size = file.file.seek(0, os.SEEK_END)
        file.file.seek(0)
        if file_size > settings.MAX_FILE_SIZE:
            raise FileSizeError(settings.MAX_FILE_SIZE)

        technique_query = select(LearningStyleStudyTechnique).where(
            LearningStyleStudyTechnique.uuid == technique_uuid,
            LearningStyleStudyTechnique.is_deleted == False
        )
        technique_result = await db.execute(technique_query)
        technique = technique_result.scalars().first()

        if not technique:
            raise HTTPException(status_code=404, detail="Technique not found.")

        upload_folder = os.path.join(settings.BASE_UPLOAD_FOLDER, "techniques")
        os.makedirs(upload_folder, exist_ok=True)

        file_name = f"{technique.uuid}_{file.filename}"
        file_path = os.path.join(upload_folder, file_name)

        try:
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

        technique.image_url = os.path.join("techniques", file_name)
        await db.commit()
        await db.refresh(technique)

        return {
            "technique_uuid": technique.uuid,
            "image_url": f"/{settings.BASE_UPLOAD_FOLDER}/techniques/{file_name}",
        }

    except (FileExtensionError, FileSizeError) as e:
        raise handle_file_error(e)
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


async def get_assessment_type_id(name: str, db: AsyncSession) -> int:
    stmt = select(AssessmentType.id).where(AssessmentType.name == name)
    result = await db.execute(stmt)
    assessment_type_id = result.scalars().first()

    if not assessment_type_id:
        raise HTTPException(status_code=404, detail=f"Assessment type '{name}' not found.")
    return assessment_type_id


async def predict_learning_style(
    data: dict,
    db: AsyncSession,
    current_user,
):
    try:
        assessment_type_id = await get_assessment_type_id("Learning Style", db)

        try:
            user_test = await create_user_test(db, current_user.id, assessment_type_id)
            logger.debug(f"Created new test: uuid={user_test.uuid}, name={user_test.name}")
        except Exception as e:
            logger.error(f"Failed to create test for user_id={current_user.id}: {e}")
            await db.rollback()
            raise HTTPException(status_code=500, detail="Failed to create a new test.")

        stmt = select(Question).options(joinedload(Question.dimension))
        result = await db.execute(stmt)
        questions = result.scalars().all()

        if isinstance(data, dict):
            normalized_answers = {key.replace("/", "").replace("ReadWrite", "Read/Write"): value for key, value in data.items()}
        else:
            normalized_answers = {key.replace("/", ""): value for key, value in data.responses.items()}

        input_data_dict = {}
        missing_questions = []

        for question in questions:
            if not question.dimension:
                logger.error(f"Dimension missing for question ID {question.id}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Dimension missing for question ID {question.id}",
                )

            question_key = f"Q{question.id}_{question.dimension.name.replace('/', '')}"

            answer = normalized_answers.get(question_key)
            if answer is not None:
                input_data_dict[question_key] = answer
            else:
                input_data_dict[question_key] = 0
                missing_questions.append(question.question_text)

        if missing_questions:
            logger.warning(f"Missing answers for questions: {missing_questions}")

        input_data = pd.DataFrame([input_data_dict]).reindex(
            columns=vark_model.feature_names_in_, fill_value=0
        )
        predicted_scores = vark_model.predict(input_data)

        predicted_probs_df = pd.DataFrame(
            predicted_scores,
            columns=["Visual_Prob", "Auditory_Prob", "ReadWrite_Prob", "Kinesthetic_Prob"],
        )

        total_score = predicted_probs_df.sum(axis=1).iloc[0]
        predicted_probs_df = predicted_probs_df.div(total_score, axis=1)

        row = predicted_probs_df.iloc[0]
        learning_style = row.idxmax().replace("_Prob", "")
        max_prob = row.max()

        chart_data = {
            "labels": ["Visual Learning", "Auditory Learning", "Read/Write Learning", "Kinesthetic Learning"],
            "values": [
                round(row["Visual_Prob"] * 100, 2),
                round(row["Auditory_Prob"] * 100, 2),
                round(row["ReadWrite_Prob"] * 100, 2),
                round(row["Kinesthetic_Prob"] * 100, 2),
            ],
        }

        dimension_details = []
        recommended_techniques = []
        related_careers = []

        for style, prob in row.items():
            dimension_name = style.replace("_Prob", "").replace("ReadWrite", "Read/Write")
            dimension_stmt = select(Dimension).where(Dimension.name == dimension_name)
            dimension = await db.execute(dimension_stmt)
            dimension = dimension.scalars().first()

            if dimension:
                percentage = round(prob * 100, 2)

                if prob > 0.6:
                    level = 3
                elif prob >= 0.3:
                    level = 2
                else:
                    level = 1

                careers_stmt = (
                    select(DimensionCareer)
                    .options(joinedload(DimensionCareer.career))
                    .where(DimensionCareer.dimension_id == dimension.id)
                )
                careers = await db.execute(careers_stmt)
                careers = careers.scalars().all()

                for career in careers:
                    career_info = {
                        "career_name": career.career.name,
                        "description": career.career.description,
                        "majors": [],
                    }

                    career_majors_stmt = (
                        select(Major)
                        .join(CareerMajor, CareerMajor.major_id == Major.id)
                        .where(CareerMajor.career_id == career.career.id, CareerMajor.is_deleted == False)
                    )
                    result = await db.execute(career_majors_stmt)
                    majors = result.scalars().all()

                    for major in majors:
                        major_info = {"major_name": major.name, "schools": []}

                        schools_stmt = (
                            select(School)
                            .join(SchoolMajor, SchoolMajor.school_id == School.id)
                            .where(SchoolMajor.major_id == major.id, SchoolMajor.is_deleted == False)
                        )
                        result = await db.execute(schools_stmt)
                        schools = result.scalars().all()

                        major_info["schools"] = [school.en_name for school in schools]
                        career_info["majors"].append(major_info)

                    related_careers.append(career_info)

                dimension_details.append(
                    {
                        "dimension_name": dimension.name,
                        "dimension_description": dimension.description,
                        "level": level,
                    }
                )

        highest_scoring_dimension_stmt = select(Dimension).where(Dimension.name == learning_style)
        highest_scoring_dimension = await db.execute(highest_scoring_dimension_stmt)
        highest_scoring_dimension = highest_scoring_dimension.scalars().first()

        if highest_scoring_dimension:
            techniques_stmt = select(LearningStyleStudyTechnique).where(
                LearningStyleStudyTechnique.dimension_id == highest_scoring_dimension.id,
                LearningStyleStudyTechnique.is_deleted == False,
            )
            techniques = await db.execute(techniques_stmt)
            recommended_techniques = [
                {
                    "technique_name": t.technique_name,
                    "category": t.category,
                    "description": t.description,
                    "image_url": f"uploads/{t.image_url}",
                }
                for t in techniques.scalars().all()
            ]

        unique_careers = list({c["career_name"]: c for c in related_careers}.values())

        response = LearningStyleResponse(
            user_uuid=current_user.uuid,
            test_uuid=str(user_test.uuid),
            test_name=user_test.name,
            learning_style=learning_style,
            probability=round(max_prob * 100, 2),
            details=row.to_dict(),
            chart=LearningStyleChart(labels=chart_data["labels"], values=chart_data["values"]),
            dimensions=dimension_details,
            recommended_techniques=recommended_techniques,
            related_careers=unique_careers,
        )

        user_responses = UserResponse(
            uuid=str(uuid.uuid4()),
            user_id=current_user.id,
            user_test_id=user_test.id,
            assessment_type_id=assessment_type_id,
            response_data=json.dumps(response.dict()),
            is_completed=True,
            created_at=datetime.utcnow(),
        )
        db.add(user_responses)

        for style, prob in row.items():
            dimension_name = style.replace("_Prob", "")
            dimension_stmt = select(Dimension).where(Dimension.name == dimension_name)
            dimension = await db.execute(dimension_stmt)
            dimension = dimension.scalars().first()

            if dimension:
                user_assessment_score = UserAssessmentScore(
                    uuid=str(uuid.uuid4()),
                    user_id=current_user.id,
                    user_test_id=user_test.id,
                    assessment_type_id=assessment_type_id,
                    dimension_id=dimension.id,
                    score=json.dumps({style: prob}),
                    created_at=datetime.utcnow(),
                )
                db.add(user_assessment_score)

        await db.commit()

        return response.dict()

    except Exception as e:
        logger.exception("An error occurred during prediction.")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")
