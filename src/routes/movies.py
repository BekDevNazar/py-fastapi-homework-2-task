from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas.movies import MovieDetail, MovieUpdate, MovieCreate, MovieList


router = APIRouter()


@router.get("/movies/", response_model=MovieList)
async def get_movies(
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=20),
        db: AsyncSession = Depends(get_db)
):
    offset = (page - 1) * per_page

    result = await db.execute(
        select(MovieModel)
        .order_by(MovieModel.id.desc())
        .offset(offset)
        .limit(per_page)
    )
    movies = result.scalars().all()

    if not movies:
        raise HTTPException(
            status_code=404,
            detail="No movies found."
        )

    total_items = await db.scalar(
        select(func.count(MovieModel.id))
    )
    total_pages = (total_items + per_page - 1) // per_page
    prev_page = None
    if page > 1:
        prev_page = f"/theater/movies/?page={page - 1}&per_page={per_page}"

    next_page = None
    if page < total_pages:
        next_page = f"/theater/movies/?page={page + 1}&per_page={per_page}"

    return {
        "movies": movies,
        "prev_page": prev_page,
        "next_page": next_page,
        "total_pages": total_pages,
        "total_items": total_items,
    }


async def get_or_create_by_name(
    db: AsyncSession,
    model,
    name: str,
):
    result = await db.execute(
        select(model).where(
            model.name == name
        )
    )

    obj = result.scalar_one_or_none()

    if obj is None:
        obj = model(name=name)
        db.add(obj)
        await db.flush()

    return obj


async def get_or_create_country(
    db: AsyncSession,
    code: str,
):
    result = await db.execute(
        select(CountryModel).where(
            CountryModel.code == code
        )
    )

    country = result.scalar_one_or_none()

    if country is None:
        country = CountryModel(
            code=code,
            name=None,
        )
        db.add(country)
        await db.flush()

    return country


@router.post(
    "/movies/",
    response_model=MovieDetail,
    status_code=201,
)
async def create_new_movie(
    movie_data: MovieCreate,
    db: AsyncSession = Depends(get_db),
):
    existing_movie = await db.scalar(
        select(MovieModel).where(
            MovieModel.name == movie_data.name,
            MovieModel.date == movie_data.date,
        )
    )

    if existing_movie is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"A movie with the name '{movie_data.name}' "
                f"and release date '{movie_data.date}' already exists."
            ),
        )

    data = movie_data.model_dump()

    genres = data.pop("genres", [])
    actors = data.pop("actors", [])
    languages = data.pop("languages", [])
    country_code = data.pop("country")

    movie = MovieModel(**data)

    country = await get_or_create_country(
        db,
        country_code,
    )

    genre_objects = [
        await get_or_create_by_name(
            db,
            GenreModel,
            name,
        )
        for name in genres
    ]

    actor_objects = [
        await get_or_create_by_name(
            db,
            ActorModel,
            name,
        )
        for name in actors
    ]

    language_objects = [
        await get_or_create_by_name(
            db,
            LanguageModel,
            name,
        )
        for name in languages
    ]

    movie.country = country
    movie.genres = genre_objects
    movie.actors = actor_objects
    movie.languages = language_objects

    db.add(movie)

    await db.commit()
    result = await db.execute(
        select(MovieModel)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
        .where(MovieModel.id == movie.id)
    )

    return result.scalar_one()


@router.get(
    "/movies/{movie_id}/",
    response_model=MovieDetail,
)
async def get_movie_by_id(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MovieModel)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
        .where(MovieModel.id == movie_id)
    )

    movie = result.scalar_one_or_none()

    if movie is None:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    return movie


@router.delete("/movies/{movie_id}/", status_code=204)
async def del_movie_by_id(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await db.get(MovieModel, movie_id)
    if movie is None:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )
    await db.delete(movie)
    await db.commit()


@router.patch("/movies/{movie_id}/", status_code=200)
async def update_movie(
        movie_id: int,
        movie_data: MovieUpdate,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(MovieModel).where(MovieModel.id == movie_id)
    )
    movie = result.scalar_one_or_none()
    if movie is None:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    update_data = movie_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(movie, key, value)

    await db.commit()

    return {"detail": "Movie updated successfully."}
