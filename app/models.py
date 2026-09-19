from pydantic import BaseModel


class RecommendationRequest(BaseModel):
    postcode: str
    plants: list[str] | None = None
    orientation: str | None = None
    shade: str | None = None
    soil_type: str | None = None
    experience_level: str | None = None


class Action(BaseModel):
    priority: int
    title: str
    detail: str
    category: str
    urgent: bool = False


class Inference(BaseModel):
    field: str
    value: str | list
    confidence: str
    reasoning: str


class RecommendationResponse(BaseModel):
    week: str
    actions: list[Action]
    inferences: list[Inference] = []
    plant_suggestions: list[str] = []
    notes: str | None = None
