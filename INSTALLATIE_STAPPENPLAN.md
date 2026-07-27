# Revit MCP Server + Copilot Studio

## Volledig installatie-stappenplan voor een nieuwe pc

Dit document beschrijft alle stappen om vanaf een schone Windows-pc:

1. De Revit MCP-extensie te installeren
2. De MCP-server op te starten
3. Een publieke tunnel op te zetten
4. De koppeling met Microsoft Copilot Studio te maken

**Benodigdheden vooraf:**
- Revit met pyRevit geïnstalleerd
- Windows met `winget` beschikbaar (standaard bij Windows 10/11)
- Een Microsoft-account (voor devtunnel login)
- Toegang tot Microsoft Copilot Studio met een agent waarin je tools mag toevoegen

---

## Stap 1 — pyRevit Routes activeren

1. Open Revit
2. Ga naar het pyRevit-tabblad → **Settings**
3. Ga naar **Routes** en activeer **Routes Server**
   (pyRevit luistert nu op `http://localhost:48884/`)

---

## Stap 2 — De extensie ophalen en installeren

**Optie A — via pyRevit Extensions:**
1. pyRevit-tabblad → **Extensions**
2. Zoek *"MCP Server for Revit Python Extension"* → **Install extension**
3. Kies een locatie (standaard: `%APPDATA%\Roaming\pyRevit\Extensions`)
4. Schakel de extensie in en herstart Revit indien nodig

**Optie B — handmatig** (bijvoorbeeld bij deze eigen/aangepaste versie — kopieer de hele projectmap naar de nieuwe pc, via USB-stick, netwerkschijf of `git clone`):
1. Zorg dat de mapnaam eindigt op `.extension` (bv. `revit-mcp-python.extension`)
2. In Revit: pyRevit-tabblad → **Settings**
3. Onder **Custom Extensions** → voeg het pad naar de map toe
4. Sla op en herlaad pyRevit (herstart Revit indien nodig)

Controleer de verbinding in een browser:
```
http://localhost:48884/revit_mcp/status/
```
Verwacht antwoord:
```json
{"status": "active", "health": "healthy", "revit_available": true, ...}
```

---

## Stap 3 — Python packagemanager `uv` installeren

```powershell
winget install astral-sh.uv
```

Sluit de terminal en open een **nieuwe** terminal (nodig zodat de PATH ververst wordt). Controleer:
```powershell
uv --version
```

---

## Stap 4 — devtunnel CLI installeren

```powershell
winget install Microsoft.devtunnel
```

Sluit de terminal en open een **nieuwe** terminal. Controleer:
```powershell
devtunnel --version
```

Log eenmalig in met je Microsoft-account:
```powershell
devtunnel user login
```
Dit toont een link (`https://login.microsoft.com/device`) en een code. Open de link in een browser, voer de code in en log in.

---

## Stap 5 — Een vaste (persistente) tunnel aanmaken — eenmalig

Kies een eigen unieke naam (voorbeeld hier: `revit-mcp`). Bestaat de naam al op jouw account, kies dan een andere.

```powershell
devtunnel create revit-mcp -a
devtunnel port create revit-mcp -p 8000
```

- `create revit-mcp -a` maakt een tunnel met vaste naam `revit-mcp` en staat anonieme toegang toe (`-a`), nodig zodat Copilot Studio er zonder Microsoft-login bij kan. De beveiliging loopt via de API-key, niet via de tunnel-login.
- `port create ... -p 8000` koppelt poort 8000 (waar de MCP-server op draait) aan deze tunnel.

Dit is **eenmalig** per pc/account — na deze stap hoef je nooit meer een nieuwe tunnel aan te maken.

---

## Stap 6 — Project ophalen (indien nog niet aanwezig)

```powershell
git clone <url-van-de-repo> revit-mcp-python.extension
```

(Of kopieer de bestaande map handmatig over, bv. via netwerkschijf of USB-stick.)

---

## Stap 7 — De MCP-server starten

```powershell
cd "<pad-naar-de-map>\revit-mcp-python.extension"
uv run --with "mcp[cli]" main.py --combined
```

Laat dit venster open staan. Bij opstarten print de server:
```
Starting combined SSE + streamable-http server on http://127.0.0.1:8000 (endpoint: /mcp)...
API key required on every request (header 'X-API-Key'): <lange-sleutel>
```

