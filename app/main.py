from fastapi import FastAPI
import psycopg
import os
from pydantic import BaseModel, Field
from psycopg.rows import dict_row
from fastapi import HTTPException, Response
import json
import redis
from fastapi.encoders import jsonable_encoder

app = FastAPI(title="Job Application Tracker")

cache = redis.Redis.from_url(
    os.environ["REDIS_URL"],
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)

CACHE_KEY = "applications:list"


def invalidate_cache():
    try:
        cache.delete(CACHE_KEY)
    except redis.exceptions.RedisError:
        pass
    
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def home():
    return {"message": "Job Application Tracker is running"}


@app.get("/db-check")
def db_check():
    with psycopg.connect(os.environ.get("DATABASE_URL"), connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user")
            database, user = cur.fetchone()
    return {"db_status": "ok", "database": database, "user": user}

class ApplicationCreate(BaseModel):
    company: str = Field(min_length=1)
    role: str = Field(min_length=1)
    status: str = Field(default="applied", min_length=1)


@app.post("/applications", status_code=201)
def create_application(application: ApplicationCreate):
    with psycopg.connect(
        os.environ["DATABASE_URL"],
        connect_timeout=5,
        row_factory=dict_row,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO applications (company, role, status)
                VALUES (%s, %s, %s)
                RETURNING id, company, role, status, created_at
                """,
                (application.company, application.role, application.status),
            )
            result = cursor.fetchone()

    invalidate_cache()
    return result


@app.get("/applications")
def list_applications():
    try:
        cached = cache.get(CACHE_KEY)
    except redis.exceptions.RedisError:
        cached = None

    if cached is not None:
        return {"source": "cache", "applications": json.loads(cached)}

    with psycopg.connect(
        os.environ["DATABASE_URL"],
        connect_timeout=5,
        row_factory=dict_row,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, company, role, status, created_at
                FROM applications
                ORDER BY id
                """
            )
            results = cursor.fetchall()

    applications = jsonable_encoder(results)

    try:
        cache.setex(CACHE_KEY, 30, json.dumps(applications))
    except redis.exceptions.RedisError:
        pass

    return {"source": "database", "applications": applications}


class ApplicationStatusUpdate(BaseModel):
    status: str = Field(min_length=1)


@app.patch("/applications/{application_id}")
def update_application(
    application_id: int,
    application: ApplicationStatusUpdate,
):
    with psycopg.connect(
        os.environ["DATABASE_URL"],
        connect_timeout=5,
        row_factory=dict_row,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE applications
                SET status = %s
                WHERE id = %s
                RETURNING id, company, role, status, created_at
                """,
                (application.status, application_id),
            )
            result = cursor.fetchone()

            if result is None:
                raise HTTPException(
                    status_code=404,
                    detail="Application not found",
                )

    invalidate_cache()
    return result


@app.delete("/applications/{application_id}", status_code=204)
def delete_application(application_id: int):
    with psycopg.connect(
        os.environ["DATABASE_URL"],
        connect_timeout=5,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM applications WHERE id = %s RETURNING id",
                (application_id,),
            )

            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Application not found",
                )
    invalidate_cache()
    return Response(status_code=204)