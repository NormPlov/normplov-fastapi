from typing import Optional

import pandas as pd
import logging
import json
import uuid

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload
from fastapi import HTTPException

from app.models.dimension_study_technique import DimensionStudyTechnique
from app.models.study_technique import StudyTechnique
from app.schemas.learning_style_assessment import LearningStyleChart, LearningStyleResponse
from app.services.test import create_user_test
from ml_models.model_loader import load_vark_model
from app.models import (
    AssessmentType, Major, CareerMajor, SchoolMajor, School, UserResponse, Dimension, Question, DimensionCareer, UserTest, CareerCategoryResponsibility,
    CareerCategory, CareerCategoryLink
)

logger = logging.getLogger(__name__)
vark_model = load_vark_model()


async def get_assessment_type_id(name: str, db: AsyncSession) -> int:
    stmt = select(AssessmentType.id).where(AssessmentType.name == name)
    result = await db.execute(stmt)
    assessment_type_id = result.scalars().first()

    if not assessment_type_id:
        raise HTTPException(status_code=404, detail=f"Assessment type '{name}' not found.")
    return assessment_type_id

# Stable version of prediction
# async def predict_learning_style(
#     data: dict,
#     db: AsyncSession,
#     current_user,
#     final_user_test: Optional[UserTest] = None
# ):
#     try:
#         assessment_type_id = await get_assessment_type_id("Learning Style", db)
#
#         user_test = final_user_test if final_user_test else await create_user_test(db, current_user.id, assessment_type_id)
#
#         stmt = select(Question).options(joinedload(Question.dimension))
#         result = await db.execute(stmt)
#         questions = result.scalars().all()
#
#         if isinstance(data, dict):
#             normalized_answers = {key.replace("/", "").replace("ReadWrite", "Read/Write"): value for key, value in data.items()}
#         else:
#             normalized_answers = {key.replace("/", ""): value for key, value in data.responses.items()}
#
#         input_data_dict = {}
#         missing_questions = []
#
#         for question in questions:
#             if not question.dimension:
#                 raise HTTPException(
#                     status_code=500,
#                     detail=f"Dimension missing for question ID {question.id}",
#                 )
#
#             question_key = f"Q{question.id}_{question.dimension.name.replace('/', '')}"
#
#             answer = normalized_answers.get(question_key)
#             if answer is not None:
#                 input_data_dict[question_key] = answer
#             else:
#                 input_data_dict[question_key] = 0
#                 missing_questions.append(question.question_text)
#
#         if missing_questions:
#             logger.warning(f"Missing answers for questions: {missing_questions}")
#
#         input_data = pd.DataFrame([input_data_dict]).reindex(
#             columns=vark_model.feature_names_in_, fill_value=0
#         )
#         predicted_scores = vark_model.predict(input_data)
#
#         predicted_probs_df = pd.DataFrame(
#             predicted_scores,
#             columns=["Visual_Prob", "Auditory_Prob", "ReadWrite_Prob", "Kinesthetic_Prob"],
#         )
#
#         total_score = predicted_probs_df.sum(axis=1).iloc[0]
#         predicted_probs_df = predicted_probs_df.div(total_score, axis=1)
#
#         row = predicted_probs_df.iloc[0]
#         learning_style = row.idxmax().replace("_Prob", "").replace("ReadWrite", "Read/Write")
#         max_prob = row.max()
#
#         chart_data = {
#             "labels": ["Visual Learning", "Auditory Learning", "Read/Write Learning", "Kinesthetic Learning"],
#             "values": [
#                 round(row["Visual_Prob"] * 100, 2),
#                 round(row["Auditory_Prob"] * 100, 2),
#                 round(row["ReadWrite_Prob"] * 100, 2),
#                 round(row["Kinesthetic_Prob"] * 100, 2),
#             ],
#         }
#
#         dimension_details = []
#         recommended_techniques = []
#         related_careers = []
#
#         for style, prob in row.items():
#             dimension_name = style.replace("_Prob", "").replace("ReadWrite", "Read/Write")
#             dimension_stmt = select(Dimension).where(Dimension.name == dimension_name)
#             dimension = await db.execute(dimension_stmt)
#             dimension = dimension.scalars().first()
#
#             if dimension:
#                 percentage = round(prob * 100, 2)
#
#                 if prob > 0.6:
#                     level = 3
#                 elif prob >= 0.3:
#                     level = 2
#                 else:
#                     level = 1
#
#                 careers_stmt = (
#                     select(DimensionCareer)
#                     .options(joinedload(DimensionCareer.career))
#                     .where(DimensionCareer.dimension_id == dimension.id)
#                 )
#                 careers = await db.execute(careers_stmt)
#                 careers = careers.scalars().all()
#
#                 for career in careers:
#                     career_info = {
#                         "career_name": career.career.name,
#                         "description": career.career.description,
#                         "majors": [],
#                     }
#
#                     career_majors_stmt = (
#                         select(Major)
#                         .join(CareerMajor, CareerMajor.major_id == Major.id)
#                         .where(CareerMajor.career_id == career.career.id, CareerMajor.is_deleted == False)
#                     )
#                     result = await db.execute(career_majors_stmt)
#                     majors = result.scalars().all()
#
#                     for major in majors:
#                         major_info = {"major_name": major.name, "schools": []}
#
#                         schools_stmt = (
#                             select(School)
#                             .join(SchoolMajor, SchoolMajor.school_id == School.id)
#                             .where(SchoolMajor.major_id == major.id, SchoolMajor.is_deleted == False)
#                         )
#                         result = await db.execute(schools_stmt)
#                         schools = result.scalars().all()
#
#                         major_info["schools"] = [school.en_name for school in schools]
#                         career_info["majors"].append(major_info)
#
#                     related_careers.append(career_info)
#
#                 dimension_details.append(
#                     {
#                         "dimension_name": dimension.name,
#                         "dimension_description": dimension.description,
#                         "level": level,
#                     }
#                 )
#
#         highest_scoring_dimension_stmt = select(Dimension).where(Dimension.name == learning_style)
#         highest_scoring_dimension = await db.execute(highest_scoring_dimension_stmt)
#         highest_scoring_dimension = highest_scoring_dimension.scalars().first()
#
#         if highest_scoring_dimension:
#             techniques_stmt = select(LearningStyleStudyTechnique).where(
#                 LearningStyleStudyTechnique.dimension_id == highest_scoring_dimension.id,
#                 LearningStyleStudyTechnique.is_deleted == False,
#             )
#             techniques = await db.execute(techniques_stmt)
#             recommended_techniques = [
#                 {
#                     "technique_name": t.technique_name,
#                     "category": t.category,
#                     "description": t.description,
#                     "image_url": f"{t.image_url}",
#                 }
#                 for t in techniques.scalars().all()
#             ]
#
#         unique_careers = list({c["career_name"]: c for c in related_careers}.values())
#
#         response = LearningStyleResponse(
#             user_uuid=current_user.uuid,
#             test_uuid=str(user_test.uuid),
#             test_name=user_test.name,
#             learning_style=learning_style,
#             probability=round(max_prob * 100, 2),
#             details=row.to_dict(),
#             chart=LearningStyleChart(labels=chart_data["labels"], values=chart_data["values"]),
#             dimensions=dimension_details,
#             recommended_techniques=recommended_techniques,
#             related_careers=unique_careers,
#         )
#
#         user_responses = UserResponse(
#             uuid=str(uuid.uuid4()),
#             user_id=current_user.id,
#             user_test_id=user_test.id,
#             assessment_type_id=assessment_type_id,
#             response_data=json.dumps(response.dict()),
#             is_completed=True,
#             created_at=datetime.utcnow(),
#         )
#         db.add(user_responses)
#
#         for style, prob in row.items():
#             dimension_name = style.replace("_Prob", "")
#             dimension_stmt = select(Dimension).where(Dimension.name == dimension_name)
#             dimension = await db.execute(dimension_stmt)
#             dimension = dimension.scalars().first()
#
#             if dimension:
#                 user_assessment_score = UserAssessmentScore(
#                     uuid=str(uuid.uuid4()),
#                     user_id=current_user.id,
#                     user_test_id=user_test.id,
#                     assessment_type_id=assessment_type_id,
#                     dimension_id=dimension.id,
#                     score=json.dumps({style: prob}),
#                     created_at=datetime.utcnow(),
#                 )
#                 db.add(user_assessment_score)
#
#         await db.commit()
#
#         return response.dict()
#
#     except Exception as e:
#         logger.exception("An error occurred during prediction.")
#         await db.rollback()
#         raise HTTPException(status_code=500, detail="Internal Server Error")


