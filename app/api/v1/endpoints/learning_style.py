from app.services.learning_style_assessment import predict_learning_style
from app.schemas.learning_style_assessment import LearningStyleInputDto
from app.models.user import User

# API Endpoint for Learning Style Assessment🥰
@assessment_router.post("/predict-learning-style")
async def predict_learning_style_route(
    data: LearningStyleInputDto,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_data),
):
    return await predict_learning_style(data, db, current_user)
