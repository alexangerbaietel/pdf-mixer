# PDF Mixer Pro (NO-METADATA)

**PDF Mixer Pro** este o aplicație desktop (Python + Tkinter) pentru lucrul rapid cu PDF-uri: îmbinare, intercalare, extragere/ștergere pagini, rotire, inversare, split – plus conversii **Word/Excel/PowerPoint → PDF** și **Poze → PDF**.  
Include o filozofie **NO-METADATA**: după export, PDF-urile sunt „rescrise” doar cu paginile, pentru a elimina metadatele (best-effort).

---

## Funcții principale

### PDF Tools
- **Unește în serie** (n PDF-uri) în ordinea din listă
- **Intercalează 2 PDF-uri** (alternativ / impare+pare etc.)
- **Extrage pagini** (intervale: `1-3,5,10`)
- **Șterge pagini** (intervale: `2,5-7`)
- **Rotire pagini** (90/180/270, pe intervale)
- **Inversează paginile** (ordine descrescătoare)
- **Split din N în N pagini**

### Convert
- **PowerPoint → PDF**
- **Excel → PDF (all sheets, landscape)**
- **Word → PDF**
- **Poze → PDF** (mai multe imagini, 1 pagină/imagine, cu opțiuni: A4/A3/Letter/Legal, margini, DPI etc.)

### NO-METADATA (sanitizer)
După export (merge/convert/poze etc.), aplicația rulează un „sanitizer” care:
- rescrie PDF-ul doar cu paginile
- încearcă să elimine `/Info` și XMP metadata (best-effort)

---

## Cerințe

- Python 3.9+ (recomandat)
- Dependențe:
  - `pypdf`
  - `pillow` (pentru Poze → PDF)
  - `tkinterdnd2` (opțional, pentru Drag & Drop)
  - `pywin32` (opțional, doar Windows, pentru conversie Office prin COM)
- Fallback conversie:
  - **LibreOffice** instalat (soffice în PATH) sau setat prin `SOFFICE_PATH`

---

## Instalare

### 1) Creează un mediu virtual (recomandat)
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
```

### 2) Instalează dependențele

```bash
pip install pypdf pillow
```

### 3) (Opțional) Drag & Drop

```bash
pip install tkinterdnd2
```

### 4) (Windows) Conversie Office prin COM (fără ferestre)

```bash
pip install pywin32
```

> Dacă `pywin32` sau Microsoft Office nu sunt disponibile, conversia se face prin **LibreOffice headless** (fallback).

---

## LibreOffice fallback (soffice)

Aplicația caută `soffice` astfel:

1. variabila de mediu `SOFFICE_PATH`
2. `soffice` / `soffice.exe` în PATH
3. locații comune (Windows/Mac/Linux)

### Setare `SOFFICE_PATH` (Windows exemplu)

```bat
setx SOFFICE_PATH "C:\Program Files\LibreOffice\program\soffice.exe"
```

---

## Rulare

```bash
python pdf_mixer_pro.py
```

(Dacă fișierul are alt nume, rulează scriptul respectiv.)

---

## Utilizare rapidă

### PDF-uri

1. Apasă **➕ Adaugă PDF-uri** (sau drag & drop dacă ai `tkinterdnd2`)
2. Reordonează lista (Sus/Jos) sau sortează
3. Alege acțiunea din partea dreaptă (Merge/Interleave/Extract etc.)

### Convert (Word/Excel/PPT)

* Din meniul **Convert** sau din „Convert rapid”:

  * selectezi fișierele
  * alegi folderul de output
  * aplicația produce PDF-uri și rulează sanitizer-ul NO-METADATA

### Poze → PDF

* Selectezi imaginile
* Alegi opțiunile (dimensiune pagină, margini, DPI etc.)
* Salvezi PDF-ul final

---

## Notițe / Limitări

* Bara de progres este **indeterminate** (spinner). Unele operații grele pot bloca UI-ul (Tkinter este single-thread).
* Conversia Office prin COM funcționează doar pe **Windows** cu Microsoft Office instalat.
* Fallback-ul LibreOffice necesită instalare LibreOffice și acces la `soffice`.

---

## Branding

* App: **PDF Mixer Pro**
* Company: **Dâmbu Software**
* Author: **Alex Șerban Dâmbu**
* Copyright: **(c) 2026**
* All rights reserved.

---

## Licență

Acest software este furnizat **„ca atare”**, fără garanții.

```

