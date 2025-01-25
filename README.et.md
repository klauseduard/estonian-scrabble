# Eesti Scrabble

Scrabble'i mängu rakendus, mis toetab eesti tähestikku ja kasutab eesti sõnastikku.

> **Arenduse märkus**: See projekt arendati eksperimendina tehisintellekti-toetatud programmeerimises, kasutades Cursor IDE agendi režiimi Claude-3.5-Sonnet mudeliga. Kogu arendusprotsess viidi läbi "YOLO režiimis", kus tehisintellekti agent osales aktiivselt koodi kirjutamises, vigade parandamises ja dokumentatsiooni koostamises.

## Eeldused

Enne alustamist veenduge, et teil on installitud:

1. **Python 3.8 või uuem**
   - Windows: Laadige alla ja installige [python.org](https://www.python.org/downloads/)
   - Linux: Tavaliselt eelinstallitud, või installige paketihalduri kaudu:
     ```bash
     sudo apt-get install python3  # Ubuntu/Debian jaoks
     sudo dnf install python3      # Fedora jaoks
     ```
   - macOS: Installige [Homebrew](https://brew.sh/) kaudu:
     ```bash
     brew install python3
     ```

2. **pip** (Pythoni paketihaldur)
   - Tavaliselt tuleb kaasa Pythoni installatsiooniga
   - Kontrollimiseks avage terminal/käsurida ja käivitage:
     ```bash
     pip --version  # või pip3 --version
     ```

## Installeerimine

1. **Laadige mäng alla**
   - Laadige see repositoorium alla ZIP-failina ja pakkige lahti
   - Või kui olete tuttav git-iga:
     ```bash
     git clone [repositooriumi-url]
     cd scrabble
     ```

2. **Avage Terminal/Käsurida**
   - Windows: Vajutage Win+R, sisestage `cmd`, vajutage Enter
   - macOS: Vajutage Cmd+Space, sisestage `terminal`, vajutage Enter
   - Linux: Vajutage Ctrl+Alt+T

3. **Liikuge mängu kausta**
   ```bash
   cd path/to/scrabble  # Asendage tegeliku teega
   ```

4. **Installige sõltuvused**
   ```bash
   pip install -r requirements.txt  # või pip3 install -r requirements.txt
   ```

5. **Käivitage mäng**
   ```bash
   python main.py  # või python3 main.py
   ```

## Kuidas mängida

1. **Mängu alustamine**
   - Käivitage mäng ülaltoodud käsuga
   - Avaneb mänguaken tühja mängulauaga
   - Kaks mängijat mängivad kordamööda

2. **Mängu juhtimine**
   - **Hiire juhtimine:**
     - Vajutage ja hoidke vasakut hiireklahvi, et lohistada tähti oma restilt lauale
     - Vabastage vasak hiireklahv tähe asetamiseks
     - Paremklõpsake laual olevat tähte, et see tagasi restile tuua
     - Vasakklõpsake nuppe ("Kinnita", "Jäta vahele", "Vaheta") toimingute sooritamiseks
   - Klõpsake "Kinnita", kui olete oma sõna asetamisega rahul
   - Klõpsake "Jäta vahele" käigu vahele jätmiseks
   - Klõpsake "Vaheta" tähtede vahetamiseks (loetakse käiguna)

3. **Esimene käik**
   - Tähed tuleb asetada läbi keskvälja
   - Peab moodustama korrektse eestikeelse sõna
   - Sõna peab olema loetav vasakult paremale või ülevalt alla

4. **Järgnevad käigud**
   - Uued tähed peavad ühenduma olemasolevate sõnadega
   - Kõik moodustatud sõnad peavad olema korrektsed eestikeelsed sõnad
   - Sõnad loetakse vasakult paremale või ülevalt alla

## Ekraanipildid

### Mängu liides
![Mängu algus](screenshots/game_start.png)
*Algne mängulaud preemiumruutudega*

![Rest ja juhtnupud](screenshots/rack_and_controls.png)
*Mängija täherida ja juhtnupud*

### Sõnade asetamine
![Korrektne sõna](screenshots/valid_word.png)
*Näide korrektsest sõna asetamisest (roheline esiletõst)*

![Vigane sõna](screenshots/invalid_word.png)
*Näide vigasest sõna asetamisest (punane esiletõst)*

### Mängu kulg
![Esimene käik](screenshots/first_move.png)
*Korrektne esimene käik läbi keskvälja*

![Mitu sõna](screenshots/multiple_words.png)
*Mitme korrektse sõna moodustamine ühe käiguga*

## Veaotsing

### Levinud probleemid

1. **"Python not found" või sarnane viga**
   - Veenduge, et Python on installitud ja lisatud PATH-i
   - Proovige kasutada `python3` `python` asemel
   - Taaskäivitage terminal/käsurida

2. **"pip not found" viga**
   - Veenduge, et pip on installitud
   - Proovige kasutada `pip3` `pip` asemel
   - Windowsis proovige: `py -m pip install -r requirements.txt`

3. **Mäng ei käivitu**
   - Veenduge, et kõik sõltuvused on installitud
   - Proovige sõltuvused uuesti installida:
     ```bash
     pip uninstall -r requirements.txt
     pip install -r requirements.txt
     ```

4. **Eesti tähed ei kuva korrektselt**
   - Veenduge, et teie süsteem toetab UTF-8
   - Proovige uuendada terminali/käsurea fonti

### Abi saamine

Probleemide korral:
1. Kontrollige ülaltoodud veaotsingu sektsiooni
2. Otsige sarnaseid probleeme projekti probleemide haldussüsteemist
3. Looge uus probleem, lisades:
   - Teie operatsioonisüsteem
   - Pythoni versioon (`python --version`)
   - Veateade (kui on)
   - Probleemi taasesitamise sammud

## Funktsioonid

- Täielik eesti tähestiku tugi, sealhulgas õ, ä, ö, ü, š, ž
- Visuaalne tagasiside korrektsete/vigaste sõnade asetamisel
- Tähtede lohistamine ja asetamine
- Reaalajas sõnade valideerimine
- Preemiumruutude punktisüsteem
- Kahe mängija tugi

## Projekti struktuur

```
scrabble/
├── game/                   # Mängu loogika ja oleku haldamine
│   ├── __init__.py        # Paketi eksport
│   ├── constants.py       # Mängu konstandid (tähtede jaotus, preemiumruudud)
│   ├── state.py          # Põhiline mängu oleku haldamine
│   └── word_validator.py  # Sõnade valideerimise loogika
├── ui/                    # Kasutajaliidese komponendid
│   ├── __init__.py       # Paketi eksport
│   └── components.py     # UI komponendid (Laud, Täht, Rest)
├── main.py               # Mängu põhiprogramm
├── requirements.txt      # Pythoni sõltuvused
└── README.md            # See fail
```

## Mängureeglid

- Mäng järgib standardseid Scrabble'i reegleid kohandustega eesti tähestiku jaoks
- Toetab eesti eritähti (õ, ä, ö, ü, š, ž)
- Kasutab eesti sõnastikku sõnade valideerimiseks
- Preemiumruudud järgivad standardset Scrabble'i laua paigutust

## Arendus

### Arhitektuur

Projekt järgib modulaarset arhitektuuri selge vastutuse jaotusega:

1. **Mängu loogika (`game/`):**
   - `state.py`: Haldab mängu olekut, mängijate käike ja tähtede asetamist
   - `word_validator.py`: Tegeleb sõnade valideerimise ja punktide arvestamisega
   - `constants.py`: Sisaldab mängu konstante ja seadistusi

2. **Kasutajaliides (`ui/`):**
   - `components.py`: Taaskasutatavad UI komponendid
   - Tegeleb kasutaja sisendi ja visuaalse tagasisidega

### Uute funktsioonide lisamine

Uute funktsioonide lisamisel:

1. Määrake, milline moodul peaks uut koodi sisaldama
2. Uuendage asjakohaseid teste (kui need lisame)
3. Järgige olemasolevat koodistiili
4. Uuendage dokumentatsiooni

### Koodistiil

- Kasutage tüübivihjeid funktsioonide parameetrite ja tagastusväärtuste jaoks
- Järgige PEP 8 juhiseid
- Kirjutage docstring'id klassidele ja funktsioonidele
- Hoidke funktsioonid fokuseeritud ja ühe eesmärgiga

## Panustamine

1. Tehke repositooriumist fork
2. Looge funktsiooni haru
3. Tehke oma muudatused
4. Esitage pull request

## Tulevased täiendused

> _Märkus: Järgnevad täiendused pakkus välja tehisintellekti agent arenduse käigus. Inimesest arendaja keskendus peamiselt põhilise mängu tööle saamisele! Tundke end vabalt neid funktsioone implementeerida, kui olete huvitatud._

✅ Implementeeritud:
- Eesti sõnastiku integratsioon
- Põhiline punktisüsteem preemiumruutudega
- Reaalajas sõnade valideerimine

🚀 Tehisintellekti soovide nimekiri:
1. **Täiustatud sõnade valideerimine**:
   - Liitsõnade toe lisamine
   - Sõnade vaidlustamise süsteemi implementeerimine mängijate vahel
   - Valideeritud sõnade vahemällu salvestamine jõudluse parandamiseks

2. **Mängu funktsioonid**:
   - Mängu oleku salvestamine/laadimine
   - Käikude tagasivõtmine/uuesti tegemine
   - Mängu taasesituse funktsioon
   - Turniirirežiim ajalimiitidega
   - Statistika jälgimine (kõrgeimad punktid, pikimad sõnad jne)

3. **Mitmikmäng**:
   - Võrgu kaudu mängimise tugi
   - Eesruum vastaste leidmiseks
   - Vestlusfunktsioon
   - Mängijate edetabel

4. **Tehisintellekti funktsioonid**:
   - Tehisintellekti vastane reguleeritava raskusastmega
   - Tehisintellekti käigusoovitused õppimiseks
   - Mängitud mängude analüüs

5. **Tehnilised täiendused**:
   - Ühiktestide katvus
   - Jõudluse optimeerimine
   - Korralik logimissüsteem
   - Seadistatavad mängureeglid
   - Platvormideülene pakkimine

6. **Kasutajaliidese täiendused**:
   - Animatsioonid tähtede asetamisel
   - Heliefektid
   - Tumeda/heleda teema tugi
   - Mobiilisõbralik kohanduv disain
   - Ligipääsetavuse funktsioonid

## Litsents

See projekt on avatud lähtekoodiga ja saadaval MIT litsentsi all. 