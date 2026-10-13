# Deployment

These notes describe a single Linux server (a VPS) running Docker. The stack is defined in
`docker-compose.prod.yml`. Hosting platforms differ: if you use a managed host, check its
current free-tier limits (some free web services sleep when idle and some free databases
expire) before relying on it for real user data.

## 1. Prepare the server

- Install Docker with the Compose plugin.
- Point your domain's DNS A record at the server.
- Install a reverse proxy that provides HTTPS. Caddy is the simplest because it obtains
  certificates automatically.

## 2. Get the code and configure

```bash
git clone <your-repo-url> kenya-job-platform && cd kenya-job-platform
cp .env.example .env
```

Edit `.env` with production values:

```env
SECRET_KEY=<a new long random value>
ALLOWED_HOSTS=jobs.example.com
SITE_URL=https://jobs.example.com
CSRF_TRUSTED_ORIGINS=https://jobs.example.com
DB_NAME=jobplatform
DB_USER=jobuser
DB_PASSWORD=<strong password>
DB_ROOT_PASSWORD=<different strong password>
EMAIL_HOST=smtp.example.com
EMAIL_HOST_USER=<smtp user>
EMAIL_HOST_PASSWORD=<smtp password>
```

Generate secrets with `openssl rand -hex 24`. Never commit `.env`.
To test over plain HTTP before HTTPS is ready, add `SECURE_SSL_REDIRECT=False`, then remove it.

## 3. Start

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f web
```

The first start runs migrations and collects static files automatically. If this is a brand
new project, create the migration files in development first (`make migrations`) and commit
them, so production applies the same migrations.

Create the admin account:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

## 4. HTTPS with Caddy

`/etc/caddy/Caddyfile`:

```
jobs.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

Caddy forwards the `X-Forwarded-Proto` header, which the production settings rely on to
recognise secure requests.

## 5. Schedule maintenance (cron)

`crontab -e`:

```
0 6 * * *  cd /opt/kenya-job-platform && docker compose -f docker-compose.prod.yml exec -T web python manage.py expire_jobs
0 7 * * *  cd /opt/kenya-job-platform && docker compose -f docker-compose.prod.yml exec -T web python manage.py send_alerts --frequency daily
0 7 * * 1  cd /opt/kenya-job-platform && docker compose -f docker-compose.prod.yml exec -T web python manage.py send_alerts --frequency weekly
```

Adjust the path to where you cloned the project. Job alerts only work once email is
configured and `send_alerts` is scheduled.

## 6. Backups

```bash
docker compose -f docker-compose.prod.yml exec -T db \
  sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction "$MYSQL_DATABASE"' \
  > backup-$(date +%F).sql
```

CV files live in the `private_media` Docker volume; back it up too. Keep backups off the
server.

## 7. Update to a new version

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

## 8. Launch checklist

- [ ] `https://your-domain/api/v1/health/` returns `"status":"ok"`
- [ ] `https://your-domain/api/docs/` loads
- [ ] A verified company and a published job appear in `/api/v1/jobs/`
- [ ] Register, login, save a job and track an application from another device
- [ ] A test alert email arrives after running `send_alerts`
- [ ] `.env` is not in Git, and the database and Redis are not exposed publicly
- [ ] Backups run and a restore has been tested
- [ ] An uptime monitor watches `/api/v1/health/`

## Notes

- The web container runs as root so that the named volumes are writable without extra
  setup. Hardening it with a non-root user is a sensible later step.
- Only list real, verified jobs. Do not claim real-time coverage or automatic alerts until
  the scheduler and email are working.