# Kenya Job Platform

A public Kenyan job board with a personal application tracker and a documented REST API.

- **Job seekers** search verified vacancies, save jobs, track every application through
  Applied, Assessment, Interview, Offer and Rejected, keep private notes and follow-up dates,
  and receive email alerts for new matching jobs.
- **Developers** can read public job and company data through a JSON API with OpenAPI docs.

Only jobs that are **published**, **not past their deadline** and from a **verified company**
are ever public. Drafts, expired jobs and unreviewed imports stay private.

## Stack

Django 5.2 LTS, Django REST Framework, MySQL 8, Redis, JWT authentication, Docker Compose,
drf-spectacular (OpenAPI), pytest.

## Quick start (Linux)

Requirements: Docker with the Compose plugin.

```bash
cp .env.example .env            # then fill in SECRET_KEY and the DB passwords
make build
make migrations                 # first time only
make up
make superuser
```

- API docs: http://localhost:8000/api/docs/
- Health check: http://localhost:8000/api/v1/health/
- Admin (add companies and jobs here): http://localhost:8000/admin/

Add a **Company**, add a **Job**, then use the **Publish selected jobs** action. The job now
appears at `/api/v1/jobs/`.

## Everyday commands

Run `make` to list them all. The most useful:

| Command | What it does |
|---|---|
| `make up` / `make down` | Start / stop the stack |
| `make logs` | Follow the web logs |
| `make test` | Run the test suite |
| `make migrations` / `make migrate` | Create / apply migrations |
| `make expire` | Close jobs whose deadline has passed |
| `make alerts` | Send due job alert emails |

## API at a glance

All endpoints live under `/api/v1/`. Browsing jobs and companies needs no account;
personal features need a Bearer token from `/auth/login/`.

| Area | Endpoints |
|---|---|
| Public data | `GET jobs/`, `GET jobs/{id}/`, `GET companies/`, `GET companies/{slug}/`, `GET skills/`, `GET meta/` |
| Auth | `POST auth/register/`, `POST auth/login/`, `POST auth/token/refresh/`, `POST auth/logout/` |
| Account | `GET/PATCH auth/me/`, `GET/PATCH auth/profile/`, `GET/DELETE auth/profile/cv/`, `POST auth/password/change/` |
| Tracker | `saved-jobs/`, `applications/`, `applications/summary/`, `applications/{id}/notes/` |
| Alerts | `alerts/` (create, list, update, delete) |
| System | `GET health/` |

Copy-paste examples are in [docs/api-examples.md](docs/api-examples.md).

## Project layout

```
backend/    Django project: config/ and apps/ (accounts, companies, jobs, tracker,
            alerts, ingestion, core, web)
frontend/   HTML templates and static assets served by Django
docs/       architecture, API examples, deployment
```

See [docs/architecture.md](docs/architecture.md) for the design decisions.

## Scheduled tasks

Two commands need a scheduler (cron) in production; see [docs/deployment.md](docs/deployment.md):

- `expire_jobs` closes jobs past their deadline.
- `send_alerts` emails users about new matching jobs.

Job alerts only work once `send_alerts` is scheduled and email is configured.

## External job sources

`python manage.py import_jobs` imports from providers such as Adzuna. Imported jobs and
their companies are saved as pending and never appear publicly until an admin reviews and
publishes them. Check each provider's country coverage and terms of use before relying on it.

## Tests

```bash
make test
```