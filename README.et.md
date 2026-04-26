# Eesti Scrabble

Eestikeelne Scrabble mitmekesi veebis mängimiseks. Toetab eesti keele eritähti (õ, ä, ö, ü, š, ž) ja kasutab Hunspelli sõnastikku morfoloogiliseks sõnade kontrolliks.

**Mängi kohe**: [klauseduard.duckdns.org/scrabble](https://klauseduard.duckdns.org/scrabble/)

> **Märkus**: See projekt loodi algselt tehisintellekti abil (Cursor IDE + Claude) 2025. aastal. Veebipõhine mitmikmängu versioon loodi Claude Code'iga 2026. aastal.

> [English documentation (README in English)](README.md)

## Funktsioonid

- **2-4 mängijat** eraldi seadmetel WebSocketi kaudu
- **Reaalajas** laua uuendused, punktide eelvaade, käiguteated
- **Mängusisene vestlus** süsteemiteadetega käikude ja vaidlustuste kohta
- **Käigu vaidlustamine** — vaidlusta mis tahes käik, palu mängijal tagasi võtta
- **Heakskiidu palumine** — mängi sõnu, mida programm ei tunne, kui kõik mängijad nõustuvad
- **Taasühendamine** — liitu mänguga uuesti, kui brauser jookseb kokku
- **Resti ümberjärjestamine** — lohista tähti ümber järjestamiseks
- **Tähtede vahetamine** — vaheta tähti kotist
- **Avalik fuajee** — leia avatud mänge või loo enda oma
- **Eestikeelne liides**

## Ekraanipildid

### Veebiversioon

![Fuajee](screenshots/web_lobby.png)
*Fuajee — loo uus mäng või liitu toa koodiga*

![Ootesaal](screenshots/web_waiting_room.png)
*Ootesaal — jaga toa koodi sõpradega*

![Mängulaud](screenshots/web_game_board.png)
*Mängulaud koos punktidega, täherida ja vestlus*

![Mäng vestlusega](screenshots/web_game_with_chat.png)
*Mängusisene vestlus süsteemi käiguteadetega*

### Töölauaversioon (Pygame)

> *Ekraanipildid näitavad Pygame töölauaversiooni, mis on endiselt saadaval.*

![Mängu algus](screenshots/game_start.png)
*Töölaua mängulaud preemiumruutudega*

![Korrektne sõna](screenshots/valid_word.png)
*Korrektne sõna asetamine (roheline esiletõst)*

## Kuidas mängida

### Veebiversioon
1. Ava mäng aadressil [klauseduard.duckdns.org/scrabble](https://klauseduard.duckdns.org/scrabble/)
2. Sisesta oma nimi ja loo uus mäng või liitu toa koodiga
3. Jaga 4-tähelist toa koodi sõpradega
4. Klõpsa või lohista tähti restilt lauale
5. Paremklõps (või puudutus) asetatud tähtedel, et need restile tagasi tuua
6. Klõpsa **Kinnita käik** sõna esitamiseks
7. Kui sõnastik ei tunne sõna, klõpsa **Palu heakskiitu** teiste mängijate nõusoleku küsimiseks

### Töölauaversioon (Pygame)
1. Käivita `python main.py`
2. Vali mängijate arv (2-4) ja sisesta nimed
3. Lohista tähti restilt lauale, paremklõps eemaldamiseks
4. Klõpsa "Kinnita käik" või "Jäta vahele"

## Veebiversioon

Mäng sisaldab veebipõhist mitmikmängu režiimi WebSocketite kaudu.

### Käivita lokaalselt

```bash
pip install -r requirements-server.txt
uvicorn server.app:app
```

Ava http://localhost:8000 brauseris.

### Käivita Dockeriga

```bash
docker compose up --build
```

Ava http://localhost:8080 brauseris.

## Projekti struktuur

```
├── game/                   # Mängu loogika (Pygame-sõltumatu)
│   ├── constants.py        # Tähtede jaotus, preemiumruudud
│   ├── state.py            # Mängu oleku haldamine
│   └── word_validator.py   # Sõnade valideerimise loogika
├── server/                 # FastAPI WebSocket server
│   ├── app.py              # WebSocket endpoindid ja mängu tegevused
│   ├── room.py             # Tubade haldamine, taasühendamine
│   └── serialization.py    # Mängu oleku JSON serialiseerimine
├── web/                    # Veebi kasutajaliides
│   ├── index.html          # Üheleheline rakendus
│   ├── css/                # Stiililehed
│   └── js/                 # Kliendipoolne loogika
├── ui/                     # Pygame töölaua kasutajaliides
├── tests/                  # Ühiktestid
├── main.py                 # Pygame mängu käivitamine
├── wordlist.py             # Hunspelli sõnastiku integratsioon
├── Dockerfile              # Docker konteineriseerimiseks
└── requirements.txt        # Pythoni sõltuvused
```

## Veaotsing

- **Veebiversioon**: Töötab igas kaasaegses brauseris. Kui WebSocket ühendus ebaõnnestub, kontrolli et sinu võrk ei blokeeri WebSocket liiklust.
- **Töölauaversioon**: Vajab Python 3.8+ ja Pygame. Käivita `pip install -r requirements.txt` sõltuvuste installimiseks.

## Tulevased ideed

- Tehisintellekti vastane reguleeritava raskusastmega
- Statistika jälgimine (kõrgeimad punktid, pikimad sõnad)
- Mängude salvestamine/jätkamine üle serveri taaskäivituste
- Sõnade valideerimise parandamine (spylls'il on [teadaolevaid valepositiivseid](https://github.com/klauseduard/estonian-scrabble/issues/32))

## Abi

Vigadest teatamine ja ettepanekud: [GitHub Issues](https://github.com/klauseduard/estonian-scrabble/issues) või email klaus.eduard@gmail.com

## Litsents

See projekt on avatud lähtekoodiga ja saadaval MIT litsentsi all.