async def predict_learning_style(
    data: dict,
    db: AsyncSession,
    current_user,
    final_user_test: Optional[UserTest] = None
):
    try:
        assessment_type_id = await get_assessment_type_id("Learning Style", db)

        user_test = final_user_test if final_user_test else await create_user_test(db, current_user.id, assessment_type_id)

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
        learning_style = row.idxmax().replace("_Prob", "").replace("ReadWrite", "Read/Write")
        max_prob = row.max()

        logger.debug("learning_style", learning_style)

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
        # related_careers = []
        #
        # for style, prob in row.items():
        #     dimension_name = style.replace("_Prob", "").replace("ReadWrite", "Read/Write")
        #     dimension_stmt = select(Dimension).where(Dimension.name == dimension_name)
        #     dimension = await db.execute(dimension_stmt)
        #     dimension = dimension.scalars().first()
        #
        #     if dimension:
        #         percentage = round(prob * 100, 2)
        #
        #         if prob > 0.6:
        #             level = 3
        #         elif prob >= 0.3:
        #             level = 2
        #         else:
        #             level = 1
        #
        #         careers_stmt = (
        #             select(DimensionCareer)
        #             .options(joinedload(DimensionCareer.career))
        #             .where(DimensionCareer.dimension_id == dimension.id)
        #         )
        #         careers = await db.execute(careers_stmt)
        #         careers = careers.scalars().all()
        #
        #         for career in careers:
        #             # Step 1: Retrieve career category links
        #             category_links_stmt = select(CareerCategoryLink).where(
        #                 CareerCategoryLink.career_id == career.career.id
        #             )
        #             category_links_result = await db.execute(category_links_stmt)
        #             career_category_links = category_links_result.scalars().all()
        #
        #             career_categories = []
        #
        #             for link in career_category_links:
        #                 # Step 2: Fetching category details
        #                 category_stmt = select(CareerCategory).where(CareerCategory.id == link.career_category_id)
        #                 category_result = await db.execute(category_stmt)
        #                 career_category = category_result.scalars().first()
        #
        #                 if career_category:
        #                     category_info = {
        #                         "category_name": career_category.name,
        #                         "responsibilities": [],
        #                     }
        #
        #                     # Step 3: Fetching responsibilities for this category
        #                     responsibilities_stmt = (
        #                         select(CareerCategoryResponsibility)
        #                         .where(CareerCategoryResponsibility.career_category_id == career_category.id)
        #                     )
        #                     responsibilities_result = await db.execute(responsibilities_stmt)
        #                     responsibilities = responsibilities_result.scalars().all()
        #                     category_info["responsibilities"] = [r.description for r in responsibilities]
        #
        #                     career_categories.append(category_info)
        #
        #             # Step 4: Compile career information along with categories
        #             career_info = {
        #                 "career_uuid": str(career.career.uuid),
        #                 "career_name": career.career.name,
        #                 "description": career.career.description,
        #                 "categories": career_categories,
        #                 "majors": [],
        #             }
        #
        #             # Step 5: Fetching major details
        #             career_majors_stmt = (
        #                 select(Major)
        #                 .join(CareerMajor, CareerMajor.major_id == Major.id)
        #                 .where(CareerMajor.career_id == career.career.id, CareerMajor.is_deleted == False)
        #             )
        #             result = await db.execute(career_majors_stmt)
        #             majors = result.scalars().all()
        #
        #             for major in majors:
        #                 major_info = {"major_name": major.name, "schools": []}
        #
        #                 # Step 6: Fetching schools related to each major
        #                 schools_stmt = (
        #                     select(School)
        #                     .join(SchoolMajor, SchoolMajor.school_id == School.id)
        #                     .where(SchoolMajor.major_id == major.id, SchoolMajor.is_deleted == False)
        #                 )
        #                 result = await db.execute(schools_stmt)
        #                 schools = result.scalars().all()
        #
        #                 major_info["schools"] = [school.en_name for school in schools]
        #                 career_info["majors"].append(major_info)
        #
        #             related_careers.append(career_info)
        #
        #         dimension_details.append(
        #             {
        #                 "dimension_name": dimension.name,
        #                 "dimension_description": dimension.description,
        #                 "level": level,
        #             }
        #         )
        #
        # highest_scoring_dimension_stmt = select(Dimension).where(Dimension.name == learning_style)
        # highest_scoring_dimension = await db.execute(highest_scoring_dimension_stmt)
        # highest_scoring_dimension = highest_scoring_dimension.scalars().first()
        #
        # if highest_scoring_dimension:
        #     techniques_stmt = select(LearningStyleStudyTechnique).where(
        #         LearningStyleStudyTechnique.dimension_id == highest_scoring_dimension.id,
        #         LearningStyleStudyTechnique.is_deleted == False,
        #     )
        #     techniques = await db.execute(techniques_stmt)
        #     recommended_techniques = [
        #         {
        #             "technique_name": t.technique_name,
        #             "category": t.category,
        #             "description": t.description,
        #             "image_url": f"{t.image_url}",
        #         }
        #         for t in techniques.scalars().all()
        #     ]
        #
        # unique_careers = list({c["career_name"]: c for c in related_careers}.values())
        #
        # response = LearningStyleResponse(
        #     user_uuid=current_user.uuid,
        #     test_uuid=str(user_test.uuid),
        #     test_name=user_test.name,
        #     learning_style=learning_style,
        #     probability=round(max_prob * 100, 2),
        #     details=row.to_dict(),
        #     chart=LearningStyleChart(labels=chart_data["labels"], values=chart_data["values"]),
        #     dimensions=dimension_details,
        #     recommended_techniques=recommended_techniques,
        #     related_careers=unique_careers,
        # )
        #
        # user_responses = UserResponse(
        #     uuid=str(uuid.uuid4()),
        #     user_id=current_user.id,
        #     user_test_id=user_test.id,
        #     assessment_type_id=assessment_type_id,
        #     response_data=json.dumps(response.dict()),
        #     is_completed=True,
        #     created_at=datetime.utcnow(),
        # )
        # db.add(user_responses)
        #
        # for style, prob in row.items():
        #     dimension_name = style.replace("_Prob", "")
        #     dimension_stmt = select(Dimension).where(Dimension.name == dimension_name)
        #     dimension = await db.execute(dimension_stmt)
        #     dimension = dimension.scalars().first()
        #
        #     if dimension:
        #         user_assessment_score = UserAssessmentScore(
        #             uuid=str(uuid.uuid4()),
        #             user_id=current_user.id,
        #             user_test_id=user_test.id,
        #             assessment_type_id=assessment_type_id,
        #             dimension_id=dimension.id,
        #             score=json.dumps({style: prob}),
        #             created_at=datetime.utcnow(),
        #         )
        #         db.add(user_assessment_score)
        #
        # await db.commit()
        #
        # return response.dict()

        related_careers = []
        processed_career_uuids = set()  # Track processed career UUIDs

        dimension_details = []
        recommended_techniques = []

        for style, prob in row.items():
            dimension_name = style
            dimension_stmt = select(Dimension).where(Dimension.name == dimension_name)
            dimension = await db.execute(dimension_stmt)
            dimension = dimension.scalars().first()

            if dimension:
                logger.debug(f"Found dimension: {dimension.name}")
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
                    # Check if the career has already been processed
                    if career.career.uuid in processed_career_uuids:
                        continue

                    processed_career_uuids.add(career.career.uuid)

                    # Step 1: Retrieve career category links
                    category_links_stmt = select(CareerCategoryLink).where(
                        CareerCategoryLink.career_id == career.career.id
                    )
                    category_links_result = await db.execute(category_links_stmt)
                    career_category_links = category_links_result.scalars().all()

                    career_categories = []

                    for link in career_category_links:
                        # Step 2: Fetching category details
                        category_stmt = select(CareerCategory).where(CareerCategory.id == link.career_category_id)
                        category_result = await db.execute(category_stmt)
                        career_category = category_result.scalars().first()

                        if career_category:
                            category_info = {
                                "category_name": career_category.name,
                                "responsibilities": [],
                            }

                            # Step 3: Fetching responsibilities for this category
                            responsibilities_stmt = (
                                select(CareerCategoryResponsibility)
                                .where(CareerCategoryResponsibility.career_category_id == career_category.id)
                            )
                            responsibilities_result = await db.execute(responsibilities_stmt)
                            responsibilities = responsibilities_result.scalars().all()
                            category_info["responsibilities"] = [r.description for r in responsibilities]

                            career_categories.append(category_info)

                    # Step 4: Compile career information along with categories
                    career_info = {
                        "career_uuid": str(career.career.uuid),
                        "career_name": career.career.name,
                        "description": career.career.description,
                        "categories": career_categories,
                        "majors": [],
                    }

                    # Step 5: Fetching major details
                    career_majors_stmt = (
                        select(Major)
                        .join(CareerMajor, CareerMajor.major_id == Major.id)
                        .where(CareerMajor.career_id == career.career.id, CareerMajor.is_deleted == False)
                    )
                    result = await db.execute(career_majors_stmt)
                    majors = result.scalars().all()

                    for major in majors:
                        major_info = {"major_name": major.name, "schools": []}

                        # Step 6: Fetching schools related to each major
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
            else:
                logger.warning(f"Dimension not found for name: {dimension_name}")

        # Adjust learning style name to include "_Prob" suffix for comparison
        learning_style_with_prob = f"{learning_style}_Prob"

        # Query for the dimension with the adjusted name
        highest_scoring_dimension_stmt = select(Dimension).where(Dimension.name == learning_style_with_prob)
        highest_scoring_dimension_result = await db.execute(highest_scoring_dimension_stmt)
        highest_scoring_dimension = highest_scoring_dimension_result.scalars().first()

        # Query for recommended techniques
        if highest_scoring_dimension:
            logger.debug(f"Found highest scoring dimension: {highest_scoring_dimension.name}")

            techniques_stmt = (
                select(StudyTechnique)
                .join(DimensionStudyTechnique, DimensionStudyTechnique.study_technique_id == StudyTechnique.id)
                .options(selectinload(StudyTechnique.category))  # Eagerly load the category relationship
                .where(
                    DimensionStudyTechnique.dimension_id == highest_scoring_dimension.id,
                    StudyTechnique.is_deleted == False
                )
            )
            techniques_result = await db.execute(techniques_stmt)

            try:
                recommended_techniques = [
                    {
                        "technique_name": technique.name,
                        "category": technique.category.name if technique.category else "Uncategorized",
                        "description": technique.description,
                    }
                    for technique in techniques_result.scalars().all()
                ]
            except Exception as e:
                logger.error(f"Error while constructing recommended techniques: {e}")
                recommended_techniques = []

            logger.debug(f"Recommended techniques: {recommended_techniques}")
        else:
            logger.warning(f"No dimension found for learning style: {learning_style_with_prob}")
            recommended_techniques = []

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
            related_careers=related_careers,  # No duplicates
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

        await db.commit()

        return response.dict()

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"An unexpected error occurred during the prediction process. Please check your input or try again."

        )
