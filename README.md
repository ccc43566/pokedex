# Pokédex

Chinese-first, bilingual Pokédex built with Nuxt 3 SSR, FastAPI, and PostgreSQL. It mirrors core PokéAPI resources into a local database and serves normal browsing without calling PokeAPI at request time.

## Stack

- Frontend: Nuxt 3, Vue 3, TypeScript, Nuxt UI, Tailwind CSS
- Backend: FastAPI, Pydantic v2, SQLAlchemy 2 async, Alembic
- Database: PostgreSQL, JSONB, pg_trgm, pgvector reservation
- Sync: HTTPX-based Python CLI and a weekly Compose scheduler
- Runtime: Docker Compose, Caddy, pnpm, uv

## Quick start

1. Copy `.env.example` to `.env` and change the password.
2. Start the database and API:

   ```powershell
   docker compose up -d db api
   ```

3. Run the initial PokeAPI mirror:

   ```powershell
   docker compose run --rm scheduler python -m pokedex_api.sync --force
   ```

   For a data-only sync, add `--skip-media`. To register and fill missing images later
   without refreshing the core data:

   ```powershell
   docker compose exec scheduler python -m pokedex_api.sync --media-only
   ```

   The historical game images can also be resumed independently. This reads the
   saved `sprites.versions` data, keeps every generation/game/type association,
   and retries only pending downloads, failed downloads, and damaged files:

   ```powershell
   docker compose exec api python -m pokedex_api.sync --versions-only
   ```

4. Start the web app and reverse proxy:

   ```powershell
   docker compose up -d web caddy scheduler
   ```

5. Open `http://localhost:8080/zh-Hans`.

## Local development

Backend:

```powershell
cd apps/api
uv sync
uv run alembic upgrade head
uv run uvicorn pokedex_api.main:app --reload
```

Frontend:

```powershell
cd apps/web
pnpm install
pnpm dev
```

Use Node.js 24 and the pnpm version in `apps/web/package.json`. Keep the existing
`http://localhost:8080` stack running, then open
`http://127.0.0.1:3000/zh-Hans/pokemon` for frontend development. The Nuxt dev
server sends browser requests for `/api/v1` and `/media` to port 8080; server-side
rendering also calls that backend. Edit Vue or CSS files and the dev page updates
without rebuilding the Docker image. Stop the dev server with `Ctrl+C`.

The dev backend defaults to `http://localhost:8080`. Set `POKEDEX_DEV_BACKEND`
before `pnpm dev` only if the backend uses a different origin. After a design
round, run `pnpm typecheck` and `pnpm build` from `apps/web`. Rebuild the Docker
web service when you are ready to update the 8080 site:

```powershell
docker compose up -d --build web
```

The historical gallery falls back to `data/version-media/{id}.json` snapshots
while the 8080 API still runs the previous Docker image. After collecting more images,
refresh those snapshots with `scripts/export_version_media.py` in the API
container and copy `/tmp/version-media` into `data/version-media`. The snapshots
are ignored by Git. Once the API image is rebuilt, both previews read
`/api/v1/pokemon/{id}/version-sprites` directly and no snapshot is needed.

## Historical sprite storage

`version_sprite` stores one row for every saved `sprites.versions` leaf, including
normal source `null` values. Each row retains the Pokémon or form, generation,
game, image kind, original URL, format, and collection status. The collector
downloads each distinct URL once, validates the original PNG/GIF/WebP bytes,
and stores a file once per SHA-256 hash in the `pokedex_media` Docker volume.
Multiple game or form rows can point to the same file without losing their
separate source identities. Existing four-category images and their files remain
in place. Statuses are `null`, `pending`, `downloaded`, `download_failed`, and
`corrupt`; a `null` field is an upstream omission and is never retried.

To inspect final counts and actual volume bytes, run
`scripts/report_version_sprites.py` with the API container's Python and database
environment. Use `docker compose down` without `-v` when stopping the stack so
the database and media volumes remain available.

## Data and attribution

The database is a rebuildable mirror. Raw PokeAPI payloads are retained in `source_record` for replay and auditing. The curated preview images and historical `sprites.versions` images can be mirrored into a local Docker volume. Image files and the database are not stored in this Git repository.

Pokémon names and images are trademarks/copyrights of Nintendo, Creatures Inc., and GAME FREAK inc. PokeAPI is used as the upstream data source. Review commercial redistribution rights before making the site commercial.
