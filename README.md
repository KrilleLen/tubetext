# TubeText

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2FKrilleLen%2Ftubetext)

En produktionstät, mobilvänlig webbapp som hämtar offentlig YouTube-textning och gör den lätt att söka, kopiera, exportera och bädda in på en annan hemsida.

## Funktioner

- Vanliga YouTube-, Shorts-, Live-, Embed- och `youtu.be`-länkar.
- Prioriterar manuellt skapad textning framför automatisk textning.
- Svenska/engelska som standard, med byte mellan alla tillgängliga språk.
- Klickbara tidsstämplar som startar videon på rätt ställe.
- Sökning och markering inne i transkriptionen.
- Export till TXT, SRT och VTT.
- Lokal historik i webbläsaren, utan användarkonto.
- Inbäddningsbar widget och kompakt `/embed`-vy.
- Cache, rate limiting, CORS, CSP och validerade YouTube-adresser.
- Docker, Render Blueprint, Railway-konfiguration och GitHub Actions.
- Automatisk publicering av Docker-image till GitHub Container Registry.

## Kör lokalt

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Öppna `http://localhost:8000`.

## Kör med Docker

```bash
cp .env.example .env
docker compose up --build
```

## Produktionsinställningar

Sätt minst följande värden på servern:

```env
ENVIRONMENT=production
DOCS_ENABLED=false
ALLOWED_ORIGINS=https://www.din-hemsida.se
EMBED_ALLOWED_ORIGINS=https://www.din-hemsida.se
```

Separera flera domäner med kommatecken. Använd inte `*` för inbäddning om appen bara ska finnas på din egen webbplats.

## Driftsätt från GitHub

### Render

Repo:t innehåller `render.yaml`. Skapa en Render Blueprint från GitHub-repot och fyll i de miljövariabler som markeras som manuella. Render bygger Dockerfilen och använder `/api/health` som hälsokontroll.

### Railway

Repo:t innehåller `railway.json` och en Dockerfile i roten. Skapa ett projekt från GitHub-repot, lägg in miljövariablerna och generera en publik domän.

### Egen Docker-server

```bash
docker build -t tubetext .
docker run -d \
  --name tubetext \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env \
  tubetext
```

Lägg normalt Nginx, Caddy eller en annan reverse proxy framför containern för HTTPS och egen subdomän.

## Lägg appen på din hemsida

När appen är driftsatt på exempelvis `https://text.dindoman.se`:

```html
<script src="https://text.dindoman.se/static/widget.js" defer></script>
<tubetext-widget></tubetext-widget>
```

Full guide finns i [EMBED.md](EMBED.md).

## GitHub Actions

- `CI`: installerar beroenden, kör Ruff och alla tester vid push och pull request.
- `Publish Docker image`: bygger och publicerar `ghcr.io/ÄGARE/REPO:latest` från `main` och versions-taggar.
- Dependabot kontrollerar Python-paket och Actions varje vecka.

## API

### `POST /api/transcripts`

```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "preferred_languages": ["sv", "en"],
  "language_code": null,
  "translate_to": null
}
```

### Hälsokontroll

```text
GET /api/health
GET /healthz
```

## Viktigt om YouTube-blockering

`youtube-transcript-api` använder YouTubes publika webbgränssnitt, inte ett officiellt API som ger fri åtkomst till textningen på valfria videor. Det kan fungera lokalt men publika datacenter-IP-adresser kan få `RequestBlocked`, `IpBlocked` eller 429.

För stabil publik drift behövs ofta:

1. En roterande residential proxy som du har rätt att använda.
2. `YOUTUBE_PROXY_URL` i servermiljön.
3. Cache och rimlig rate limiting, vilket redan finns i projektet.

För större trafik bör lokal cache och rate limiting flyttas till Redis.

## Testa

```bash
pip install -r requirements-dev.txt
ruff check .
pytest
```

## Juridik

Verktyget ska användas för material du har rätt att behandla. Lagra eller återpublicera inte upphovsrättsskyddad text i strid med rättighetsinnehavarens eller plattformens villkor. Kontrollera YouTubes villkor innan kommersiell lansering.

## Licens

MIT