Onthoud/kopieer deze API-key — ook automatisch opgeslagen in `.revit_mcp_api_key` in de projectmap (per installatie/pc uniek, wordt aangemaakt bij eerste start).

> **Poort al in gebruik? (`Errno 10048`)**
> ```powershell
> netstat -ano | findstr :8000
> taskkill /F /PID <pid>
> ```

---

## Stap 8 — De tunnel starten

Open een **tweede, aparte** terminal:
```powershell
devtunnel host revit-mcp
```
(gebruik de naam uit Stap 5)

De output toont twee URL's per poort:
- **Connect via browser** — de échte publieke URL voor Copilot Studio, bv. `https://revit-mcp-8000.euw.devtunnels.ms`
- **Inspect network activity** — **geen** API-endpoint, maar een debug-scherm voor live verkeer. Gebruik deze nooit als server-URL.

Dankzij de vaste tunnel-naam uit Stap 5 blijft deze URL voortaan altijd hetzelfde, ook na een herstart.

---

## Stap 9 — Koppelen in Microsoft Copilot Studio

1. Ga naar [copilotstudio.microsoft.com](https://copilotstudio.microsoft.com) en open de gewenste agent
2. Tabblad **Tools** → **Hulpmiddel toevoegen**
3. Kies (of maak) de **Model Context Protocol**-tool, bv. genaamd "Revit Connector"
4. Bij **Verbinding** → chevron (▾) → **Nieuwe verbinding maken**
5. Vul de API-key in (Stap 7) → **Maken**
6. Vul/controleer onder **Bijkomende details** de Server URL (**met trailing slash!**):
   ```
   https://<jouw-tunnel-naam>-8000.<regio>.devtunnels.ms/mcp/
   ```
   > **Belangrijk:** de trailing slash `/mcp/` is verplicht. Zonder slash geeft de server een `307`-redirect terug die Copilot Studio niet volgt bij POST-requests — de koppeling loopt dan vast zonder duidelijke foutmelding.
7. Klik op het vernieuw-icoon (↻) naast "Naam van hulpmiddel" om de tool-lijst op te halen. Bij succes zie je tools als `get_revit_status`, `list_levels`, `place_family`, etc.
8. Vink de gewenste tools aan en sla op.

Test met: *"Wat is de status van de Revit-verbinding?"*

---

## Stap 10 — Foutmeldingen en oplossingen

| Symptoom | Oorzaak | Oplossing |
|---|---|---|
| `401 Unauthorized` | Geen/verkeerde `X-API-Key` | Vergelijk met `.revit_mcp_api_key` |
| `404 Not Found` (JSON, via de server) | Verkeerd pad | Server-URL moet eindigen op `/mcp/` |
| Platte tekst `"Not Found"` (9 bytes, geen `Server: uvicorn`-header) | Verzoek komt niet bij `main.py` aan | Check of je de juiste (niet `-inspect`) tunnel-URL gebruikt en of `devtunnel host` draait |
| `307 Temporary Redirect` (in het `main.py`-venster) | Server-URL mist trailing slash | Voeg toe: `/mcp/` |
| `[Errno 10048]` bij opstarten | Poort 8000 al in gebruik | Zie Stap 7 |
| Tools verdwijnen / agent reageert niet meer | `main.py`- of `devtunnel host`-venster gesloten, of pc in slaapstand | Beide opnieuw starten (Stap 7 en 8) — URL blijft gelijk dankzij Stap 5 |

**Live verkeer bekijken:** open de *inspect*-URL uit Stap 8 in je browser terwijl je in Copilot Studio iets test — je ziet het binnenkomende verzoek inclusief pad, headers en response.

---

## Dagelijks gebruik — kort overzicht

Na de eenmalige installatie (Stap 1 t/m 6) is elke volgende keer starten simpel:

```powershell
# Terminal 1
cd "<pad-naar-de-map>\revit-mcp-python.extension"
uv run --with "mcp[cli]" main.py --combined

# Terminal 2
devtunnel host revit-mcp
```

Zorg dat Revit open staat met pyRevit Routes actief. Zolang beide terminalvensters openstaan, blijft de Copilot Studio-agent werken.
