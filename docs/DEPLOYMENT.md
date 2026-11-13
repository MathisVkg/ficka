# Portainer and image deployment

## Two separate Compose files

| File                 | Purpose                                | Source build  | Published ports                       |
| -------------------- | -------------------------------------- | ------------- | ------------------------------------- |
| `compose.yaml`       | Local development/build verification   | API and web   | Web on 127.0.0.1                      |
| `compose.dev.yaml`   | Overlay for native API/web development | Start only db | DB on 127.0.0.1                       |
| `docker-compose.yml` | Portainer Git stack / Linux homelab    | None          | Web on all host interfaces by default |

Use `docker-compose.yml` with Portainer **Docker Standalone** on a Linux amd64 host. This configuration uses Compose health dependencies, not Swarm scheduling. Images are currently published for linux/amd64; do not deploy these tags to an ARM host. No required bind mounts or host source checkout is used at runtime.

## Publishing images with GitHub Actions

Pushes to `main` start **Publish images**. Its first job calls the reusable **Foundation checks** workflow: frontend lint, types, formatting and browser tests; API tests and PostgreSQL 17 migrations/readiness; development and production Compose validation and startup. Only after all check jobs succeed do image jobs run. PRs run checks without registry write permission. Manual dispatch is supported; image publication is restricted to the main ref.

The publication jobs use Docker Buildx and service-scoped GitHub Actions layer caches. Only these jobs receive `packages: write`, alongside `contents: read`. They log in with the built-in `GITHUB_TOKEN`; no publishing PAT or external service is required. The Linux amd64 images carry source/revision OCI labels and the following tags:

- `ghcr.io/mathisvkg/ficka-api:main` and `ghcr.io/mathisvkg/ficka-web:main`.
- `ghcr.io/mathisvkg/ficka-api:sha-<full-commit-sha>` and the matching web tag.

Enable Actions in repository settings and allow the workflow's declared package permission under your account/organization policy. If either package already exists, grant this repository Actions write access in its package settings. Both matrix jobs must finish successfully before deploying a matching pair. A registry/network failure during publishing can leave only one image updated; wait for the complete workflow and rerun failed jobs before deployment.

