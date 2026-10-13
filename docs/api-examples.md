# API examples

```bash
BASE=http://localhost:8000/api/v1
```

Interactive documentation: http://localhost:8000/api/docs/

## Health and reference data

```bash
curl $BASE/health/
curl $BASE/meta/          # counties, job types, work modes, experience levels
curl "$BASE/skills/?search=py"
```

## Register and log in

```bash
curl -X POST $BASE/auth/register/ -H "Content-Type: application/json" -d '{
  "username": "njeri",
  "email": "njeri@example.com",
  "password": "Zebra-Mango-47!x",
  "password_confirm": "Zebra-Mango-47!x",
  "role": "job_seeker"
}'

# The "username" field accepts a username or an email address.
curl -X POST $BASE/auth/login/ -H "Content-Type: application/json" \
  -d '{"username": "njeri", "password": "Zebra-Mango-47!x"}'
```

Save the tokens (`jq` is optional: `sudo apt install jq`):

```bash
RESPONSE=$(curl -s -X POST $BASE/auth/login/ -H "Content-Type: application/json" \
  -d '{"username": "njeri", "password": "Zebra-Mango-47!x"}')
TOKEN=$(echo "$RESPONSE" | jq -r .access)
REFRESH=$(echo "$RESPONSE" | jq -r .refresh)
```

Refresh the access token (the old refresh token stops working because tokens rotate):

```bash
curl -X POST $BASE/auth/token/refresh/ -H "Content-Type: application/json" \
  -d "{\"refresh\": \"$REFRESH\"}"
```

Log out:

```bash
curl -X POST $BASE/auth/logout/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d "{\"refresh\": \"$REFRESH\"}"
```

## Search jobs (no login needed)

```bash
curl "$BASE/jobs/?search=python"
curl "$BASE/jobs/?county=nairobi&county=kiambu&job_type=internship"
curl "$BASE/jobs/?work_mode=remote&experience_level=entry"
curl "$BASE/jobs/?min_salary=50000&has_salary=true"
curl "$BASE/jobs/?skills=python,django&posted_within=7"
curl "$BASE/jobs/?company=acme-kenya-ltd&deadline_before=2026-12-31"
curl "$BASE/jobs/?ordering=-published_at&page_size=10&page=2"
curl $BASE/jobs/1/
```

## Companies

```bash
curl "$BASE/companies/?county=nairobi&search=tech"
curl $BASE/companies/acme-kenya-ltd/
```

## Account, profile and CV

```bash
curl -H "Authorization: Bearer $TOKEN" $BASE/auth/me/
curl -X PATCH $BASE/auth/profile/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"headline": "Backend developer", "county": "nairobi", "skills": ["Python", "Django"]}'

# Upload a CV (pdf, doc or docx, up to 5 MB)
curl -X PATCH $BASE/auth/profile/ -H "Authorization: Bearer $TOKEN" -F "cv=@/path/to/cv.pdf"
curl -H "Authorization: Bearer $TOKEN" -OJ $BASE/auth/profile/cv/
curl -X DELETE -H "Authorization: Bearer $TOKEN" $BASE/auth/profile/cv/

curl -X POST $BASE/auth/password/change/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"old_password": "Zebra-Mango-47!x", "new_password": "Another-Strong-91?y"}'
```

## Saved jobs

```bash
curl -X POST $BASE/saved-jobs/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"job_id": 1}'
curl -H "Authorization: Bearer $TOKEN" $BASE/saved-jobs/
curl -X DELETE -H "Authorization: Bearer $TOKEN" $BASE/saved-jobs/1/    # the saved-job id
```

## Applications

```bash
curl -X POST $BASE/applications/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"job_id": 1, "follow_up_date": "2026-11-01"}'

curl -X PATCH $BASE/applications/1/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"status": "interview"}'
# statuses: saved, applied, assessment, interview, offer, rejected

curl -H "Authorization: Bearer $TOKEN" "$BASE/applications/?status=interview"
curl -H "Authorization: Bearer $TOKEN" "$BASE/applications/?follow_up_date__lte=2026-11-30"
curl -H "Authorization: Bearer $TOKEN" $BASE/applications/summary/
```

Notes:

```bash
curl -X POST $BASE/applications/1/notes/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"body": "Prepare a portfolio walkthrough"}'
curl -H "Authorization: Bearer $TOKEN" $BASE/applications/1/notes/
curl -X DELETE -H "Authorization: Bearer $TOKEN" $BASE/applications/1/notes/1/
```

## Job alerts

```bash
curl -X POST $BASE/alerts/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Python in Nairobi", "query": "python", "county": "nairobi", "frequency": "daily"}'
curl -H "Authorization: Bearer $TOKEN" $BASE/alerts/
curl -X PATCH $BASE/alerts/1/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"is_active": false}'
curl -X DELETE -H "Authorization: Bearer $TOKEN" $BASE/alerts/1/
```

## Errors you may see

| Status | Meaning |
|---|---|
| 400 | Invalid input; the body lists the problem per field |
| 401 | Missing or expired token |
| 404 | Not found, or it belongs to another user |
| 429 | Rate limit reached; wait and retry |