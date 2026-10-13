from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from redis.exceptions import RedisError
from starlette.responses import JSONResponse

from .store import NewsStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not hasattr(app.state, "store"):
        app.state.store = NewsStore()
    yield
    app.state.store.redis.close()


app = FastAPI(title="TerraNewsphere", version="0.1.0", lifespan=lifespan)


@app.exception_handler(RedisError)
async def unavailable(request: Request, error: RedisError):
    return JSONResponse(status_code=503, content={"detail": "News storage temporarily unavailable"},
                        headers={"Cache-Control": "no-store"})


@app.middleware("http")
async def no_news_cache(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
def health(request: Request):
    request.app.state.store.redis.ping()
    return {"status": "ok"}


@app.get("/api/news/markers")
def markers(request: Request,
            country: Annotated[str | None, Query(pattern=r"^[A-Z]{2}$")] = None,
            adm1: Annotated[str | None, Query(max_length=160)] = None,
            adm2: Annotated[str | None, Query(max_length=160)] = None,
            bbox: Annotated[str | None, Query(max_length=100)] = None,
            limit: Annotated[int, Query(ge=1, le=200)] = 100,
            cursor: Annotated[int, Query(ge=0, le=1000000)] = 0):
    if (adm1 or adm2) and not country:
        raise HTTPException(422, "Administrative filters require country")
    if adm2 and not adm1:
        raise HTTPException(422, "ADM2 filter requires ADM1")
    bounds = None
    if bbox:
        try:
            west, south, east, north = map(float, bbox.split(","))
            if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= north <= 90):
                raise ValueError()
            bounds = (west, south, east, north)
        except ValueError:
            raise HTTPException(422, "bbox must be west,south,east,north") from None
    articles, next_cursor = request.app.state.store.list(country, adm1, adm2, bounds, limit, cursor)
    return {"items": [{"news_id": article.news_id, "title": article.content.title,
                       "language": article.content.language,
                       "translations": {lang: {"title": text.title} for lang, text in
                                        article.content.translations.items()},
                       "thumbnail_url": article.content.thumbnail_url,
                       "publisher": article.source.publisher, "locations": article.locations,
                       "published_at": article.published_at, "expires_at": article.expires_at,
                       "is_demo": article.is_demo} for article in articles],
            "next_cursor": next_cursor}


@app.get("/api/news/{news_id}")
def preview(news_id: str, request: Request):
    if len(news_id) != 64 or any(char not in "0123456789abcdef" for char in news_id):
        raise HTTPException(404, "News not found")
    article = request.app.state.store.get(news_id)
    if article is None:
        raise HTTPException(404, "News not found")
    return article