After the first successful push, open the account's Packages page and each package's settings. Make both packages **public** for anonymous pulls, or leave them private and add a `ghcr.io` registry in Portainer using your GitHub username and a classic PAT with `read:packages` plus access to the packages. Select that registry for the stack. Repository visibility alone does not establish package visibility. See [GitHub's GHCR guidance](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).

## Portainer Git stack setup

Wait for the main **Publish images** run to be green and verify that both packages exist. Then in Portainer's Docker Standalone environment choose **Stacks → Add stack → Repository**:

| Field                | Value                                         |
| -------------------- | --------------------------------------------- |
| Stack name           | `ficka`, or preserve your existing stack name |
| Repository URL       | `https://github.com/MathisVkg/ficka`          |
| Repository reference | `refs/heads/main`                             |
| Compose path         | **`docker-compose.yml`**                      |

Add stack environment variables below. You do not need a tracked `.env`, `stack.env`, a database URL or host paths. Portainer substitutes the values explicitly referenced in the Compose file; see [Portainer Git stack documentation](https://docs.portainer.io/user/docker/stacks/add).

| Variable            | Required | Value / default                                            |
| ------------------- | -------- | ---------------------------------------------------------- |
| `POSTGRES_USER`     | Yes      | Your Ficka database role                                   |
| `POSTGRES_PASSWORD` | Yes      | A strong unique password; preserve existing DB credentials |
| `POSTGRES_DB`       | Yes      | Your database name                                         |
| `WEB_PORT`          | No       | `3000` on the Docker host                                  |
| `WEB_BIND_ADDRESS`  | No       | `0.0.0.0`; set a specific host LAN IP if desired           |
| `FICKA_WEB_IMAGE`   | No       | `ghcr.io/mathisvkg/ficka-web:main`                         |
| `FICKA_API_IMAGE`   | No       | `ghcr.io/mathisvkg/ficka-api:main`                         |
| `CORS_ORIGINS`      | No       | `[]`; normal remote web access needs no CORS changes       |

Deploy the stack with image pulling enabled. The database must become healthy before API startup; API runs migrations before becoming ready; web waits for API readiness. Only web has a host port. API talks to `db:5432`; web talks to `http://api:8000` on internal Docker networking. Passwords are passed as separate fields and safely assembled by SQLAlchemy.

## LAN access and connection verification

Open `http://<docker-host-LAN-IP>:3000` (or your selected WEB_PORT) from another device. Allow that web port through the host firewall for your trusted LAN. Do not publish 5432 or 8000. This foundation has no authentication; keep it on a trusted LAN/private network.

The browser requests `/api/health/ready` on the same host it used for the page. Next.js makes the internal request to API. Neither browser localhost nor the internal Docker hostname is used as a browser backend destination. There is no browser-side API hostname to rebuild.

From another Windows device:

```powershell
Invoke-RestMethod http://<docker-host-LAN-IP>:3000/api/health/ready
# Expected: status = ready
```

All six routes should load and the dashboard should show **All systems connected**. On the host, inspect `docker compose -f docker-compose.yml ps` and service logs. Browser access via the host's LAN address can be checked locally; a second-device test also verifies firewall/routing and must be performed on your LAN.

## Updates, fixed versions and rollback

Default `main` tags follow the latest successful main build. After a green workflow, update/redeploy the Git stack and re-pull images; `pull_policy: always` requests fresh application images at deployment. An already running container does not change just because its registry tag changes.

Git polling can notice a source commit **before** image publication finishes. Do not depend on an immediate Git poll to deploy that commit's image: wait for publishing, then use Portainer's re-pull/redeploy action. If you enable automatic stack updates, coordinate their trigger after publishing (for example with your existing deployment tooling) or allow a later forced re-pull. This repository does not configure a Portainer webhook or send deployment requests.

To pin a matched revision, set both full image variables to their `:sha-<full-commit-sha>` references. SHA tags identify source revisions, but registry tags can be replaced. For a truly immutable deployment, use each published image's digest: `ghcr.io/mathisvkg/ficka-web@sha256:<web-digest>` and `ghcr.io/mathisvkg/ficka-api@sha256:<api-digest>`. The full-reference environment variables support either form.

Record both image digests and take a database backup before updates. Keep the stack name and volume unchanged. Reverting application images does not undo database migrations; review compatibility before rollback. The baseline has no financial tables today, but future migrations may change rollback requirements.

## Configuration checks without real credentials

From repository root in PowerShell, use dummy values in the process environment. Do not paste a real resolved configuration into tickets because config output includes passwords.

```powershell
$env:POSTGRES_USER = "config_test"
$env:POSTGRES_PASSWORD = "dummy-config-only"
$env:POSTGRES_DB = "config_test"
docker compose -f docker-compose.yml config
docker compose -f compose.yaml config
docker compose -f compose.yaml -f compose.dev.yaml config
Remove-Item Env:POSTGRES_USER, Env:POSTGRES_PASSWORD, Env:POSTGRES_DB
```

Use a fresh shell if other image/binding variables are set. Syntax/interpolation checks need a CLI, but do not demonstrate a successful image build or running deployment. CI uses disposable test credentials and separately starts both stack modes.

## Troubleshooting

- **Portainer still builds source / http2 frame too large:** confirm its Compose path is `docker-compose.yml`, not the default local-build `compose.yaml`. The image-only path bypasses the failing BuildKit worker operation. The reported error is a build transport/worker failure; its exact Portainer/Engine/proxy cause has not been established. If local builds also fail, inspect `docker version`, `docker buildx ls`, `docker buildx inspect --bootstrap`, Docker context/DOCKER_HOST and Engine/BuildKit compatibility. Do not expose an unauthenticated Docker TCP socket as a workaround.
- **Image unknown / manifest not found:** wait for the first successful publishing run, confirm image names and full tags, and ensure both matrix jobs succeeded. A main branch alone does not create registry images.
- **Denied / unauthorized pulls:** make both packages public or fix Portainer's selected GHCR registry credentials, PAT `read:packages` access and any required organization SSO authorization.
- **No matching manifest:** published images target Linux amd64. Confirm the Docker host architecture. ARM needs a deliberate multi-platform build before deployment.
- **Old version after update:** force re-pull/redeploy after a green publishing run, or pin the two expected image digests. Git updates and image publication finish at different times.
- **API unhealthy:** inspect API/database logs, credentials and named volume. Existing PostgreSQL passwords do not change when stack variables change. API applies migrations before its server starts.
- **Web loads but connection banner appears:** check API readiness, `API_INTERNAL_URL=http://api:8000` inside web, and Docker network membership. Request the web readiness route. Do not set it to the host IP, browser localhost or a public API URL.
- **LAN page unavailable:** verify WEB_BIND_ADDRESS, host LAN IP, published WEB_PORT and firewall. Source-build Compose intentionally binds localhost; Portainer uses the LAN-ready file.

## Persistence and backups

PostgreSQL 17 stores data in the stack's `postgres_data` named volume at `/var/lib/postgresql/data`. Normal stop, redeploy and `docker compose down` preserve it. Deleting the stack's volume or running `down -v` destroys it. Keep the stack name stable and never switch PostgreSQL major versions against this volume without a planned migration.

For a backup on a CLI-managed host (Portainer users can run the same command in the db container console):

```powershell
docker compose -f docker-compose.yml exec db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/ficka-backup.dump'
docker compose -f docker-compose.yml cp db:/tmp/ficka-backup.dump ./ficka-backup.dump
docker compose -f docker-compose.yml exec db rm /tmp/ficka-backup.dump
```

When managing a Portainer stack by CLI, supply its actual project name with `-p <stack-name>` and the same stack variables. Copy the backup off the host securely, then test restoration with `pg_restore` into a separate disposable database before relying on it. Also retain protected configuration and deployment image digests. Backups may contain sensitive business data; keep them out of Git.
