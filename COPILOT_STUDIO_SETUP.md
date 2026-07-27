# Revit MCP Server opstarten en koppelen aan Microsoft Copilot Studio

Deze gids beschrijft hoe je de Revit MCP-server (`main.py`) lokaal opstart en
via een dev tunnel beschikbaar maakt voor Microsoft Copilot Studio.

```
Copilot Studio (cloud)
       |  HTTPS + X-API-Key header
       v
  devtunnel  (publieke URL -> jouw pc)
       |
       v
  main.py  (MCP server, poort 8000)
       |  HTTP (localhost:48884)
       v
  pyRevit Routes  (binnen Revit)
       |
       v
  Revit
```

Er moeten dus **drie dingen tegelijk draaien** op je pc: Revit (met pyRevit
Routes actief), de MCP-server (`main.py`), en de dev tunnel.

---

## 1. Eenmalige installatie

### 1.1 pyRevit Routes activeren in Revit

1. In Revit: pyRevit-tab → **Settings**
2. **Routes** → activeer **Routes Server**
3. pyRevit luistert nu op `http://localhost:48884/`

### 1.2 De extensie installeren

Via pyRevit: pyRevit-tab → **Extensions** → *MCP Server for Revit Python
Extension* → **Install extension**. Of handmatig: zie de hoofd-[README.md](README.md#installing-the-extension-on-revit)
voor het toevoegen van een custom extension-pad.

Test daarna of Revit bereikbaar is:
```
http://localhost:48884/revit_mcp/status/
```

### 1.3 uv installeren (Python package runner)

Zie [README_UV.md](README_UV.md). Controleer met:
```powershell
uv --version
```

### 1.4 devtunnel CLI installeren

```powershell
winget install Microsoft.devtunnel
```

Open na installatie een **nieuwe** terminal (de eerste keer moet de PATH
ververst worden), en log daarna eenmalig in met je Microsoft-account:
```powershell
devtunnel user login
```
Dit opent een device-code flow: volg de link, log in met je account.

---

## 2. De MCP-server starten

In een terminal, in de map van dit project:
```powershell
cd "C:\Users\g.devogel\Downloads\revit-mcp-python.extension"
uv run --with "mcp[cli]" main.py --combined
```

Laat dit venster openstaan. Bij het opstarten print de server je API key,
bijvoorbeeld:
```
Starting combined SSE + streamable-http server on http://127.0.0.1:8000 (endpoint: /mcp)...
API key required on every request (header 'X-API-Key'): <jouw-key>
```

De key wordt ook lokaal opgeslagen in `.revit_mcp_api_key` (staat in
`.gitignore` — commit dit bestand nooit).

> **Poort al in gebruik?** Foutmelding `[Errno 10048] ... elk socketadres kan
> normaal slechts één keer worden gebruikt` betekent dat er al een proces op
> poort 8000 luistert. Zoek het op met `netstat -ano | findstr :8000` en sluit
> het oude proces af (`taskkill /F /PID <pid>`).

---

## 3. Een dev tunnel starten

In een **tweede, aparte** terminal:
```powershell
devtunnel host -p 8000 --allow-anonymous
```

- `--allow-anonymous` is nodig zodat Copilot Studio zonder Microsoft-login bij
  de tunnel kan. De beveiliging zit dan in de `X-API-Key` header, niet in de
  tunnel zelf.
- De output toont **twee** URL's per poort:
  - **Connect via browser**: `https://<id>-8000.<regio>.devtunnels.ms` — dit
    is de echte, publieke endpoint-URL die je in Copilot Studio gebruikt.
  - **Inspect network activity**: `https://<id>-8000-inspect.<regio>.devtunnels.ms`
    — **dit is géén API-endpoint**, maar een debug-paneel waarin je live
    binnenkomend verkeer kunt bekijken. Handig om te debuggen, maar gebruik
    deze URL nooit als server-URL.

> **Let op:** iedere keer dat je `devtunnel host` opnieuw start, kan de URL
> wijzigen tenzij je een persistent/named tunnel aanmaakt (`devtunnel create`
> met een vaste tunnel-ID). Bij een nieuwe URL moet je de server-URL in de
> Copilot Studio-connector bijwerken.

---

## 4. Koppelen in Copilot Studio

1. Open je agent op [copilotstudio.microsoft.com](https://copilotstudio.microsoft.com).
2. Ga naar het tabblad **Tools** → **Hulpmiddel toevoegen**.
3. Kies (of open) de **Model Context Protocol**-tool "Revit Connector".
4. Klik bij **Verbinding** op de chevron (▾) → **Nieuwe verbinding maken**.
5. Vul de API key in (uit stap 2, of `.revit_mcp_api_key`) en klik **Maken**.
6. Vul/controleer bij **Bijkomende details** de **Server URL**. Dit moet zijn:
   ```
   https://<jouw-devtunnel-id>-8000.<regio>.devtunnels.ms/mcp/
   ```
   **De trailing slash (`/mcp/`) is verplicht.** Zonder slash stuurt de
   server een `307 Temporary Redirect` terug, die Copilot Studio niet volgt
   bij POST-requests — het verzoek strandt dan zonder duidelijke foutmelding.
7. Klik op het vernieuw-icoontje (↻) naast "Naam van hulpmiddel" om de
   tool-lijst op te halen. Bij succes verschijnen tools als
   `get_revit_status`, `list_levels`, `place_family`, etc.
8. Vink de gewenste tools aan en sla op.

### Testen
Vraag je agent bijvoorbeeld: *"Wat is de status van de Revit-verbinding?"*
Dit zou de `get_revit_status`-tool moeten aanroepen en een live antwoord uit
je geopende Revit-document moeten teruggeven.

---

## 5. Troubleshooting

| Symptoom | Oorzaak | Oplossing |
|---|---|---|
| `401 Unauthorized` | Geen of verkeerde `X-API-Key` | Controleer de key in de connector tegen `.revit_mcp_api_key` |
| `404 Not Found` (JSON, via server) | Verkeerd pad aangeroepen | Server-URL moet eindigen op `/mcp/` |
| Plain-text `"Not Found"` (9 bytes), **Server**-header ontbreekt of is niet `uvicorn` | Verzoek komt niet bij `main.py` aan | Devtunnel-URL klopt niet (bv. `-inspect`-URL gebruikt), of `devtunnel host` draait niet |
| `307 Temporary Redirect` in de `main.py`-terminal | Server-URL mist trailing slash | Voeg `/` toe: `.../mcp/` |
| `[Errno 10048]` bij opstarten | Poort 8000 al bezet | Oud proces stoppen (zie sectie 2) |
| Tools verdwijnen / agent reageert niet meer | `main.py` of `devtunnel host` venster gesloten, of pc in slaapstand | Beide terminals opnieuw starten; bij nieuwe tunnel-URL ook de connector bijwerken |

### Live verkeer bekijken
Open de **inspect**-URL uit stap 3 in je browser terwijl je in Copilot Studio
een actie uitvoert (bv. ↻ klikken) — je ziet daar het binnenkomende
HTTP-verzoek inclusief pad, headers en response, wat het debuggen sterk
vereenvoudigt.

---

## 6. Dagelijks gebruik (kort overzicht)

Elke keer dat je dit opnieuw wilt gebruiken:

```powershell
# Terminal 1
cd "C:\Users\g.devogel\Downloads\revit-mcp-python.extension"
uv run --with "mcp[cli]" main.py --combined

# Terminal 2
devtunnel host -p 8000 --allow-anonymous
```

Zolang beide vensters open blijven (en Revit met Routes actief is), blijft de
Copilot Studio-agent werken — mits de server-URL in de connector nog
overeenkomt met de actieve devtunnel-URL.
