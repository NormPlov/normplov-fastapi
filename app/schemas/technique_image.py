from pydantic import BaseModel


class LearningStyleTechniqueImageResponse(BaseModel):
    id: int
    file_name: str
    file_url: str
    file_type: str
