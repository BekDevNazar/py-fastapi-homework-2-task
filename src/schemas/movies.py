from datetime import date as Date, timedelta

from pydantic import BaseModel, ConfigDict, Field, field_validator

from database.models import MovieStatusEnum


class CountryDetail(BaseModel):
    id: int
    code: str
    name: str | None

    model_config = ConfigDict(from_attributes=True)


class RelatedEntityDetail(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class MovieCreate(BaseModel):
    name: str = Field(max_length=255)
    date: Date
    score: float = Field(ge=0, le=100)
    overview: str
    status: MovieStatusEnum
    budget: float = Field(ge=0)
    revenue: float = Field(ge=0)

    country: str
    genres: list[str]
    actors: list[str]
    languages: list[str]

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: Date):
        max_date = Date.today() + timedelta(days=365)

        if value > max_date:
            raise ValueError(
                "Release date cannot be more than one year in the future."
            )

        return value


class MovieDetail(BaseModel):
    id: int
    name: str
    date: Date
    score: float
    overview: str
    status: str
    budget: float
    revenue: float

    country: CountryDetail
    genres: list[RelatedEntityDetail]
    actors: list[RelatedEntityDetail]
    languages: list[RelatedEntityDetail]

    model_config = ConfigDict(from_attributes=True)


class MovieListItem(BaseModel):
    id: int
    name: str
    date: Date
    score: float
    overview: str

    model_config = ConfigDict(from_attributes=True)


class MovieList(BaseModel):
    movies: list[MovieListItem]
    prev_page: str | None
    next_page: str | None
    total_pages: int
    total_items: int


class MovieUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        max_length=255,
    )
    date: Date | None = None
    score: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    overview: str | None = None
    status: MovieStatusEnum | None = None
    budget: float | None = Field(
        default=None,
        ge=0,
    )
    revenue: float | None = Field(
        default=None,
        ge=0,
    )

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: Date | None):
        if value is None:
            return value

        max_date = Date.today() + timedelta(days=365)

        if value > max_date:
            raise ValueError(
                "Release date cannot be more than one year in the future."
            )

        return value
