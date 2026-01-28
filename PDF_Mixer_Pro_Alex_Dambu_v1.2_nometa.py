#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Mixer Pro – v1.2 (Branded, NO-METADATA)
Author: Alex Șerban Dâmbu
Company: Dâmbu Software
Copyright (c) 2026
All rights reserved.

Built with: Python + Tkinter + pypdf
Optional DnD via: tkinterdnd2

NEW in v1.2:
- Convert PowerPoint/Excel/Word -> PDF (Microsoft Office COM, runs in background; no windows shown)
- Fallback conversion via LibreOffice headless (soffice) if Office/pywin32 not available
- Images -> PDF (multiple images, one page per image)
- Post-export PDF sanitizer: re-writes pages only to avoid metadata (NO-METADATA philosophy)

Dependencies:
- pypdf
- optional: tkinterdnd2
- Windows Office conversion: pywin32  (pip install pywin32)
- Images -> PDF: pillow (pip install pillow)
- Fallback: LibreOffice installed (soffice in PATH or set SOFFICE_PATH)
"""

import os
import time
import platform
import ctypes
import subprocess
import shutil
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
from typing import List, Optional

# Optional OS drag & drop
_dnd_available = True
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES  # type: ignore
except Exception:
    _dnd_available = False

# PDF core
try:
    from pypdf import PdfReader, PdfWriter
except Exception:
    print("Eroare: trebuie instalat 'pypdf' (pip install pypdf)")
    raise

# Images -> PDF
_PIL_OK = True
try:
    from PIL import Image
except Exception:
    _PIL_OK = False

# Microsoft Office COM (Windows)
_HAS_WIN32 = False
if platform.system() == "Windows":
    try:
        import win32com.client  # type: ignore
        _HAS_WIN32 = True
    except Exception:
        _HAS_WIN32 = False

# ------------------ Branding & App Consts ------------------
APP_NAME = "PDF Mixer Pro"
APP_VERSION = "1.2"
BRAND_AUTHOR = "Alex Șerban Dâmbu"
BRAND_COMPANY = "Dâmbu Software"
COPYRIGHT_YEAR = "2025"
APP_TITLE = f"{APP_NAME} – v{APP_VERSION} • {BRAND_COMPANY}"
APP_MIN_W, APP_MIN_H = 1100, 720

# Palettes
PALETTES = {
    "indigo": dict(ACCENT="#6C5CE7", BG_MAIN="#0f141a", BG_CARD="#151b23", FG_TEXT="#e6e9ef", FG_MUTED="#9aa4ad"),
    "teal":   dict(ACCENT="#19c5b9", BG_MAIN="#0e1416", BG_CARD="#122024", FG_TEXT="#e6f4f1", FG_MUTED="#93b6b1"),
    "amber":  dict(ACCENT="#ffb300", BG_MAIN="#14120c", BG_CARD="#1b1911", FG_TEXT="#f4efe5", FG_MUTED="#a79f8c"),
}
CURRENT_PALETTE_NAME = "indigo"
THEME = PALETTES[CURRENT_PALETTE_NAME]

# ------------------ Utilities ------------------

class Tooltip:
    def __init__(self, widget, text: str, delay_ms: int = 450):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id = None
        self.tip = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _schedule(self, _):
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _show(self):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.overrideredirect(True)
        self.tip.attributes("-topmost", True)
        frm = tk.Frame(self.tip, bg="#1e2630", bd=0, highlightthickness=0)
        frm.pack()
        lbl = tk.Label(frm, text=self.text, bg="#1e2630", fg=THEME['FG_TEXT'],
                        font=("Segoe UI", 9), padx=8, pady=6, justify="left")
        lbl.pack()
        self.tip.geometry(f"+{x}+{y}")

    def _hide(self, _=None):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        if self.tip:
            self.tip.destroy()
            self.tip = None


def parse_page_ranges(ranges_str: str, total_pages: int) -> List[int]:
    if not ranges_str or not ranges_str.strip():
        return []
    indices: List[int] = []
    for part in [p.strip() for p in ranges_str.split(",")]:
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                start, end = int(a), int(b)
            except ValueError:
                continue
            step = 1 if start <= end else -1
            for v in range(start, end + step, step):
                if 1 <= v <= total_pages:
                    indices.append(v - 1)
        else:
            try:
                v = int(part)
                if 1 <= v <= total_pages:
                    indices.append(v - 1)
            except ValueError:
                continue
    # dedup keep order
    out, seen = [], set()
    for i in indices:
        if i not in seen:
            seen.add(i); out.append(i)
    return out


def ask_save_as(default_name: str = "output.pdf") -> Optional[str]:
    return filedialog.asksaveasfilename(
        title="Salvează ca...",
        defaultextension=".pdf",
        initialfile=default_name,
        filetypes=[("PDF files", "*.pdf")]
    )


def safe_open_reader(path: str) -> Optional[PdfReader]:
    try:
        r = PdfReader(path)
        _ = len(r.pages)
        return r
    except Exception as e:
        messagebox.showerror("Eroare la deschidere PDF", f"Nu pot deschide „{os.path.basename(path)}”.\n\n{e}")
        return None


def rotate_page(page, degrees: int):
    d = degrees % 360
    if d:
        page.rotate(d)
    return page


def _parse_dnd_file_list(dnd_data: str) -> List[str]:
    if not dnd_data:
        return []
    out, token, in_brace = [], "", False
    for ch in dnd_data:
        if ch == "{":
            in_brace = True; token = ""
        elif ch == "}":
            in_brace = False; out.append(token); token = ""
        elif ch == " " and not in_brace:
            if token: out.append(token); token = ""
        else:
            token += ch
    if token: out.append(token)
    return [os.path.normpath(p) for p in out]


def _collect_pdfs_from_paths(paths: List[str]) -> List[str]:
    pdfs = []
    for p in paths:
        if os.path.isdir(p):
            for name in sorted(os.listdir(p)):
                if name.lower().endswith(".pdf"):
                    pdfs.append(os.path.join(p, name))
        else:
            if p.lower().endswith(".pdf"):
                pdfs.append(p)
    return pdfs


# ------------------ NO-METADATA Sanitizer ------------------

def sanitize_pdf_no_metadata(src_pdf: str, dst_pdf: str) -> None:
    """
    Rescrie PDF-ul fără /Info și fără XMP metadata (best-effort),
    păstrând doar paginile.
    """
    r = PdfReader(src_pdf)
    w = PdfWriter()
    for p in r.pages:
        w.add_page(p)

    try:
        w.add_metadata({})
    except Exception:
        pass
    try:
        w.xmp_metadata = None  # type: ignore[attr-defined]
    except Exception:
        pass

    with open(dst_pdf, "wb") as f:
        w.write(f)


def auto_rotate_pdf_pages_to_landscape(src_pdf: str, dst_pdf: str) -> None:
    """
    Dacă o pagină are mediabox portrait (H > W), o rotim 90°.
    Util pentru Excel când output-ul e portrait.
    """
    r = PdfReader(src_pdf)
    w = PdfWriter()
    for p in r.pages:
        mb = p.mediabox
        width = float(mb.width)
        height = float(mb.height)
        if height > width:
            p.rotate(90)
        w.add_page(p)
    with open(dst_pdf, "wb") as f:
        w.write(f)


# ------------------ LibreOffice fallback ------------------

def find_soffice() -> Optional[str]:
    env = os.environ.get("SOFFICE_PATH", "").strip()
    if env and os.path.isfile(env):
        return env

    in_path = shutil.which("soffice") or shutil.which("soffice.exe")
    if in_path:
        return in_path

    candidates = []
    if platform.system() == "Windows":
        candidates += [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
    elif platform.system() == "Darwin":
        candidates += ["/Applications/LibreOffice.app/Contents/MacOS/soffice"]
    else:
        candidates += ["/usr/bin/soffice", "/snap/bin/libreoffice", "/usr/bin/libreoffice"]

    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def soffice_convert_to_pdf(in_path: str, out_pdf: str, timeout_s: int = 180) -> None:
    soffice = find_soffice()
    if not soffice:
        raise RuntimeError(
            "Nu am găsit LibreOffice (soffice).\n\n"
            "Instalează LibreOffice sau setează SOFFICE_PATH către soffice(.exe)."
        )

    in_path = os.path.abspath(in_path)
    out_pdf = os.path.abspath(out_pdf)
    out_dir = os.path.dirname(out_pdf)
    os.makedirs(out_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            soffice,
            "--headless", "--nologo", "--nofirststartwizard",
            "--convert-to", "pdf",
            "--outdir", tmpdir,
            in_path
        ]
        subprocess.run(cmd, check=True, timeout=timeout_s)

        produced = os.path.join(tmpdir, os.path.splitext(os.path.basename(in_path))[0] + ".pdf")
        if not os.path.exists(produced):
            raise RuntimeError("Conversia LibreOffice a eșuat (PDF rezultat nu a fost găsit).")
        os.replace(produced, out_pdf)


# ------------------ Microsoft Office COM converters (background) ------------------

def convert_word_to_pdf_office(in_path: str, out_pdf: str) -> None:
    if not _HAS_WIN32:
        raise RuntimeError("pywin32 nu este disponibil. Instalează: pip install pywin32")
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(os.path.abspath(in_path), ReadOnly=True)
        try:
            # 17 = wdExportFormatPDF
            doc.ExportAsFixedFormat(os.path.abspath(out_pdf), 17)
        finally:
            doc.Close(False)
    finally:
        word.Quit()


def convert_excel_to_pdf_office_all_sheets_landscape(in_path: str, out_pdf: str) -> None:
    if not _HAS_WIN32:
        raise RuntimeError("pywin32 nu este disponibil. Instalează: pip install pywin32")

    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    excel.ScreenUpdating = False
    try:
        wb = excel.Workbooks.Open(os.path.abspath(in_path), ReadOnly=True)
        try:
            # 2 = xlLandscape
            for ws in wb.Worksheets:
                try:
                    ws.Activate()

                    # --- 1) Dezactivează wrap text (scade riscul de "intercalat" aiurea)
                    try:
                        ws.Cells.WrapText = False
                    except Exception:
                        pass

                    # --- 2) AutoFit pe coloane și rânduri
                    try:
                        used = ws.UsedRange
                        # auto-fit columns/rows on used area
                        used.Columns.AutoFit()
                        used.Rows.AutoFit()
                    except Exception:
                        # fallback mai agresiv dacă UsedRange dă rateu
                        try:
                            ws.Cells.EntireColumn.AutoFit()
                            ws.Cells.EntireRow.AutoFit()
                        except Exception:
                            pass

                    # --- 3) Page setup landscape + fit to width
                    try:
                        ps = ws.PageSetup
                        ps.Orientation = 2
                        ps.Zoom = False
                        ps.FitToPagesWide = 1
                        ps.FitToPagesTall = False
                    except Exception:
                        pass

                except Exception:
                    pass

            # 0 = xlTypePDF
            wb.ExportAsFixedFormat(0, os.path.abspath(out_pdf))
        finally:
            wb.Close(False)
    finally:
        excel.ScreenUpdating = True
        excel.Quit()



def convert_powerpoint_to_pdf_office(in_path: str, out_pdf: str) -> None:
    if not _HAS_WIN32:
        raise RuntimeError("pywin32 nu este disponibil. Instalează: pip install pywin32")
    ppt = win32com.client.DispatchEx("PowerPoint.Application")
    try:
        # WithWindow=False => no UI
        pres = ppt.Presentations.Open(os.path.abspath(in_path), WithWindow=False)
        try:
            # 32 = ppSaveAsPDF
            pres.SaveAs(os.path.abspath(out_pdf), 32)
        finally:
            pres.Close()
    finally:
        ppt.Quit()


def convert_office_doc_to_pdf(in_path: str, out_pdf: str, kind: str) -> None:
    """
    kind: 'word' | 'excel' | 'ppt'
    Tries Office COM first; fallback to LibreOffice if Office fails or not available.
    """
    last_err = None

    # Office first (background)
    try:
        if kind == "word":
            convert_word_to_pdf_office(in_path, out_pdf)
        elif kind == "excel":
            convert_excel_to_pdf_office_all_sheets_landscape(in_path, out_pdf)
        elif kind == "ppt":
            convert_powerpoint_to_pdf_office(in_path, out_pdf)
        else:
            raise RuntimeError("Tip necunoscut.")
        return
    except Exception as e:
        last_err = e

    # Fallback
    try:
        soffice_convert_to_pdf(in_path, out_pdf)
        return
    except Exception as e2:
        raise RuntimeError(f"Conversia a eșuat.\n\nOffice error: {last_err}\n\nLibreOffice error: {e2}")


# ------------------ Images -> PDF ------------------
'''
def images_to_pdf(image_paths: List[str], out_pdf: str) -> None:
    if not _PIL_OK:
        raise RuntimeError("Lipsește Pillow. Instalează: pip install pillow")
    if not image_paths:
        raise RuntimeError("Nu s-au selectat imagini.")

    # One page per image. Page size equals image size in points (pragmatic, no distortion).
    # We build as PDF pages by converting images to single multi-page PDF via Pillow when possible.
    # Pillow can save multipage PDF directly.
    imgs: List[Image.Image] = []
    for p in image_paths:
        im = Image.open(p)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGB")
        else:
            im = im.convert("RGB")
        imgs.append(im)

    first, rest = imgs[0], imgs[1:]
    first.save(out_pdf, "PDF", resolution=300.0, save_all=True, append_images=rest)
'''
def _white_bg_if_transparent(im: "Image.Image") -> "Image.Image":
    """
    Dacă imaginea are alpha/transparență, o așezăm pe fundal alb.
    """
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        bg.alpha_composite(rgba)
        return bg.convert("RGB")
    return im.convert("RGB")


def _parse_page_size(name: str) -> Optional[tuple]:
    """
    Returnează (width_pt, height_pt) în puncte PDF (1 inch = 72pt).
    Dacă e None => folosim dimensiunea imaginii.
    """
    name = (name or "").strip().upper()
    sizes = {
        "A4": (595.276, 841.890),
        "A3": (841.890, 1190.551),
        "LETTER": (612.0, 792.0),
        "LEGAL": (612.0, 1008.0),
    }
    if name in sizes:
        return sizes[name]
    return None


def _ask_images_pdf_options(parent: tk.Tk) -> Optional[dict]:
    """
    Dialog simplu pentru opțiuni Poze → PDF.
    Returnează dict cu opțiuni sau None dacă user anulează.
    """
    dlg = tk.Toplevel(parent)
    dlg.title("Poze → PDF • Opțiuni")
    dlg.grab_set()
    dlg.resizable(False, False)
    apply_modern_theme(dlg)

    # Vars
    var_resize_to_page = tk.BooleanVar(value=True)
    var_page_size = tk.StringVar(value="A4")
    var_keep_aspect = tk.BooleanVar(value=True)
    var_center = tk.BooleanVar(value=True)
    var_margin_mm = tk.IntVar(value=10)
    var_dpi = tk.IntVar(value=300)
    var_sort_by_name = tk.BooleanVar(value=True)

    def set_state():
        st = "readonly" if var_resize_to_page.get() else "disabled"
        cb_size.configure(state=st)
        chk_aspect.configure(state=("normal" if var_resize_to_page.get() else "disabled"))
        chk_center.configure(state=("normal" if var_resize_to_page.get() else "disabled"))
        sp_margin.configure(state=("normal" if var_resize_to_page.get() else "disabled"))

    wrap = ttk.Frame(dlg, padding=12, style="Card.TFrame")
    wrap.pack(fill=tk.BOTH, expand=True)

    ttk.Label(wrap, text="Setări PDF din poze", style="Header.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

    chk_resize = ttk.Checkbutton(
        wrap,
        text="Redimensionează și așază pe o dimensiune de pagină (recomandat)",
        variable=var_resize_to_page,
        command=set_state
    )
    chk_resize.grid(row=1, column=0, columnspan=3, sticky="w", pady=4)

    ttk.Label(wrap, text="Dimensiune pagină:").grid(row=2, column=0, sticky="e", padx=(0, 8), pady=4)
    cb_size = ttk.Combobox(wrap, textvariable=var_page_size, values=["A4", "A3", "Letter", "Legal"], width=12, state="readonly")
    cb_size.grid(row=2, column=1, sticky="w", pady=4)

    ttk.Label(wrap, text="Margini (mm):").grid(row=3, column=0, sticky="e", padx=(0, 8), pady=4)
    sp_margin = ttk.Spinbox(wrap, from_=0, to=50, textvariable=var_margin_mm, width=6)
    sp_margin.grid(row=3, column=1, sticky="w", pady=4)

    chk_aspect = ttk.Checkbutton(wrap, text="Păstrează proporțiile (fără deformare)", variable=var_keep_aspect)
    chk_aspect.grid(row=4, column=0, columnspan=3, sticky="w", pady=4)

    chk_center = ttk.Checkbutton(wrap, text="Centrează imaginea pe pagină", variable=var_center)
    chk_center.grid(row=5, column=0, columnspan=3, sticky="w", pady=4)

    ttk.Separator(wrap, orient="horizontal").grid(row=6, column=0, columnspan=3, sticky="ew", pady=(10, 10))

    ttk.Label(wrap, text="Alte opțiuni utile").grid(row=7, column=0, columnspan=3, sticky="w", pady=(0, 6))

    chk_sort = ttk.Checkbutton(wrap, text="Sortează imaginile după nume (A→Z)", variable=var_sort_by_name)
    chk_sort.grid(row=8, column=0, columnspan=3, sticky="w", pady=4)

    ttk.Label(wrap, text="DPI export (calitate):").grid(row=9, column=0, sticky="e", padx=(0, 8), pady=4)
    sp_dpi = ttk.Spinbox(wrap, from_=72, to=600, increment=1, textvariable=var_dpi, width=6)
    sp_dpi.grid(row=9, column=1, sticky="w", pady=4)

    # Buttons
    out = {"ok": False}

    def on_ok():
        out["ok"] = True
        dlg.destroy()

    def on_cancel():
        out["ok"] = False
        dlg.destroy()

    btns = ttk.Frame(wrap)
    btns.grid(row=10, column=0, columnspan=3, sticky="e", pady=(12, 0))
    ttk.Button(btns, text="Anulează", command=on_cancel).pack(side=tk.RIGHT, padx=6)
    ttk.Button(btns, text="OK", style="Accent.TButton", command=on_ok).pack(side=tk.RIGHT)

    set_state()
    dlg.wait_window()

    if not out["ok"]:
        return None

    return {
        "resize_to_page": bool(var_resize_to_page.get()),
        "page_size": str(var_page_size.get()),
        "keep_aspect": bool(var_keep_aspect.get()),
        "center": bool(var_center.get()),
        "margin_mm": int(var_margin_mm.get()),
        "dpi": int(var_dpi.get()),
        "sort_by_name": bool(var_sort_by_name.get()),
    }


def images_to_pdf_with_options(image_paths: List[str], out_pdf: str, opts: dict) -> None:
    if not _PIL_OK:
        raise RuntimeError("Lipsește Pillow. Instalează: pip install pillow")
    if not image_paths:
        raise RuntimeError("Nu s-au selectat imagini.")

    if opts.get("sort_by_name", True):
        image_paths = sorted(image_paths, key=lambda p: os.path.basename(p).lower())

    dpi = int(opts.get("dpi", 300))
    resize_to_page = bool(opts.get("resize_to_page", True))
    page_size_name = str(opts.get("page_size", "A4"))
    keep_aspect = bool(opts.get("keep_aspect", True))
    center = bool(opts.get("center", True))
    margin_mm = int(opts.get("margin_mm", 10))

    # conversie mm -> points
    margin_pt = margin_mm * 72.0 / 25.4

    page_pt = _parse_page_size(page_size_name) if resize_to_page else None

    imgs: List[Image.Image] = []
    for p in image_paths:
        im = Image.open(p)
        im = _white_bg_if_transparent(im)

        if page_pt:
            pw, ph = page_pt
            # canvas alb la dimensiunea paginii
            canvas = Image.new("RGB", (int(round(pw)), int(round(ph))), (255, 255, 255))

            # zona disponibilă după margini
            avail_w = max(1, int(round(pw - 2 * margin_pt)))
            avail_h = max(1, int(round(ph - 2 * margin_pt)))

            src_w, src_h = im.size

            if keep_aspect:
                scale = min(avail_w / src_w, avail_h / src_h)
                new_w = max(1, int(round(src_w * scale)))
                new_h = max(1, int(round(src_h * scale)))
            else:
                new_w, new_h = avail_w, avail_h

            im_resized = im.resize((new_w, new_h), Image.LANCZOS)

            if center:
                x = int(round((pw - new_w) / 2))
                y = int(round((ph - new_h) / 2))
            else:
                x = int(round(margin_pt))
                y = int(round(margin_pt))

            canvas.paste(im_resized, (x, y))
            imgs.append(canvas)
        else:
            # fără resize: păstrăm dimensiunea imaginii, dar sigur fundal alb
            imgs.append(im)

    first, rest = imgs[0], imgs[1:]
    first.save(out_pdf, "PDF", resolution=float(dpi), save_all=True, append_images=rest)

   

# ------------------ Styling ------------------

def apply_modern_theme(root: tk.Tk):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    root.configure(bg=THEME['BG_MAIN'])
    style.configure("TFrame", background=THEME['BG_MAIN'])
    style.configure("Card.TFrame", background=THEME['BG_CARD'])
    style.configure("TLabel", background=THEME['BG_MAIN'], foreground=THEME['FG_TEXT'], font=("Segoe UI", 10))
    style.configure("Muted.TLabel", background=THEME['BG_MAIN'], foreground=THEME['FG_MUTED'])
    style.configure("Header.TLabel", background=THEME['BG_MAIN'], foreground=THEME['FG_TEXT'], font=("Segoe UI", 16, "bold"))
    style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 6))
    style.map("Accent.TButton",
              background=[("active", THEME['ACCENT']), ("!active", THEME['ACCENT'])],
              foreground=[("active", "white"), ("!active", "white")])
    style.configure("TButton", font=("Segoe UI", 10), padding=(10, 6))
    style.map("TButton",
              background=[("active", "#263143")],
              foreground=[("active", THEME['FG_TEXT'])])
    style.configure("TEntry", fieldbackground=THEME['BG_MAIN'], foreground=THEME['FG_TEXT'])
    style.configure("Horizontal.TSeparator", background="#202733")
    style.configure("TProgressbar", troughcolor=THEME['BG_CARD'], background=THEME['ACCENT'],
                    bordercolor=THEME['BG_CARD'], lightcolor=THEME['ACCENT'], darkcolor=THEME['ACCENT'])


def try_set_windows_dark_titlebar(win: tk.Tk):
    if platform.system() != "Windows":
        return
    try:
        hwnd = win.winfo_id()
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.wintypes.HWND(hwnd),
            ctypes.wintypes.DWORD(DWMWA_USE_IMMERSIVE_DARK_MODE),
            ctypes.byref(value),
            ctypes.sizeof(value)
        )
    except Exception:
        try:
            DWMWA_USE_IMMERSIVE_DARK_MODE = 19
            hwnd = win.winfo_id()
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.wintypes.HWND(hwnd),
                ctypes.wintypes.DWORD(DWMWA_USE_IMMERSIVE_DARK_MODE),
                ctypes.byref(value),
                ctypes.sizeof(value)
            )
        except Exception:
            pass


# ------------------ Base App ------------------

class PDFMixerBase:
    def __init__(self):
        self.status = tk.StringVar(value="Gata.")
        self._busy_visible = False

    # ---- Menubar clasic (OS bar sus) ----
    def build_menubar(self):
        menubar = tk.Menu(self)

        # Fișier
        m_file = tk.Menu(menubar, tearoff=0)
        m_file.add_command(label="Adaugă PDF-uri...", command=self.add_files, accelerator="Ctrl+O")
        m_file.add_separator()
        m_file.add_command(label="Ieșire", command=self.quit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="Fișier", menu=m_file)

        # Convert
        m_conv = tk.Menu(menubar, tearoff=0)
        m_conv.add_command(label="PowerPoint → PDF...", command=self.convert_ppt_dialog)
        m_conv.add_command(label="Excel → PDF (all sheets)...", command=self.convert_excel_dialog)
        m_conv.add_command(label="Word → PDF...", command=self.convert_word_dialog)
        m_conv.add_separator()
        m_conv.add_command(label="Poze → PDF...", command=self.images_to_pdf_dialog)
        menubar.add_cascade(label="Convert", menu=m_conv)

        # Unelte
        m_tools = tk.Menu(menubar, tearoff=0)
        m_tools.add_command(label="Unește în serie", command=self.merge_serial)
        m_tools.add_command(label="Intercalează (2 PDF-uri)", command=self.open_interleave_dialog)
        m_tools.add_separator()
        m_tools.add_command(label="Extrage pagini...", command=self.extract_pages_dialog)
        m_tools.add_command(label="Șterge pagini...", command=self.delete_pages_dialog)
        m_tools.add_command(label="Rotire pagini...", command=self.rotate_pages_dialog)
        m_tools.add_command(label="Inversează paginile (descrescător)", command=self.reverse_pages_dialog)
        m_tools.add_command(label="Split din N în N pagini...", command=self.split_every_dialog)
        menubar.add_cascade(label="Unelte", menu=m_tools)

        # Aspect
        m_view = tk.Menu(menubar, tearoff=0)
        m_view.add_command(label="Dark Indigo", command=lambda: self.switch_palette("indigo"))
        m_view.add_command(label="Dark Teal", command=lambda: self.switch_palette("teal"))
        m_view.add_command(label="Dark Amber", command=lambda: self.switch_palette("amber"))
        menubar.add_cascade(label="Aspect", menu=m_view)

        # Ajutor
        m_help = tk.Menu(menubar, tearoff=0)
        m_help.add_command(label="Despre…", command=self.show_about)
        menubar.add_cascade(label="Ajutor", menu=m_help)

        self.config(menu=menubar)

        # Shortcuts
        self.bind_all("<Control-o>", lambda e: self.add_files())
        self.bind_all("<Control-q>", lambda e: self.quit())

    def switch_palette(self, name: str):
        global CURRENT_PALETTE_NAME, THEME
        if name not in PALETTES:
            return
        CURRENT_PALETTE_NAME = name
        THEME = PALETTES[name]
        apply_modern_theme(self)

    def build_layout(self, dnd: bool):
        apply_modern_theme(self)
        try_set_windows_dark_titlebar(self)

        # Header minimal (fără titlu duplicat)
        header = ttk.Frame(self, padding=(16, 10))
        header.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(header, text=f"{BRAND_COMPANY}  |  © {COPYRIGHT_YEAR} {BRAND_AUTHOR}", style="Muted.TLabel").pack(anchor="w")

        # Divider
        ttk.Separator(self, orient="horizontal").pack(fill=tk.X, padx=0, pady=(0, 6))

        # Top toolbar (card)
        toolbar = ttk.Frame(self, padding=10, style="Card.TFrame")
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(0, 10))
        self.btn_add = ttk.Button(toolbar, text="➕ Adaugă PDF-uri", style="Accent.TButton", command=self.add_files)
        self.btn_remove = ttk.Button(toolbar, text="🗑️ Șterge din listă", command=self.remove_selected)
        self.btn_up = ttk.Button(toolbar, text="⬆️ Sus", command=lambda: self.move_selected(-1))
        self.btn_down = ttk.Button(toolbar, text="⬇️ Jos", command=lambda: self.move_selected(1))
        self.btn_clear = ttk.Button(toolbar, text="🧹 Golește lista", command=self.clear_list)
        self.btn_sort_desc = ttk.Button(toolbar, text="🔽 Sortează lista (Z→A)", command=self.sort_list_desc)
        for w in (self.btn_add, self.btn_remove, self.btn_up, self.btn_down, self.btn_clear, self.btn_sort_desc):
            w.pack(side=tk.LEFT, padx=6)

        Tooltip(self.btn_add, "Adaugă PDF-uri din disc sau trage-le în fereastră.")
        Tooltip(self.btn_remove, "Șterge din listă PDF-urile selectate (nu din disc).")
        Tooltip(self.btn_up, "Mută în sus PDF-ul selectat.")
        Tooltip(self.btn_down, "Mută în jos PDF-ul selectat.")
        Tooltip(self.btn_clear, "Golește lista (nu afectează fișierele reale).")
        Tooltip(self.btn_sort_desc, "Sortează descrescător (Z→A) după nume.")

        # Center panel
        center = ttk.Frame(self, padding=6)
        center.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        left = ttk.Frame(center)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        hint_text = "Trage & plasează PDF-uri aici (sau foldere) • se adaugă automat" if dnd else \
                    "Adaugă PDF-uri cu butonul sau instalează 'tkinterdnd2' pentru drag & drop."
        ttk.Label(left, text=hint_text, style="Muted.TLabel").pack(anchor="w", pady=(0, 6))

        list_wrap = ttk.Frame(left, padding=8, style="Card.TFrame")
        list_wrap.pack(fill=tk.BOTH, expand=True)
        self.listbox = tk.Listbox(list_wrap, selectmode=tk.EXTENDED, activestyle="dotbox",
                                  bg=THEME['BG_MAIN'], fg=THEME['FG_TEXT'], relief=tk.FLAT, highlightthickness=0)
        self.listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.scroll = ttk.Scrollbar(list_wrap, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=self.scroll.set)
        self.scroll.pack(side=tk.RIGHT, fill=tk.Y)
        Tooltip(self.listbox, "Ordinea din listă = ordinea la \"Unește în serie\".")

        if dnd:
            self.drop_target_register(DND_FILES)           # type: ignore
            self.dnd_bind('<<Drop>>', self._on_drop_files) # type: ignore
            self.listbox.drop_target_register(DND_FILES)   # type: ignore
            self.listbox.dnd_bind('<<Drop>>', self._on_drop_files)  # type: ignore

        right = ttk.Frame(center)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=(12, 0))

        ttk.Label(right, text="Acțiuni rapide").pack(anchor="w")
        self.btn_merge = ttk.Button(right, text="📚 Unește în serie (n PDF-uri)", command=self.merge_serial)
        self.btn_interleave = ttk.Button(right, text="🔀 Intercalează (2 PDF-uri)", command=self.open_interleave_dialog)
        self.btn_extract = ttk.Button(right, text="✂️ Extrage pagini...", command=self.extract_pages_dialog)
        self.btn_delete = ttk.Button(right, text="🧽 Șterge pagini...", command=self.delete_pages_dialog)
        self.btn_rotate = ttk.Button(right, text="🔄 Rotire pagini...", command=self.rotate_pages_dialog)
        self.btn_reverse = ttk.Button(right, text="↕️ Inversează paginile (descrescător)", command=self.reverse_pages_dialog)
        self.btn_split_every = ttk.Button(right, text="🍰 Split la fiecare N pagini...", command=self.split_every_dialog)
        for w in (self.btn_merge, self.btn_interleave, self.btn_extract, self.btn_delete, self.btn_rotate, self.btn_reverse, self.btn_split_every):
            w.pack(fill=tk.X, pady=5)

        ttk.Separator(right, orient="horizontal").pack(fill=tk.X, pady=(10, 8))
        ttk.Label(right, text="Convert rapid").pack(anchor="w")
        self.btn_conv_ppt = ttk.Button(right, text="🖥️ PowerPoint → PDF", command=self.convert_ppt_dialog)
        self.btn_conv_xls = ttk.Button(right, text="📊 Excel → PDF", command=self.convert_excel_dialog)
        self.btn_conv_doc = ttk.Button(right, text="📝 Word → PDF", command=self.convert_word_dialog)
        self.btn_conv_img = ttk.Button(right, text="🖼️ Poze → PDF", command=self.images_to_pdf_dialog)
        for w in (self.btn_conv_ppt, self.btn_conv_xls, self.btn_conv_doc, self.btn_conv_img):
            w.pack(fill=tk.X, pady=5)

        Tooltip(self.btn_merge, "Unește toate PDF-urile din listă în ordinea curentă.")
        Tooltip(self.btn_interleave, "Intercalează două PDF-uri după reguli: alternativ, impare/pare etc.")
        Tooltip(self.btn_extract, "Extrage doar paginile alese (ex: 1-3,5,10).")
        Tooltip(self.btn_delete, "Șterge din PDF paginile indicate și salvează rezultatul.")
        Tooltip(self.btn_rotate, "Rotește pagini cu 90/180/270°.")
        Tooltip(self.btn_reverse, "Creează un PDF cu paginile în ordine inversă.")
        Tooltip(self.btn_split_every, "Împarte PDF-ul în fișiere de câte N pagini.")
        Tooltip(self.btn_conv_ppt, "Exportă prezentări în PDF (în background).")
        Tooltip(self.btn_conv_xls, "Exportă Excel în PDF (toate sheet-urile, landscape).")
        Tooltip(self.btn_conv_doc, "Exportă documente Word în PDF (respectă formatul paginii).")
        Tooltip(self.btn_conv_img, "Creează un PDF din mai multe poze (o pagină per poză).")

        # Onboarding wizard (when list is empty)
        self.wizard = ttk.Frame(left, padding=16, style="Card.TFrame")
        wtitle = ttk.Label(self.wizard, text="Începe în 3 pași", style="Header.TLabel")
        w1 = ttk.Label(self.wizard, text="1) Adaugă PDF-uri (butonul ➕ sau drag & drop)")
        w2 = ttk.Label(self.wizard, text="2) Opțional: rearanjează / sortează lista")
        w3 = ttk.Label(self.wizard, text="3) Alege acțiunea: Unește / Intercalează / etc.")
        for w in (wtitle, w1, w2, w3):
            w.pack(anchor="w", pady=2)
        self._toggle_wizard()
        self.listbox.bind("<KeyRelease>", lambda e: self._toggle_wizard())
        self.listbox.bind("<ButtonRelease>", lambda e: self._toggle_wizard())

        # Status bar (with hidden, non-modal progressbar)
        status_bar = ttk.Frame(self, style="Card.TFrame")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=10)
        self.lbl_status = ttk.Label(status_bar, textvariable=self.status, anchor="w")
        self.lbl_status.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.progress = ttk.Progressbar(status_bar, mode="indeterminate", length=160)
        self.progress.pack(side=tk.RIGHT)
        self.progress.pack_forget()  # hidden by default

    def _toggle_wizard(self):
        if self.listbox.size() == 0:
            self.wizard.pack(fill=tk.X, pady=10)
        else:
            self.wizard.pack_forget()

    # Non-modal progress helpers
    def _busy_on(self):
        if not self._busy_visible:
            self.progress.pack(side=tk.RIGHT)
            self.progress.start(12)
            self._busy_visible = True
            self.update_idletasks()

    def _busy_off(self):
        if self._busy_visible:
            self.progress.stop()
            self.progress.pack_forget()
            self._busy_visible = False
            self.update_idletasks()

    # ---- Menus ----
    def show_about(self):
        engine = "Office COM" if _HAS_WIN32 else "LibreOffice fallback only"
        text = (
            f"{APP_NAME} v{APP_VERSION}\n"
            f"{BRAND_COMPANY}\n\n"
            f"Autor: {BRAND_AUTHOR}\n"
            f"© {COPYRIGHT_YEAR} {BRAND_AUTHOR}. Toate drepturile rezervate.\n\n"
            f"Convert Engine: {engine}\n"
            "Convert Fallback: LibreOffice (soffice)\n\n"
            "Oracolul:\n"
            "Și se va scula unul din voi,\n"
            "Și se va răsuci spre voi,\n"
            "Și va vrea să deschidă caseta străveche,\n"
            "Iar pălăria lui,\n"
            "Roșie sau albastră va fi,\n"
            "Sau altă parte a hainelor sale,\n"
            "Împodobit cu semnele nopții:\n"
            "Lună sau stele!\n"
            "Și va fi cunoscut ca\n"
            "Cel-care-ATâT-de-Groaznic-se-Înfurie!\n\n"
            "Nm... Nm...\n"
            "Zafali!\n"
            "F-fântâna magică începe să se usuce!\n"
            "Z-zali!\n"
            "P-păsările sunt disperate!\n"
            "Și ceea ce de veacuri a fost o bucată de gheață,\n"
            "Se preface în apă!\n"
            "Piatra până acum tăcută,\n"
            "Începe să vorbească!\n"
            "Și din cer cade o ploaie de broaște!\n"
            "Și astfel, Țara Vrăjilor se va prăbuși în prăpastie...\n\n"
            "Acum sosește Babole!\n"
            "Câinele din Stele!\n"
            "Și vă revine speranța!\n"
            "Și mă duc cu...\n"
            "Cârtița la piață! Și...\n"
            "Numărul de lebede albe...\n"
            "Azali...\n"
            "Ne revine a treia parte...\n\n"
            "Acest software este furnizat ‘ca atare’, fără garanții."
        )
        messagebox.showinfo("Despre", text)


    # ---------- List management ----------
    def add_files(self):
        paths = filedialog.askopenfilenames(title="Alege PDF-uri", filetypes=[("PDF files", "*.pdf")])
        if not paths:
            return
        for p in paths:
            self.listbox.insert(tk.END, p)
        self._toggle_wizard()
        self.status.set(f"Am adăugat {len(paths)} fișier(e).")

    def sort_list_desc(self):
        items = list(self.listbox.get(0, tk.END))
        items.sort(key=lambda p: os.path.basename(p).lower(), reverse=True)
        self.listbox.delete(0, tk.END)
        for p in items:
            self.listbox.insert(tk.END, p)
        self.status.set("Lista a fost sortată descrescător (Z→A).")

    def selected_indices(self) -> List[int]:
        return list(self.listbox.curselection())

    def remove_selected(self):
        idxs = self.selected_indices()
        if not idxs:
            return
        for i in reversed(idxs):
            self.listbox.delete(i)
        self._toggle_wizard()
        self.status.set(f"Am eliminat {len(idxs)} element(e).")

    def move_selected(self, direction: int):
        idxs = self.selected_indices()
        if not idxs:
            return
        # Move in correct order to avoid index shifting issues
        rng = idxs if direction < 0 else list(reversed(idxs))
        for i in rng:
            new_i = i + direction
            if 0 <= new_i < self.listbox.size():
                text = self.listbox.get(i)
                self.listbox.delete(i)
                self.listbox.insert(new_i, text)
                self.listbox.selection_set(new_i)
        self.status.set("Rearanjat.")

    def clear_list(self):
        self.listbox.delete(0, tk.END)
        self._toggle_wizard()
        self.status.set("Lista a fost golită.")

    # ---------- Convert dialogs ----------
    def _ask_output_folder(self) -> Optional[str]:
        return filedialog.askdirectory(title="Alege folderul de output pentru PDF-uri")

    def convert_ppt_dialog(self):
        paths = filedialog.askopenfilenames(
            title="Alege prezentări PowerPoint",
            filetypes=[
                ("PowerPoint", "*.ppt;*.pptx;*.pps;*.ppsx;*.pot;*.potx"),
                ("All files", "*.*")
            ],
        )
        if not paths:
            return
        out_dir = self._ask_output_folder()
        if not out_dir:
            return

        self._busy_on()
        try:
            ok = 0
            for in_path in paths:
                base = os.path.splitext(os.path.basename(in_path))[0]
                tmp_pdf = os.path.join(out_dir, base + ".__tmp__.pdf")
                final_pdf = os.path.join(out_dir, base + ".pdf")

                convert_office_doc_to_pdf(in_path, tmp_pdf, kind="ppt")
                sanitize_pdf_no_metadata(tmp_pdf, final_pdf)
                try:
                    os.remove(tmp_pdf)
                except Exception:
                    pass

                ok += 1
                self.status.set(f"PowerPoint → PDF: {ok}/{len(paths)}")
                self.update_idletasks()

            self.status.set(f"Conversie PPT → PDF completă: {ok} fișier(e).")
            messagebox.showinfo(APP_NAME, f"Conversie completă: {ok} fișier(e).")
        except Exception as e:
            messagebox.showerror("Eroare conversie PowerPoint", str(e))
        finally:
            self._busy_off()

    def convert_excel_dialog(self):
        paths = filedialog.askopenfilenames(
            title="Alege fișiere Excel",
            filetypes=[
                ("Excel", "*.xls;*.xlsx;*.xlsm;*.xlsb;*.xlt;*.xltx;*.csv"),
                ("All files", "*.*")
            ],
        )
        if not paths:
            return
        out_dir = self._ask_output_folder()
        if not out_dir:
            return

        # Option: force landscape via post-rotate (useful if fallback/odd templates)
        force_landscape = messagebox.askyesno(
            "Excel → PDF",
            "Vrei să forțez landscape (auto-rotate paginile portrait) după export?\n\nRecomandat: DA"
        )

        self._busy_on()
        try:
            ok = 0
            for in_path in paths:
                base = os.path.splitext(os.path.basename(in_path))[0]
                tmp_pdf = os.path.join(out_dir, base + ".__tmp__.pdf")
                mid_pdf = os.path.join(out_dir, base + ".__mid__.pdf")
                final_pdf = os.path.join(out_dir, base + ".pdf")

                convert_office_doc_to_pdf(in_path, tmp_pdf, kind="excel")

                if force_landscape:
                    auto_rotate_pdf_pages_to_landscape(tmp_pdf, mid_pdf)
                    sanitize_pdf_no_metadata(mid_pdf, final_pdf)
                else:
                    sanitize_pdf_no_metadata(tmp_pdf, final_pdf)

                for p in (tmp_pdf, mid_pdf):
                    try:
                        if os.path.exists(p):
                            os.remove(p)
                    except Exception:
                        pass

                ok += 1
                self.status.set(f"Excel → PDF: {ok}/{len(paths)}")
                self.update_idletasks()

            self.status.set(f"Conversie Excel → PDF completă: {ok} fișier(e).")
            messagebox.showinfo(APP_NAME, f"Conversie completă: {ok} fișier(e).")
        except Exception as e:
            messagebox.showerror("Eroare conversie Excel", str(e))
        finally:
            self._busy_off()

    def convert_word_dialog(self):
        paths = filedialog.askopenfilenames(
            title="Alege documente Word",
            filetypes=[
                ("Word", "*.doc;*.docx;*.docm;*.rtf"),
                ("All files", "*.*")
            ],
        )
        if not paths:
            return
        out_dir = self._ask_output_folder()
        if not out_dir:
            return

        self._busy_on()
        try:
            ok = 0
            for in_path in paths:
                base = os.path.splitext(os.path.basename(in_path))[0]
                tmp_pdf = os.path.join(out_dir, base + ".__tmp__.pdf")
                final_pdf = os.path.join(out_dir, base + ".pdf")

                convert_office_doc_to_pdf(in_path, tmp_pdf, kind="word")
                sanitize_pdf_no_metadata(tmp_pdf, final_pdf)
                try:
                    os.remove(tmp_pdf)
                except Exception:
                    pass

                ok += 1
                self.status.set(f"Word → PDF: {ok}/{len(paths)}")
                self.update_idletasks()

            self.status.set(f"Conversie Word → PDF completă: {ok} fișier(e).")
            messagebox.showinfo(APP_NAME, f"Conversie completă: {ok} fișier(e).")
        except Exception as e:
            messagebox.showerror("Eroare conversie Word", str(e))
        finally:
            self._busy_off()

    def images_to_pdf_dialog(self):
        paths = filedialog.askopenfilenames(
            title="Alege poze (una sau mai multe)",
            filetypes=[
                ("Images", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tif;*.tiff"),
                ("All files", "*.*")
            ],
        )
        if not paths:
            return

        opts = _ask_images_pdf_options(self)
        if opts is None:
            return

        out_path = ask_save_as("images.pdf")
        if not out_path:
            return

        self._busy_on()
        try:
            tmp_pdf = out_path.replace(".pdf", ".__tmp__.pdf")
            images_to_pdf_with_options(list(paths), tmp_pdf, opts)
            sanitize_pdf_no_metadata(tmp_pdf, out_path)
            try:
                os.remove(tmp_pdf)
            except Exception:
                pass

            self.status.set(f"PDF creat din {len(paths)} imagine(i).")
            messagebox.showinfo(APP_NAME, f"PDF salvat:\n{out_path}")
        except Exception as e:
            messagebox.showerror("Eroare poze → PDF", str(e))
        finally:
            self._busy_off()


    # ---------- Actions (with non-modal progress) ----------
    def merge_serial(self):
        items = self.listbox.get(0, tk.END)
        if not items:
            messagebox.showwarning("Atenție", "Adaugă cel puțin un PDF.")
            return
        out_path = ask_save_as("merged.pdf")
        if not out_path:
            return
        self._busy_on()
        try:
            writer = PdfWriter(); total = 0
            for path in items:
                reader = safe_open_reader(path)
                if not reader:
                    return
                for page in reader.pages:
                    writer.add_page(page)
                    total += 1
                    if total % 8 == 0:
                        self.update_idletasks()
            with open(out_path, "wb") as f:
                writer.write(f)

            # Keep "NO-METADATA" policy (resave pages only)
            tmp2 = out_path.replace(".pdf", ".__tmp__.pdf")
            try:
                os.replace(out_path, tmp2)
                sanitize_pdf_no_metadata(tmp2, out_path)
                os.remove(tmp2)
            except Exception:
                # if anything fails, still keep the merged PDF as-is
                try:
                    if os.path.exists(tmp2):
                        os.replace(tmp2, out_path)
                except Exception:
                    pass

            self.status.set(f"Succes! Am salvat {total} pagini în {os.path.basename(out_path)}.")
            messagebox.showinfo(APP_NAME, f"PDF salvat:\n{out_path}")
        except Exception as e:
            messagebox.showerror("Eroare la salvare", str(e))
        finally:
            self._busy_off()

    def open_interleave_dialog(self):
        items = self.listbox.get(0, tk.END)
        if len(items) < 2:
            messagebox.showwarning("Atenție", "Adaugă cel puțin două PDF-uri.")
            return
        dlg = tk.Toplevel(self)
        dlg.title("Intercalare pagini")
        dlg.grab_set()
        dlg.resizable(False, False)
        apply_modern_theme(dlg)

        ttk.Label(dlg, text="Alege cele două PDF-uri pentru intercalare:").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 4)
        )
        varA = tk.StringVar(value=items[0])
        varB = tk.StringVar(value=items[1])
        cbA = ttk.Combobox(dlg, textvariable=varA, values=list(items), state="readonly", width=60)
        cbB = ttk.Combobox(dlg, textvariable=varB, values=list(items), state="readonly", width=60)
        ttk.Label(dlg, text="PDF A:").grid(row=1, column=0, sticky="e", padx=8, pady=2)
        cbA.grid(row=1, column=1, sticky="w", padx=8, pady=2)
        ttk.Label(dlg, text="PDF B:").grid(row=2, column=0, sticky="e", padx=8, pady=2)
        cbB.grid(row=2, column=1, sticky="w", padx=8, pady=2)

        ttk.Label(dlg, text="Mod intercalare:").grid(row=3, column=0, sticky="e", padx=8, pady=(8, 2))
        mode = tk.StringVar(value="alternate")
        modes = [
            ("Alternativ (A1,B1,A2,B2)", "alternate"),
            ("A impare + B pare", "a_odd_b_even"),
            ("A pare + B impare", "a_even_b_odd"),
            ("Doar impare din A", "a_odd"),
            ("Doar pare din B", "b_even"),
        ]
        frm_modes = ttk.Frame(dlg)
        frm_modes.grid(row=3, column=1, sticky="w", padx=8, pady=(8, 2))
        for text, val in modes:
            ttk.Radiobutton(frm_modes, text=text, value=val, variable=mode).pack(anchor="w")

        ttk.Label(dlg, text="Paginare începe de la (1-based):").grid(row=4, column=0, sticky="e", padx=8, pady=2)
        start_from = tk.IntVar(value=1)
        ttk.Spinbox(dlg, from_=1, to=99999, textvariable=start_from, width=6).grid(
            row=4, column=1, sticky="w", padx=8, pady=2
        )

        btns = ttk.Frame(dlg)
        btns.grid(row=5, column=0, columnspan=2, sticky="e", padx=8, pady=8)
        ttk.Button(btns, text="Anulează", command=dlg.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(
            btns,
            text="OK",
            command=lambda: (self._busy_on(), self._do_interleave(varA.get(), varB.get(), mode.get(), start_from.get(), dlg), self._busy_off()),
        ).pack(side=tk.RIGHT)

    def _do_interleave(self, path_a: str, path_b: str, mode: str, start_from: int, dlg: tk.Toplevel):
        reader_a = safe_open_reader(path_a)
        reader_b = safe_open_reader(path_b)
        if not reader_a or not reader_b:
            return
        out_path = ask_save_as("interleaved.pdf")
        if not out_path:
            return
        writer = PdfWriter()

        def is_odd(i1: int) -> bool:
            return i1 % 2 == 1

        pa, pb = len(reader_a.pages), len(reader_b.pages)
        ia = ib = start_from - 1
        if mode == "alternate":
            while ia < pa or ib < pb:
                if ia < pa:
                    writer.add_page(reader_a.pages[ia]); ia += 1
                if ib < pb:
                    writer.add_page(reader_b.pages[ib]); ib += 1
        elif mode == "a_odd_b_even":
            for i in range(start_from, max(pa, pb) + 1):
                if i <= pa and is_odd(i):
                    writer.add_page(reader_a.pages[i - 1])
                if i <= pb and not is_odd(i):
                    writer.add_page(reader_b.pages[i - 1])
        elif mode == "a_even_b_odd":
            for i in range(start_from, max(pa, pb) + 1):
                if i <= pa and not is_odd(i):
                    writer.add_page(reader_a.pages[i - 1])
                if i <= pb and is_odd(i):
                    writer.add_page(reader_b.pages[i - 1])
        elif mode == "a_odd":
            for i in range(start_from, pa + 1):
                if is_odd(i):
                    writer.add_page(reader_a.pages[i - 1])
        elif mode == "b_even":
            for i in range(start_from, pb + 1):
                if not is_odd(i):
                    writer.add_page(reader_b.pages[i - 1])
        else:
            messagebox.showerror("Eroare", "Mod necunoscut.")
            return

        with open(out_path, "wb") as f:
            writer.write(f)

        # sanitize output
        tmp2 = out_path.replace(".pdf", ".__tmp__.pdf")
        try:
            os.replace(out_path, tmp2)
            sanitize_pdf_no_metadata(tmp2, out_path)
            os.remove(tmp2)
        except Exception:
            try:
                if os.path.exists(tmp2):
                    os.replace(tmp2, out_path)
            except Exception:
                pass

        dlg.destroy()
        self.status.set(f"Intercalare reușită. Am salvat {os.path.basename(out_path)}.")
        messagebox.showinfo(APP_NAME, f"PDF salvat:\n{out_path}")

    def extract_pages_dialog(self):
        items = self.listbox.get(0, tk.END)
        if not items:
            messagebox.showwarning("Atenție", "Adaugă cel puțin un PDF și selectează-l.")
            return
        sel = self.selected_indices()
        if len(sel) != 1:
            messagebox.showwarning("Atenție", "Selectează un singur PDF din listă pentru a extrage pagini.")
            return
        path = items[sel[0]]
        reader = safe_open_reader(path)
        if not reader:
            return
        total = len(reader.pages)
        ranges = simpledialog.askstring("Extrage pagini", f"Introdu intervale (1-based), ex: 1-3,5,7-9\nTotal pagini: {total}")
        if ranges is None:
            return
        idxs = parse_page_ranges(ranges, total)
        if not idxs:
            messagebox.showwarning("Atenție", "Nu s-a specificat niciun interval valid.")
            return
        out_path = ask_save_as(f"extract_{os.path.basename(path)}")
        if not out_path:
            return
        self._busy_on()
        try:
            writer = PdfWriter()
            for j, i in enumerate(idxs):
                writer.add_page(reader.pages[i])
                if j % 8 == 0:
                    self.update_idletasks()
            with open(out_path, "wb") as f:
                writer.write(f)

            tmp2 = out_path.replace(".pdf", ".__tmp__.pdf")
            try:
                os.replace(out_path, tmp2)
                sanitize_pdf_no_metadata(tmp2, out_path)
                os.remove(tmp2)
            except Exception:
                try:
                    if os.path.exists(tmp2):
                        os.replace(tmp2, out_path)
                except Exception:
                    pass

            self.status.set(f"Extras cu succes {len(idxs)} pagini.")
            messagebox.showinfo(APP_NAME, f"PDF salvat:\n{out_path}")
        finally:
            self._busy_off()

    def delete_pages_dialog(self):
        items = self.listbox.get(0, tk.END)
        if not items:
            messagebox.showwarning("Atenție", "Adaugă cel puțin un PDF și selectează-l.")
            return
        sel = self.selected_indices()
        if len(sel) != 1:
            messagebox.showwarning("Atenție", "Selectează un singur PDF din listă pentru a șterge pagini.")
            return
        path = items[sel[0]]
        reader = safe_open_reader(path)
        if not reader:
            return
        total = len(reader.pages)
        ranges = simpledialog.askstring("Șterge pagini", f"Introdu intervale (1-based) de șters, ex: 2,5-7\nTotal pagini: {total}")
        if ranges is None:
            return
        to_delete = set(parse_page_ranges(ranges, total))
        if not to_delete:
            messagebox.showwarning("Atenție", "Nu s-a specificat niciun interval valid.")
            return
        out_path = ask_save_as(f"deleted_{os.path.basename(path)}")
        if not out_path:
            return
        self._busy_on()
        try:
            writer = PdfWriter()
            kept = 0
            for i in range(total):
                if i not in to_delete:
                    writer.add_page(reader.pages[i]); kept += 1
                    if kept % 8 == 0:
                        self.update_idletasks()
            with open(out_path, "wb") as f:
                writer.write(f)

            tmp2 = out_path.replace(".pdf", ".__tmp__.pdf")
            try:
                os.replace(out_path, tmp2)
                sanitize_pdf_no_metadata(tmp2, out_path)
                os.remove(tmp2)
            except Exception:
                try:
                    if os.path.exists(tmp2):
                        os.replace(tmp2, out_path)
                except Exception:
                    pass

            self.status.set(f"Am șters {len(to_delete)} pagini. Păstrate {kept}.")
            messagebox.showinfo(APP_NAME, f"PDF salvat:\n{out_path}")
        finally:
            self._busy_off()

    def rotate_pages_dialog(self):
        items = self.listbox.get(0, tk.END)
        if not items:
            messagebox.showwarning("Atenție", "Adaugă cel puțin un PDF și selectează-l.")
            return
        sel = self.selected_indices()
        if len(sel) != 1:
            messagebox.showwarning("Atenție", "Selectează un singur PDF din listă pentru rotire.")
            return
        path = items[sel[0]]
        reader = safe_open_reader(path)
        if not reader:
            return
        total = len(reader.pages)

        dlg = tk.Toplevel(self)
        dlg.title("Rotire pagini")
        dlg.grab_set()
        dlg.resizable(False, False)
        apply_modern_theme(dlg)

        ttk.Label(dlg, text=f"Fișier: {os.path.basename(path)} – {total} pagini").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 4)
        )
        ttk.Label(dlg, text="Grade (90 / 180 / 270):").grid(row=1, column=0, sticky="e", padx=8, pady=2)
        var_deg = tk.IntVar(value=90)
        ttk.Spinbox(dlg, from_=0, to=359, textvariable=var_deg, width=6).grid(row=1, column=1, sticky="w", padx=8, pady=2)

        ttk.Label(dlg, text="Intervale (opțional):").grid(row=2, column=0, sticky="e", padx=8, pady=2)
        var_ranges = tk.StringVar(value="")
        ttk.Entry(dlg, textvariable=var_ranges, width=40).grid(row=2, column=1, sticky="w", padx=8, pady=2)
        ttk.Label(dlg, text="Ex: 1-3,5,10").grid(row=3, column=1, sticky="w", padx=8, pady=(0, 8))

        btns = ttk.Frame(dlg)
        btns.grid(row=4, column=0, columnspan=2, sticky="e", padx=8, pady=8)
        ttk.Button(btns, text="Anulează", command=dlg.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="OK", command=lambda: (self._busy_on(), self._do_rotate(path, var_deg.get(), var_ranges.get(), dlg), self._busy_off())).pack(side=tk.RIGHT)

    def _do_rotate(self, path: str, degrees: int, ranges: str, dlg: tk.Toplevel):
        reader = safe_open_reader(path)
        if not reader:
            return
        total = len(reader.pages)
        idxs = parse_page_ranges(ranges, total) if ranges.strip() else list(range(total))

        out_path = ask_save_as(f"rotated_{os.path.basename(path)}")
        if not out_path:
            return

        writer = PdfWriter()
        idx_set = set(idxs)
        for i in range(total):
            page = reader.pages[i]
            if i in idx_set:
                rotate_page(page, degrees)
            writer.add_page(page)
            if i % 8 == 0:
                self.update_idletasks()

        with open(out_path, "wb") as f:
            writer.write(f)

        tmp2 = out_path.replace(".pdf", ".__tmp__.pdf")
        try:
            os.replace(out_path, tmp2)
            sanitize_pdf_no_metadata(tmp2, out_path)
            os.remove(tmp2)
        except Exception:
            try:
                if os.path.exists(tmp2):
                    os.replace(tmp2, out_path)
            except Exception:
                pass

        dlg.destroy()
        self.status.set(f"Rotire reușită. PDF salvat: {os.path.basename(out_path)}.")
        messagebox.showinfo(APP_NAME, f"PDF salvat:\n{out_path}")

    def reverse_pages_dialog(self):
        items = self.listbox.get(0, tk.END)
        if not items:
            messagebox.showwarning("Atenție", "Adaugă cel puțin un PDF și selectează-l.")
            return
        sel = self.selected_indices()
        if len(sel) != 1:
            messagebox.showwarning("Atenție", "Selectează un singur PDF din listă pentru inversare.")
            return
        path = items[sel[0]]
        reader = safe_open_reader(path)
        if not reader:
            return

        out_path = ask_save_as(f"reversed_{os.path.basename(path)}")
        if not out_path:
            return

        total = len(reader.pages)
        self._busy_on()
        try:
            writer = PdfWriter()
            for i in range(total - 1, -1, -1):
                writer.add_page(reader.pages[i])
                if i % 8 == 0:
                    self.update_idletasks()
            with open(out_path, "wb") as f:
                writer.write(f)

            tmp2 = out_path.replace(".pdf", ".__tmp__.pdf")
            try:
                os.replace(out_path, tmp2)
                sanitize_pdf_no_metadata(tmp2, out_path)
                os.remove(tmp2)
            except Exception:
                try:
                    if os.path.exists(tmp2):
                        os.replace(tmp2, out_path)
                except Exception:
                    pass

            self.status.set(f"Am inversat ordinea paginilor. PDF salvat: {os.path.basename(out_path)}.")
            messagebox.showinfo(APP_NAME, f"PDF salvat:\n{out_path}")
        finally:
            self._busy_off()

    def split_every_dialog(self):
        items = self.listbox.get(0, tk.END)
        if not items:
            messagebox.showwarning("Atenție", "Adaugă cel puțin un PDF și selectează-l.")
            return
        sel = self.selected_indices()
        if len(sel) != 1:
            messagebox.showwarning("Atenție", "Selectează un singur PDF din listă pentru split.")
            return
        path = items[sel[0]]
        reader = safe_open_reader(path)
        if not reader:
            return

        total = len(reader.pages)
        n = simpledialog.askinteger("Split PDF", "Împarte în fișiere de câte N pagini (ex: 10):", minvalue=1, initialvalue=10)
        if n is None:
            return
        out_dir = filedialog.askdirectory(title="Alege directorul unde salvez fișierele rezultate")
        if not out_dir:
            return

        base = os.path.splitext(os.path.basename(path))[0]
        self._busy_on()
        created = 0
        try:
            for start in range(0, total, n):
                writer = PdfWriter()
                end = min(start + n, total)
                for i in range(start, end):
                    writer.add_page(reader.pages[i])
                    if i % 8 == 0:
                        self.update_idletasks()

                out_path = os.path.join(out_dir, f"{base}_part_{start+1}-{end}.pdf")
                with open(out_path, "wb") as f:
                    writer.write(f)

                # sanitize each chunk
                tmp2 = out_path.replace(".pdf", ".__tmp__.pdf")
                try:
                    os.replace(out_path, tmp2)
                    sanitize_pdf_no_metadata(tmp2, out_path)
                    os.remove(tmp2)
                except Exception:
                    try:
                        if os.path.exists(tmp2):
                            os.replace(tmp2, out_path)
                    except Exception:
                        pass

                created += 1

            self.status.set(f"Am creat {created} fișier(e) în {out_dir}.")
            messagebox.showinfo(APP_NAME, f"Am creat {created} fișier(e).")
        finally:
            self._busy_off()

    # ---- DnD handler ----
    def _on_drop_files(self, event):
        paths = _parse_dnd_file_list(event.data)
        pdfs = _collect_pdfs_from_paths(paths)
        for p in pdfs:
            self.listbox.insert(tk.END, p)
        self._toggle_wizard()
        self.status.set(f"Adăugat prin DnD: {len(pdfs)} PDF-uri.")


# ------------------ Root Implementations ------------------

class PDFMixerDnD(TkinterDnD.Tk, PDFMixerBase):  # type: ignore
    def __init__(self):
        TkinterDnD.Tk.__init__(self)
        PDFMixerBase.__init__(self)
        self.title(APP_TITLE)
        self.minsize(APP_MIN_W, APP_MIN_H)
        self.build_menubar()
        self.build_layout(dnd=True)

class PDFMixerNoDnD(tk.Tk, PDFMixerBase):
    def __init__(self):
        super().__init__()
        PDFMixerBase.__init__(self)
        self.title(APP_TITLE)
        self.minsize(APP_MIN_W, APP_MIN_H)
        self.build_menubar()
        self.build_layout(dnd=False)

# ------------------ Main ------------------

def main():
    if _dnd_available:
        app = PDFMixerDnD()
    else:
        app = PDFMixerNoDnD()
    app.mainloop()

if __name__ == "__main__":
    main()

