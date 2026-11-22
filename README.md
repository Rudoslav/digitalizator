# digitalizator

DIY náhrada CZUR skenera pre archívy: Android telefón na stojane nad stolom slúži ako kamera, počítač ukazuje živý náhľad,
**medzerník** (alebo nožný pedál, ktorý posiela medzerník) odfotí stranu, fotky sa uložia do priečinka spisu (`0001.jpg`, `0002.jpg`, …)
a jedným tlačidlom sa z nich urobí **PDF/A s OCR**. Všetko beží lokálne, nič sa nikam neposiela.

Stav: **MVP (v0.1)**, vyvíjané na Linuxe (Fedora). Windows balík zatiaľ nie je. Telefónna časť je v repe
[digitalizator-android](https://github.com/Rudoslav/digitalizator-android).

## Čo vie
- živý náhľad z telefónu cez USB, fotka v plnom rozlíšení (12 MP)
- rám A4 / A3 na náhľade, orezanie pri fotení podľa rámu
- zoznam strán, klik = pozastaví náhľad a ukáže stranu, **Delete** ju zmaže (aj z disku), **Pokračovať** vráti náhľad
- PDF/A s textovou vrstvou: OCR cez **PERO** (predvolené) alebo **Tesseract**, ukazovateľ priebehu
- **F11** celá obrazovka, **Ctrl + šípky / Ctrl +/−** doladenie rámu (ukladá sa do `~/.config/digitalizator/frame.json`)

## Inštalácia (Linux)
1. Programy: `sudo dnf install tesseract tesseract-langpack-{slk,ces,deu,hun} ghostscript android-tools`
2. Python: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
3. Telefón: nainštaluj APK z [releases digitalizator-android](https://github.com/Rudoslav/digitalizator-android/releases),
   zapni USB ladenie, pripoj USB kábel (na Xiaomi povoľ aj „Inštalácia cez USB" a pri prvom spustení kameru).
4. Spustenie: `.venv/bin/python desktop/mvp.py`

### PERO OCR (voliteľné, lepšie pre češtinu a slovenčinu)
PERO potrebuje Python 3.11 (kvôli `numpy~=1.24`) a PyTorch (okolo 2 GB, GPU netreba):
```
uv venv --python 3.11 .venv-pero
uv pip install --python .venv-pero/bin/python torch torchvision --index-url https://download.pytorch.org/whl/cpu
git clone --depth 1 -b develop https://github.com/DCGM/pero-ocr.git vendor/pero-ocr
uv pip install --python .venv-pero/bin/python ./vendor/pero-ocr
mkdir -p vendor/pero-models-dl && cd vendor/pero-models-dl
curl -L -o models.zip https://nextcloud.fit.vutbr.cz/s/NtAbHTNkZFpapdJ/download && unzip models.zip -d extracted
```
Bez PERO appka ponúkne len Tesseract. Modely PERO sú trénované na české noviny; pri maďarčine (ő, ű) a latinčine je lepší Tesseract.

## Porovnanie OCR enginov
`bench/bench.py` porovná enginy na stranách s ručne opraveným textom (chybovosť na znaky a zachovanie diakritiky):
`python bench/bench.py priecinok --engines tesseract,pero`

## Poznámky
- PDF/A vzniká cez Ghostscript (AGPL); formálne overenie validátorom (veraPDF) zatiaľ nebolo urobené.
- Font v `desktop/fonts/` (Liberation Sans, licencia SIL OFL) slúži len na neviditeľnú textovú vrstvu.
- Plán a zápis požiadaviek: [PLAN.md](PLAN.md), [ZAPIS.md](ZAPIS.md).
