# Architecture

## Overview

```
Browser / API client
        |  HTTPS
        v
Reverse proxy (Caddy or nginx)
        |
        v
Django + Django REST Framework (gunicorn) ----> Redis (cache, rate limits)
        |
        v
      MySQL
```

The website and third-party developers use the **same API**. The HTML pages are shells that
fetch data from `/api/v1/` with JavaScript, so the API is always exercised by the product
itself.

## Backend apps

| App | Responsibility |
|---|---|
| `accounts` | Custom user (job seeker or employer), profile, private CV, JWT auth |
| `companies` | Employers and their verification status |
| `jobs` | Listings, skills, sources, search, filters, pagination, expiry |
| `tracker` | Saved jobs, applications, notes. Always scoped to the logged-in user |
| `alerts` | Saved searches and the email sender |
| `ingestion` | Pluggable external job sources and the importer |
| `core` | Shared base model, utilities, cache helpers, throttling, health check |
| `web` | Views that render the HTML pages |

## Data model

```
User 1--1 Profile
User 1--* SavedJob *--1 Job
User 1--* Application *--1 Job
Application 1--* ApplicationNote
User 1--* JobAlert
Company 1--* Job *--* Skill
Job 1--* JobSource
```

## Key decisions

1. **One definition of "public".** `Job.objects.public()` returns jobs that are published,
   not past their deadline and belong to a verified company. Every public endpoint uses it,
   so a draft or expired job cannot leak.
2. **Custom user from day one.** Changing the user model after the first migration is painful.
3. **Counties are a fixed list** of the 47 Kenyan counties stored as slugs, which prevents
   typos and makes filtering exact.
4. **Duplicate detection** uses a fingerprint of company, normalised title and county.
   Admin validation and the importer both use it.
5. **Imports are never auto-published.** Imported jobs are `pending_review` and their
   companies `pending`, so an admin reviews them first.
6. **Caching by version number.** Public list responses are cached in Redis. Saving a job,
   company or skill bumps a namespace version, so old entries are never read again. If Redis
   is down the API still works, uncached.
7. **Private CVs.** Files live outside any public folder and are only downloadable by their
   owner through an authenticated endpoint.
8. **Tokens.** Short-lived access tokens, rotating refresh tokens, and logout blacklists the
   refresh token.
9. **Rate limiting.** Anonymous and user limits everywhere, and a strict limit on
   register/login.
10. **Scheduled work is plain management commands**, so any scheduler (cron, a hosting
    platform's scheduler) can run them.

## Request example

`GET /api/v1/jobs/?search=python&county=nairobi`

1. Throttling checks the caller's rate.
2. The cache is checked using a key built from the namespace version and the full URL.
3. On a miss, `JobFilter` and the search filter run over `Job.objects.public()`.
4. The paginated result is cached for `JOB_LIST_CACHE_SECONDS` and returned.

## Testing

pytest with `config.settings.test` (in-memory cache, fast password hasher, throwaway CV
folder). Each app has tests, and `backend/tests/integration/` covers the whole job-seeker
flow.