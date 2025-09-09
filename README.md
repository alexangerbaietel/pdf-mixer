# PDF Mixer Pro

Un utilitar desktop (Tkinter) pentru operații rapide pe fișiere PDF: unire, intercalare, extragere/ștergere/rotire pagini, inversare ordine și split la N pagini. Ediție „NO-METADATA” — nu modifică intenționat metadatele fișierelor PDF rezultate.&#x20;

## ✨ Caracteristici

* **Unește** mai multe PDF-uri în serie, în ordinea din listă.&#x20;
* **Intercalează** două PDF-uri (alternativ sau pe criterii impare/pare, cu offset configurabil).&#x20;
* **Extrage** pagini după intervale (ex. `1-3,5,10`).&#x20;
* **Șterge** pagini după intervale.&#x20;
* **Rotește** pagini (90/180/270°) pe tot documentul sau pe intervale.&#x20;
* **Inversează** ordinea paginilor.&#x20;
* **Împarte** un PDF în fișiere de câte **N** pagini.&#x20;
* **Drag & Drop** opțional (prin `tkinterdnd2`) pentru adăugarea rapidă a fișierelor/folderelor.&#x20;
* UI modern dark, cu 3 palete (Indigo/Teal/Amber) și bară de progres non-modală.&#x20;
* **Nu** scrie metadate PDF — „NO-METADATA build”.&#x20;

## 📦 Tech & cerințe

* Python 3 (testat cu 3.x)
* Dependențe:

  * [`pypdf`](https://pypi.org/project/pypdf/) — citire/scriere PDF (obligatoriu)&#x20;
  * `tkinter` — UI standard (inclus în distribuțiile Python pe Windows/macOS)&#x20;
  * `tkinterdnd2` — **opțional** pentru drag & drop.&#x20;

Instalare dependențe:

```bash
pip install pypdf tkinterdnd2
```

> Dacă nu instalezi `tkinterdnd2`, aplicația pornește fără drag & drop.&#x20;

## 🚀 Rulare

Clasic, din surse:

```bash
python PDF_Mixer_Pro_Alex_Dambu_v1_nometa.py
```

Aplicația pornește cu o fereastră GUI. Poți adăuga PDF-urile din disc sau prin drag & drop (dacă e activ).&#x20;

## 🖱️ Utilizare

1. **Adaugă** PDF-uri (butonul „➕ Adaugă PDF-uri” sau DnD).
2. **Rearanjează** ordinea (sus/jos, sortare Z→A, ștergere din listă).
3. Alege o **acțiune rapidă** din panoul din dreapta:

   * *Unește în serie*, *Intercalează (2 PDF-uri)*, *Extrage/Șterge/Rotire/Inversează/Împarte*.&#x20;
4. La salvare, alege un nume (ex.: `merged.pdf`, `extract_*.pdf`, `rotated_*.pdf`).&#x20;

### Intervalele de pagini

* Acceptă liste și intervale 1-based: `1,3,5-9,12-10` (intervalele descrescătoare sunt permise).
* Valorile în afara limitelor sunt ignorate; duplicatele se deduplică păstrând ordinea.&#x20;

### Intercalare

* Moduri: **alternativ** (A1,B1,A2,B2…), **A impare + B pare**, **A pare + B impare**, **doar impare din A**, **doar pare din B**.
* Paginarea poate începe de la un index 1-based configurabil.&#x20;

## ⌨️ Shortcuts

* `Ctrl + O` – Adaugă PDF-uri
* `Ctrl + Q` – Ieșire&#x20;

## 🧰 Build / distribuire

### Windows (exemplu)

Repo-ul include un `build.bat` (Windows). Poți adapta un scenariu cu **PyInstaller**:

```bat
py -m pip install --upgrade pip
py -m pip install pypdf tkinterdnd2 pyinstaller
py -m PyInstaller --noconsole --name "PDF Mixer Pro" --onefile PDF_Mixer_Pro_Alex_Dambu_v1_nometa.py
```

> `tkinter` vine de obicei cu Python pe Windows; dacă lipsește, instalează distribuția oficială Python. Aplicația folosește și o optimizare pentru titlurile ferestrelor dark pe Windows, acolo unde e posibil.&#x20;

### macOS / Linux

Rulează din surse sau creează pachete (`pyinstaller`, `briefcase`, `pyoxidizer`) după preferințe.

## 🖌️ Tematizare

* 3 palete dark predefinite: **Indigo**, **Teal**, **Amber** (meniul *Aspect*).
* Stilizare modernă pentru `ttk` + tooltip-uri.&#x20;

## ℹ️ „Despre”

* **Nume:** `PDF Mixer Pro` **v1.0**
* **Autor:** Alex Șerban Dâmbu — **Dâmbu Software**
* **Copyright:** © 2025. Toate drepturile rezervate.




