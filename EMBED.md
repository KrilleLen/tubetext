# Lägg TubeText på din hemsida

Appen måste först ligga på en publik HTTPS-adress, till exempel `https://text.dindoman.se`.
Sätt sedan miljövariabeln:

```env
EMBED_ALLOWED_ORIGINS=https://www.dindoman.se,https://dindoman.se
```

Ange bara domäner du själv vill tillåta. Starta om appen efter ändringen.

## Rekommenderat: webbkomponent

Klistra in detta där appen ska visas:

```html
<script src="https://text.dindoman.se/static/widget.js" defer></script>
<tubetext-widget></tubetext-widget>
```

Widgeten anpassar höjden automatiskt. Du kan även förinställa en video:

```html
<tubetext-widget
  video-url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  radius="12px"
  height="760px">
</tubetext-widget>
```

## Alternativ: vanlig iframe

```html
<iframe
  src="https://text.dindoman.se/embed"
  title="YouTube-transkribering"
  width="100%"
  height="850"
  style="border:0;border-radius:18px"
  allow="clipboard-write; fullscreen"
  loading="lazy">
</iframe>
```

För en förvald video:

```html
<iframe src="https://text.dindoman.se/embed?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DdQw4w9WgXcQ"></iframe>
```

## WordPress

Lägg koden i ett block av typen **Anpassad HTML**. WordPress kan ibland flytta `<script>`-taggar beroende på behörighet och säkerhetsplugin. Då kan script-taggen läggas globalt i sidhuvudet och endast `<tubetext-widget>` placeras i sidans innehåll.

## Om inbäddningen blockeras

Kontrollera att webbplatsens exakta origin finns i `EMBED_ALLOWED_ORIGINS`. Origin består av protokoll och domän, exempelvis `https://www.dindoman.se`, utan sökväg eller avslutande snedstreck.
