# PDF Mixer Pro

Un utilitar desktop (Tkinter) pentru operații rapide pe fișiere PDF: unire, intercalare, extragere/ștergere/rotire pagini, inversare ordine și split la N pagini. Ediție „NO-METADATA” — nu modifică intenționat metadatele fișierelor PDF rezultate.

## ✨ Caracteristici

* **Unește** mai multe PDF-uri în serie, în ordinea din listă
* **Intercalează** două PDF-uri (alternativ sau pe criterii impare/pare, cu offset configurabil)
* **Extrage** pagini după intervale (ex. `1-3,5,10`)
* **Șterge** pagini după intervale
* **Rotește** pagini (90/180/270°)
* **Inversează** ordinea paginilor
* **Împarte** un PDF în fișiere de câte **N** pagini
* **Drag & Drop** opțional (prin `tkinterdnd2`)
* UI modern dark, cu 3 palete (Indigo/Teal/Amber) și bară de progres non-modală
* **Nu** scrie metadate PDF — „NO-METADATA build”

## 📦 Instalare

Pe Windows, aplicația se construiește/rulează direct cu scriptul inclus **`build.bat`**.
Acesta se ocupă de:

* instalarea pachetelor necesare (`pypdf`, `tkinterdnd2`, `pyinstaller`)
* generarea executabilului final (`PDF Mixer Pro.exe`)

### Pași

1. Descarcă repository-ul (sau clonează-l din GitHub).
2. Rulează **`build.bat`** prin dublu click sau din Command Prompt.
3. După finalizare, vei găsi aplicația în folderul **`dist\PDF Mixer Pro.exe`**.

Nu este nevoie să instalezi manual dependențe — scriptul se ocupă de tot.

## 🚀 Rulare

După ce build-ul s-a terminat:

* mergi în `dist\`
* pornește **`PDF Mixer Pro.exe`**

Se deschide interfața grafică, gata de folosit.

## 🖱️ Utilizare

1. **Adaugă** PDF-uri (butonul „➕ Adaugă PDF-uri” sau drag & drop).
2. **Rearanjează** ordinea din listă.
3. Alege o **acțiune rapidă**:

   * unire, intercalare, extragere, ștergere, rotire, inversare, split.
4. Salvează fișierul rezultat.

## ⌨️ Shortcuts

* `Ctrl + O` – Adaugă PDF-uri
* `Ctrl + Q` – Ieșire

## ℹ️ „Despre”

* **Nume:** `PDF Mixer Pro` **v1.0**
* **Autor:** Alex Șerban Dâmbu — **Dâmbu Software**
* **Copyright:** © 2025. Toate drepturile rezervate.

