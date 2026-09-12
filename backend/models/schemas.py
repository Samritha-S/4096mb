from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question asked by the user")
    max_results: int = Field(default=5, ge=1, le=10)


class Citation(BaseModel):
    title: str
    url: str
    snippet: str


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation] = []
