# Job Tracker — DevOps Lab

A Python CRUD API built to practise container networking, database persistence, caching and failure recovery on AWS EC2.

## Stack

- **FastAPI + Uvicorn:** API endpoints, request validation and HTTP serving.
- **PostgreSQL:** persistent storage for job applications.
- **Redis:** application-list cache with a 30-second expiry.
- **Nginx:** reverse proxy forwarding requests to the API.
- **Docker Compose:** builds and runs the services together.

Requests enter through Nginx on port `8080`. FastAPI reads from Redis when cached, otherwise queries PostgreSQL.

## Project structure

```text
app/
  main.py
  requirements.txt
nginx/
  default.conf
Dockerfile
compose.yaml
.env.example
.gitignore
```

## Run

Requires Docker Engine and Docker Compose.

```bash
cp .env.example .env
# Edit .env and set the database credentials.
sudo docker compose up -d --build
curl http://127.0.0.1:8080/health
```

Ports are bound to localhost. Run these requests on the Docker host.

For an existing database volume, use its current credentials. Changing `.env` does not change the stored PostgreSQL password.

## Database setup

Open a PostgreSQL session using the username and database configured in `.env`:

```bash
sudo docker compose exec db psql -U jobtracker -d jobtracker
```

Create the table:

```sql
CREATE TABLE IF NOT EXISTS applications (

Paste this into **`README.md`** in your project root:

````markdown
# Job Tracker — DevOps Lab

A Python CRUD API running on AWS EC2 with PostgreSQL, Redis and Nginx, managed through Docker Compose.

## Request flow

Client → Nginx → Uvicorn/FastAPI → Redis or PostgreSQL

- **FastAPI:** endpoints and request validation using Pydantic.
- **Uvicorn:** serves the Python application over HTTP.
- **PostgreSQL:** stores job applications in a persistent Docker volume.
- **Redis:** caches application lists for 30 seconds.
- **Nginx:** reverse proxy forwarding requests to the API.

## Run

Requires Docker Engine and Docker Compose v2.

```bash
cp .env.example .env
# Edit .env and set your database credentials
sudo docker compose up -d --build
```

For a fresh database, create the application table:

```bash
sudo docker compose exec db psql -U jobtracker -d jobtracker
```

```sql
CREATE TABLE IF NOT EXISTS applications (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'applied',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Enter `\q` to exit. Table creation is currently manual.

## API

Run these requests on the EC2 host. Nginx is bound to localhost port 8080.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Check API availability |
| GET | `/db-check` | Verify database connectivity |
| POST | `/applications` | Create an application |
| GET | `/applications` | List applications |
| PATCH | `/applications/{id}` | Update application status |
| DELETE | `/applications/{id}` | Delete an application |

```bash
# Create
curl -i -X POST http://127.0.0.1:8080/applications \
  -H "Content-Type: application/json" \
  -d '{"company":"Example Ltd","role":"DevOps Engineer"}'

# List
curl http://127.0.0.1:8080/applications

# Update — replace 1 with the returned ID
curl -i -X PATCH http://127.0.0.1:8080/applications/1 \
  -H "Content-Type: application/json" \
  -d '{"status":"interview"}'

# Delete
curl -i -X DELETE http://127.0.0.1:8080/applications/1
```

Responses include 201 for creation, 200 for reads/updates, 204 for deletion, 404 for missing records and 422 for invalid input.

## Cache behaviour

- Key: `applications:list`; value: application records serialized as JSON.
- Cache miss: read PostgreSQL and cache the result for 30 seconds.
- Cache hit: return the cached list.
- Successful writes delete the key.
- Redis failure falls back to PostgreSQL.
- List responses identify their source as `database` or `cache`.

## Verified

- Create, list, update and delete operations.
- Database persistence after container removal and recreation.
- Cache hits and invalidation.
- Requests through Nginx.
- Continued reads during a Redis outage and caching after recovery.

## Operations

```bash
sudo docker compose ps -a
sudo docker compose logs --tail=50 api nginx
sudo docker compose down
```

`down` preserves database data. **`down -v` deletes the database volume.**

## Scope

Learning lab; authentication, HTTPS, automated schema migrations and backups are not yet implemented. `/health` checks the API only.

Keep `.env` and private keys out of Git. The database volume resides on the EC2 disk and is not a backup.