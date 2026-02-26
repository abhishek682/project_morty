from pydantic import BaseModel


class CharacterOut(BaseModel):
    id: int
    name: str
    status: str
    species: str
    origin_name: str
    origin_url: str | None = None
    image: str | None = None

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    page: int
    limit: int
    total: int
    items: list[CharacterOut]
