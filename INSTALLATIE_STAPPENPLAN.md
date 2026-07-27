========================================================================
REVIT MCP SERVER + COPILOT STUDIO
Volledig installatie-stappenplan voor een nieuwe PC
========================================================================

Dit document beschrijft alle stappen om vanaf een schone Windows-pc:
1. De Revit MCP-extensie te installeren
2. De MCP-server op te starten
3. Een publieke tunnel op te zetten
4. De koppeling met Microsoft Copilot Studio te maken

Benodigdheden vooraf:
- Revit met pyRevit geinstalleerd
- Windows met winget beschikbaar (standaard bij Windows 10/11)
- Een Microsoft-account (voor devtunnel login)
- Toegang tot Microsoft Copilot Studio met een agent waarin je tools mag
  toevoegen

------------------------------------------------------------------------
STAP 1 - pyRevit Routes activeren
------------------------------------------------------------------------
1. Open Revit
2. Ga naar het pyRevit-tabblad -> Settings
3. Ga naar "Routes" en activeer "Routes Server"
   (pyRevit luistert nu op http://localhost:48884/)

------------------------------------------------------------------------
STAP 2 - De extensie ophalen en installeren
------------------------------------------------------------------------
Optie A - via pyRevit Extensions:
1. pyRevit-tabblad -> Extensions
2. Zoek "MCP Server for Revit Python Extension" -> Install extension
3. Kies een locatie (standaard: %APPDATA%\Roaming\pyRevit\Extensions)
4. Schakel de extensie in en herstart Revit indien nodig

Optie B - handmatig (bijvoorbeeld als je deze eigen/aangepaste versie
gebruikt, kopieer dan de hele projectmap naar de nieuwe pc, bijvoorbeeld
via een USB-stick, netwerkschijf of git clone):
1. Zorg dat de mapnaam eindigt op ".extension"
   (bijvoorbeeld: revit-mcp-python.extension)
2. In Revit: pyRevit-tabblad -> Settings
3. Onder "Custom Extensions" -> voeg het pad naar de map toe
4. Sla op en herlaad pyRevit (herstart Revit indien nodig)

Controleer de verbinding door in een browser te openen:
   http://localhost:48884/revit_mcp/status/

Je moet een antwoord zien zoals:
   {"status": "active", "health": "healthy", "revit_available": true, ...}

------------------------------------------------------------------------
STAP 3 - Python packagemanager "uv" installeren
------------------------------------------------------------------------
Open PowerShell en voer uit:

   winget install astral-sh.uv

Sluit de terminal en open een NIEUWE terminal (nodig zodat de PATH
ververst wordt). Controleer:

   uv --version

------------------------------------------------------------------------
STAP 4 - devtunnel CLI installeren
------------------------------------------------------------------------
In PowerShell:

   winget install Microsoft.devtunnel

Sluit de terminal en open een NIEUWE terminal. Controleer:

   devtunnel --version

Log daarna eenmalig in met je Microsoft-account:

   devtunnel user login

Dit toont een link (https://login.microsoft.com/device) en een code.
Open de link in een browser, voer de code in en log in.

------------------------------------------------------------------------
STAP 5 - Een vaste (persistente) tunnel aanmaken - EENMALIG
------------------------------------------------------------------------
Kies een eigen unieke naam (hier gebruikt als voorbeeld: revit-mcp).
Als de naam al bestaat op jouw account, kies een andere naam.

   devtunnel create revit-mcp -a
   devtunnel port create revit-mcp -p 8000

Uitleg:
- "create revit-mcp -a" maakt een tunnel met vaste naam "revit-mcp" en
  staat anonieme toegang toe (-a), nodig zodat Copilot Studio er zonder
  Microsoft-login bij kan. De beveiliging loopt via de API-key, niet via
  de tunnel-login.
- "port create ... -p 8000" koppelt poort 8000 (waar de MCP-server op
  draait) aan deze tunnel.

Dit is EENMALIG per pc/account. Na deze stap hoef je nooit meer een
nieuwe tunnel aan te maken.

------------------------------------------------------------------------
STAP 6 - Project ophalen (indien nog niet aanwezig op deze pc)
------------------------------------------------------------------------
Kopieer of clone de volledige projectmap naar de nieuwe pc, bijvoorbeeld:

   git clone <url-van-de-repo> revit-mcp-python.extension

(Of kopieer de bestaande map handmatig over, bijvoorbeeld via een
netwerkschijf of USB-stick.)

------------------------------------------------------------------------
STAP 7 - De MCP-server starten
------------------------------------------------------------------------
Open een terminal, ga naar de projectmap en start de server:

   cd "<pad-naar-de-map>\revit-mcp-python.extension"
   uv run --with "mcp[cli]" main.py --combined

Laat dit venster open staan. Bij het opstarten print de server iets als:

   Starting combined SSE + streamable-http server on http://127.0.0.1:8000 (endpoint: /mcp)...
   API key required on every request (header 'X-API-Key'): <lange-sleutel>

Onthoud/kopieer deze API-key (deze wordt ook automatisch opgeslagen in
het bestand ".revit_mcp_api_key" in de projectmap - dit bestand wordt bij
de eerste start automatisch aangemaakt als het nog niet bestaat, en is
per installatie/pc uniek).

Probleem "poort al in gebruik" (Errno 10048)?
   Er draait al iets op poort 8000. Zoek het proces op:
      netstat -ano | findstr :8000
   Sluit het af (vervang <pid> door het gevonden proces-ID):
      taskkill /F /PID <pid>

------------------------------------------------------------------------
STAP 8 - De tunnel starten
------------------------------------------------------------------------
Open een TWEEDE, aparte terminal en voer uit:

   devtunnel host revit-mcp

(Gebruik hier de naam die je in Stap 5 hebt gekozen.)

De output toont twee URL's per poort:
- "Connect via browser": dit is de echte publieke URL die je in Copilot
  Studio gebruikt, bijvoorbeeld:
     https://revit-mcp-8000.euw.devtunnels.ms
- "Inspect network activity": dit is GEEN API-endpoint, maar een
  debug-scherm om live verkeer te bekijken. Gebruik deze URL nooit als
  server-URL in Copilot Studio.

Omdat je in Stap 5 een vaste tunnel-naam hebt gebruikt, blijft deze URL
voortaan altijd hetzelfde, ook na een herstart.

------------------------------------------------------------------------
STAP 9 - Koppelen in Microsoft Copilot Studio
------------------------------------------------------------------------
1. Ga naar copilotstudio.microsoft.com en open de gewenste agent
2. Ga naar het tabblad "Tools" -> "Hulpmiddel toevoegen"
3. Kies (of maak) de "Model Context Protocol"-tool, bijvoorbeeld
   genaamd "Revit Connector"
4. Bij "Verbinding" -> klik op de pijl (chevron) -> "Nieuwe verbinding
   maken"
5. Vul de API-key in (uit Stap 7) en klik op "Maken"
6. Vul/controleer onder "Bijkomende details" de Server URL. Dit moet
   zijn (let op: MET slash op het einde!):

      https://<jouw-tunnel-naam>-8000.<regio>.devtunnels.ms/mcp/

   BELANGRIJK: de trailing slash "/mcp/" is verplicht. Zonder de slash
   op het einde geeft de server een 307-redirect terug die Copilot
   Studio niet volgt, waardoor de koppeling zonder duidelijke
   foutmelding vastloopt.
7. Klik op het vernieuw-icoon (rondje met pijl) naast "Naam van
   hulpmiddel" om de tool-lijst op te halen. Bij succes zie je namen
   zoals get_revit_status, list_levels, place_family, enzovoort.
8. Vink de gewenste tools aan en sla op.

Test met een vraag aan je agent, bijvoorbeeld:
   "Wat is de status van de Revit-verbinding?"

------------------------------------------------------------------------
STAP 10 - Foutmeldingen en oplossingen
------------------------------------------------------------------------
401 Unauthorized
   -> Geen of verkeerde X-API-Key. Vergelijk met de sleutel in het
      bestand .revit_mcp_api_key.

404 Not Found (met JSON-inhoud, via de server)
   -> Verkeerd pad. Server-URL moet eindigen op /mcp/

Platte tekst "Not Found" (9 bytes, geen "Server: uvicorn"-header)
   -> Het verzoek komt niet bij main.py aan. Controleer of je de juiste
      tunnel-URL gebruikt (niet de -inspect-URL) en of "devtunnel host"
      nog draait.

307 Temporary Redirect (te zien in het main.py-venster)
   -> Server-URL mist de trailing slash. Voeg toe: /mcp/

[Errno 10048] bij het opstarten van main.py
   -> Poort 8000 is al in gebruik. Zie Stap 7 voor de oplossing.

Tools verdwijnen of de agent reageert niet meer
   -> Het venster van main.py of devtunnel host is gesloten, of de pc
      stond in slaapstand. Start beide opnieuw (zie Stap 7 en 8).
      Dankzij de vaste tunnel-naam (Stap 5) blijft de URL wel gelijk.

------------------------------------------------------------------------
DAGELIJKS GEBRUIK - KORT OVERZICHT
------------------------------------------------------------------------
Na de eenmalige installatie (Stap 1 t/m 6) is elke volgende keer starten
zo simpel als:

   Terminal 1:
      cd "<pad-naar-de-map>\revit-mcp-python.extension"
      uv run --with "mcp[cli]" main.py --combined

   Terminal 2:
      devtunnel host revit-mcp

Zorg dat Revit open staat met pyRevit Routes actief. Zolang beide
terminalvensters openstaan, blijft de Copilot Studio-agent werken.
