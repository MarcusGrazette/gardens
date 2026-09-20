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
    why_now: str | None = None
    minutes: int | None = None


class Inference(BaseModel):
    field: str
    value: str | list
    confidence: str
    reasoning: str


class PlantSuggestion(BaseModel):
    name: str
    latin: str | None = None
    note: str | None = None


class RecommendationResponse(BaseModel):
    week: str
    summary: str | None = None
    actions: list[Action]
    inferences: list[Inference] = []
    plant_suggestions: list[PlantSuggestion] = []
    notes: str | None = None
