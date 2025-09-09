#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Mixer Pro – v1.0 (Branded, NO-METADATA)
Author: Alex Șerban Dâmbu
Company: Dâmbu Software
Copyright (c) 2025
All rights reserved.

Built with: Python + Tkinter + pypdf
Optional DnD via: tkinterdnd2
NOTE: This build intentionally does NOT modify any PDF metadata.
"""

import os
import time
import platform
import ctypes
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

try:
    from pypdf import PdfReader, PdfWriter
except Exception:
    print("Eroare: trebuie instalat 'pypdf' (pip install pypdf)")
    raise

# ------------------ Branding & App Consts ------------------
APP_NAME = "PDF Mixer Pro"
APP_VERSION = "1.0"
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

# ------------------ Styling ------------------

def apply_modern_theme(root: tk.Tk):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    # Global
    root.configure(bg=THEME['BG_MAIN'])
    style.configure("TFrame", background=THEME['BG_MAIN'])
    style.configure("Card.TFrame", background=THEME['BG_CARD'])
    style.configure("TLabel", background=THEME['BG_MAIN'], foreground=THEME['FG_TEXT'], font=("Segoe UI", 10))
    style.configure("Muted.TLabel", background=THEME['BG_MAIN'], foreground=THEME['FG_MUTED'])
    style.configure("Header.TLabel", background=THEME['BG_MAIN'], foreground=THEME['FG_TEXT'], font=("Segoe UI", 16, "bold"))
    style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=(12,6))
    style.map("Accent.TButton",
              background=[("active", THEME['ACCENT']), ("!active", THEME['ACCENT'])],
              foreground=[("active", "white"), ("!active", "white")])
    style.configure("TButton", font=("Segoe UI", 10), padding=(10,6))
    style.map("TButton",
              background=[("active", "#263143")],
              foreground=[("active", THEME['FG_TEXT'])])
    style.configure("TEntry", fieldbackground=THEME['BG_MAIN'], foreground=THEME['FG_TEXT'])
    style.configure("Horizontal.TSeparator", background="#202733")
    style.configure("TProgressbar", troughcolor=THEME['BG_CARD'], background=THEME['ACCENT'], bordercolor=THEME['BG_CARD'], lightcolor=THEME['ACCENT'], darkcolor=THEME['ACCENT'])

# Windows dark titlebar (best-effort coloring like the rest of the app)

def try_set_windows_dark_titlebar(win: tk.Tk):
    if platform.system() != "Windows":
        return
    try:
        hwnd = win.winfo_id()
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.wintypes.HWND(hwnd), ctypes.wintypes.DWORD(DWMWA_USE_IMMERSIVE_DARK_MODE), ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        try:
            DWMWA_USE_IMMERSIVE_DARK_MODE = 19
            hwnd = win.winfo_id()
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.wintypes.HWND(hwnd), ctypes.wintypes.DWORD(DWMWA_USE_IMMERSIVE_DARK_MODE), ctypes.byref(value), ctypes.sizeof(value))
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
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(0,10))
        self.btn_add = ttk.Button(toolbar, text="➕ Adaugă PDF-uri", style="Accent.TButton", command=self.add_files)
        self.btn_remove = ttk.Button(toolbar, text="🗑️ Șterge din listă", command=self.remove_selected)
        self.btn_up = ttk.Button(toolbar, text="⬆️ Sus", command=lambda: self.move_selected(-1))
        self.btn_down = ttk.Button(toolbar, text="⬇️ Jos", command=lambda: self.move_selected(1))
        self.btn_clear = ttk.Button(toolbar, text="🧹 Golește lista", command=self.clear_list)
        self.btn_sort_desc = ttk.Button(toolbar, text="🔽 Sortează lista (Z→A)", command=self.sort_list_desc)
        for w in (self.btn_add, self.btn_remove, self.btn_up, self.btn_down, self.btn_clear, self.btn_sort_desc):
            w.pack(side=tk.LEFT, padx=6)
        # Tooltips
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
        ttk.Label(left, text=hint_text, style="Muted.TLabel").pack(anchor="w", pady=(0,6))

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
        # Tooltips
        Tooltip(self.btn_merge, "Unește toate PDF-urile din listă în ordinea curentă.")
        Tooltip(self.btn_interleave, "Intercalează două PDF-uri după reguli: alternativ, impare/pare etc.")
        Tooltip(self.btn_extract, "Extrage doar paginile alese (ex: 1-3,5,10).")
        Tooltip(self.btn_delete, "Șterge din PDF paginile indicate și salvează rezultatul.")
        Tooltip(self.btn_rotate, "Rotește pagini cu 90/180/270°.")
        Tooltip(self.btn_reverse, "Creează un PDF cu paginile în ordine inversă.")
        Tooltip(self.btn_split_every, "Împarte PDF-ul în fișiere de câte N pagini.")

        # Onboarding wizard (when list is empty)
        self.wizard = ttk.Frame(left, padding=16, style="Card.TFrame")
        wtitle = ttk.Label(self.wizard, text="Începe în 3 pași", style="Header.TLabel")
        w1 = ttk.Label(self.wizard, text="1) Adaugă PDF-uri (butonul ➕ sau drag & drop)")
        w2 = ttk.Label(self.wizard, text="2) Opțional: rearanjează / sortează lista")
        w3 = ttk.Label(self.wizard, text="3) Alege acțiunea: Unește / Intercalează / etc.")
        for w in (wtitle, w1, w2, w3): w.pack(anchor="w", pady=2)
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
        text = (
            f"{APP_NAME} v{APP_VERSION}\n"
            f"{BRAND_COMPANY}\n\n"
            f"Autor: {BRAND_AUTHOR}\n"
            f"© {COPYRIGHT_YEAR} {BRAND_AUTHOR}. Toate drepturile rezervate.\n\n"
            "Ediția specială: de Simion Vampiru — paznic de noapte la pagini 🧛\n\n"
            "Acest software este furnizat ‘ca atare’, fără garanții. Folosirea implică acceptarea termenilor standard de licențiere pentru software proprietar."
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
        for i in idxs:
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
                if not reader: return
                for page in reader.pages:
                    writer.add_page(page)
                    total += 1
                    if total % 8 == 0:
                        self.update_idletasks()
            with open(out_path, "wb") as f: writer.write(f)
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
        dlg = tk.Toplevel(self); dlg.title("Intercalare pagini"); dlg.grab_set(); dlg.resizable(False, False)
        apply_modern_theme(dlg)
        ttk.Label(dlg, text="Alege cele două PDF-uri pentru intercalare:").grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8,4))
        varA = tk.StringVar(value=items[0]); varB = tk.StringVar(value=items[1])
        cbA = ttk.Combobox(dlg, textvariable=varA, values=list(items), state="readonly", width=60)
        cbB = ttk.Combobox(dlg, textvariable=varB, values=list(items), state="readonly", width=60)
        ttk.Label(dlg, text="PDF A:").grid(row=1, column=0, sticky="e", padx=8, pady=2); cbA.grid(row=1, column=1, sticky="w", padx=8, pady=2)
        ttk.Label(dlg, text="PDF B:").grid(row=2, column=0, sticky="e", padx=8, pady=2); cbB.grid(row=2, column=1, sticky="w", padx=8, pady=2)
        ttk.Label(dlg, text="Mod intercalare:").grid(row=3, column=0, sticky="e", padx=8, pady=(8,2))
        mode = tk.StringVar(value="alternate")
        modes = [("Alternativ (A1,B1,A2,B2)", "alternate"),("A impare + B pare","a_odd_b_even"),("A pare + B impare","a_even_b_odd"),("Doar impare din A","a_odd"),("Doar pare din B","b_even")]
        frm_modes = ttk.Frame(dlg); frm_modes.grid(row=3, column=1, sticky="w", padx=8, pady=(8,2))
        for text, val in modes: ttk.Radiobutton(frm_modes, text=text, value=val, variable=mode).pack(anchor="w")
        ttk.Label(dlg, text="Paginare începe de la (1-based):").grid(row=4, column=0, sticky="e", padx=8, pady=2)
        start_from = tk.IntVar(value=1); ttk.Spinbox(dlg, from_=1, to=99999, textvariable=start_from, width=6).grid(row=4, column=1, sticky="w", padx=8, pady=2)
        btns = ttk.Frame(dlg); btns.grid(row=5, column=0, columnspan=2, sticky="e", padx=8, pady=8)
        ttk.Button(btns, text="Anulează", command=dlg.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="OK", command=lambda: (self._busy_on(), self._do_interleave(varA.get(), varB.get(), mode.get(), start_from.get(), dlg), self._busy_off())).pack(side=tk.RIGHT)

    def _do_interleave(self, path_a: str, path_b: str, mode: str, start_from: int, dlg: tk.Toplevel):
        reader_a = safe_open_reader(path_a); reader_b = safe_open_reader(path_b)
        if not reader_a or not reader_b: return
        out_path = ask_save_as("interleaved.pdf");
        if not out_path: return
        writer = PdfWriter()
        def is_odd(i1: int) -> bool: return i1 % 2 == 1
        pa, pb = len(reader_a.pages), len(reader_b.pages)
        ia = ib = start_from - 1
        if mode == "alternate":
            while ia < pa or ib < pb:
                if ia < pa: writer.add_page(reader_a.pages[ia]); ia += 1
                if ib < pb: writer.add_page(reader_b.pages[ib]); ib += 1
        elif mode == "a_odd_b_even":
            for i in range(start_from, max(pa, pb) + 1):
                if i <= pa and is_odd(i): writer.add_page(reader_a.pages[i-1])
                if i <= pb and not is_odd(i): writer.add_page(reader_b.pages[i-1])
        elif mode == "a_even_b_odd":
            for i in range(start_from, max(pa, pb) + 1):
                if i <= pa and not is_odd(i): writer.add_page(reader_a.pages[i-1])
                if i <= pb and is_odd(i): writer.add_page(reader_b.pages[i-1])
        elif mode == "a_odd":
            for i in range(start_from, pa + 1):
                if is_odd(i): writer.add_page(reader_a.pages[i-1])
        elif mode == "b_even":
            for i in range(start_from, pb + 1):
                if not is_odd(i): writer.add_page(reader_b.pages[i-1])
        else:
            messagebox.showerror("Eroare", "Mod necunoscut."); return
        with open(out_path, "wb") as f: writer.write(f)
        dlg.destroy(); self.status.set(f"Intercalare reușită. Am salvat {os.path.basename(out_path)}."); messagebox.showinfo(APP_NAME, f"PDF salvat:\n{out_path}")

    def extract_pages_dialog(self):
        items = self.listbox.get(0, tk.END)
        if not items:
            messagebox.showwarning("Atenție", "Adaugă cel puțin un PDF și selectează-l."); return
        sel = self.selected_indices()
        if len(sel) != 1:
            messagebox.showwarning("Atenție", "Selectează un singur PDF din listă pentru a extrage pagini."); return
        path = items[sel[0]]
        reader = safe_open_reader(path)
        if not reader: return
        total = len(reader.pages)
        ranges = simpledialog.askstring("Extrage pagini", f"Introdu intervale (1-based), ex: 1-3,5,7-9\nTotal pagini: {total}")
        if ranges is None: return
        idxs = parse_page_ranges(ranges, total)
        if not idxs:
            messagebox.showwarning("Atenție", "Nu s-a specificat niciun interval valid."); return
        out_path = ask_save_as(f"extract_{os.path.basename(path)}")
        if not out_path: return
        self._busy_on()
        try:
            writer = PdfWriter()
            for i in idxs:
                writer.add_page(reader.pages[i])
                if i % 8 == 0: self.update_idletasks()
            with open(out_path, "wb") as f: writer.write(f)
            self.status.set(f"Extras cu succes {len(idxs)} pagini.")
            messagebox.showinfo(APP_NAME, f"PDF salvat:\n{out_path}")
        finally:
            self._busy_off()

    def delete_pages_dialog(self):
        items = self.listbox.get(0, tk.END)
        if not items:
            messagebox.showwarning("Atenție", "Adaugă cel puțin un PDF și selectează-l."); return
        sel = self.selected_indices()
        if len(sel) != 1:
            messagebox.showwarning("Atenție", "Selectează un singur PDF din listă pentru a șterge pagini."); return
        path = items[sel[0]]
        reader = safe_open_reader(path)
        if not reader: return
        total = len(reader.pages)
        ranges = simpledialog.askstring("Șterge pagini", f"Introdu intervale (1-based) de șters, ex: 2,5-7\nTotal pagini: {total}")
        if ranges is None: return
        to_delete = set(parse_page_ranges(ranges, total))
        if not to_delete:
            messagebox.showwarning("Atenție", "Nu s-a specificat niciun interval valid."); return
        out_path = ask_save_as(f"deleted_{os.path.basename(path)}")
        if not out_path: return
        self._busy_on()
        try:
            writer = PdfWriter(); kept = 0
            for i in range(total):
                if i not in to_delete:
                    writer.add_page(reader.pages[i]); kept += 1
                    if kept % 8 == 0: self.update_idletasks()
            with open(out_path, "wb") as f: writer.write(f)
            self.status.set(f"Am șters {len(to_delete)} pagini. Păstrate {kept}.")
            messagebox.showinfo(APP_NAME, f"PDF salvat:\n{out_path}")
        finally:
            self._busy_off()

    def rotate_pages_dialog(self):
        items = self.listbox.get(0, tk.END)
        if not items:
            messagebox.showwarning("Atenție", "Adaugă cel puțin un PDF și selectează-l."); return
        sel = self.selected_indices()
        if len(sel) != 1:
            messagebox.showwarning("Atenție", "Selectează un singur PDF din listă pentru rotire."); return
        path = items[sel[0]]
        reader = safe_open_reader(path)
        if not reader: return
        total = len(reader.pages)
        dlg = tk.Toplevel(self); dlg.title("Rotire pagini"); dlg.grab_set(); dlg.resizable(False, False)
        apply_modern_theme(dlg)
        ttk.Label(dlg, text=f"Fișier: {os.path.basename(path)} – {total} pagini").grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8,4))
        ttk.Label(dlg, text="Grade (90 / 180 / 270):").grid(row=1, column=0, sticky="e", padx=8, pady=2)
        var_deg = tk.IntVar(value=90)
        ttk.Spinbox(dlg, from_=0, to=359, textvariable=var_deg, width=6).grid(row=1, column=1, sticky="w", padx=8, pady=2)
        ttk.Label(dlg, text="Intervale (opțional):").grid(row=2, column=0, sticky="e", padx=8, pady=2)
        var_ranges = tk.StringVar(value="")
        ttk.Entry(dlg, textvariable=var_ranges, width=40).grid(row=2, column=1, sticky="w", padx=8, pady=2)
        ttk.Label(dlg, text="Ex: 1-3,5,10").grid(row=3, column=1, sticky="w", padx=8, pady=(0,8))
        btns = ttk.Frame(dlg); btns.grid(row=4, column=0, columnspan=2, sticky="e", padx=8, pady=8)
        ttk.Button(btns, text="Anulează", command=dlg.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="OK", command=lambda: (self._busy_on(), self._do_rotate(path, var_deg.get(), var_ranges.get(), dlg), self._busy_off())).pack(side=tk.RIGHT)

    def _do_rotate(self, path: str, degrees: int, ranges: str, dlg: tk.Toplevel):
        reader = safe_open_reader(path)
        if not reader: return
        total = len(reader.pages); idxs = parse_page_ranges(ranges, total) if ranges.strip() else list(range(total))
        out_path = ask_save_as(f"rotated_{os.path.basename(path)}")
        if not out_path: return
        writer = PdfWriter()
        for i in range(total):
            page = reader.pages[i]
            if i in idxs: rotate_page(page, degrees)
            writer.add_page(page)
            if i % 8 == 0: self.update_idletasks()
        with open(out_path, "wb") as f: writer.write(f)
        dlg.destroy(); self.status.set(f"Rotire reușită. PDF salvat: {os.path.basename(out_path)}."); messagebox.showinfo(APP_NAME, f"PDF salvat:\n{out_path}")

    def reverse_pages_dialog(self):
        items = self.listbox.get(0, tk.END)
        if not items:
            messagebox.showwarning("Atenție", "Adaugă cel puțin un PDF și selectează-l."); return
        sel = self.selected_indices()
        if len(sel) != 1:
            messagebox.showwarning("Atenție", "Selectează un singur PDF din listă pentru inversare."); return
        path = items[sel[0]]; reader = safe_open_reader(path)
        if not reader: return
        out_path = ask_save_as(f"reversed_{os.path.basename(path)}")
        if not out_path: return
        total = len(reader.pages)
        self._busy_on()
        try:
            writer = PdfWriter()
            for i in range(total - 1, -1, -1):
                writer.add_page(reader.pages[i])
                if i % 8 == 0: self.update_idletasks()
            with open(out_path, "wb") as f: writer.write(f)
            self.status.set(f"Am inversat ordinea paginilor. PDF salvat: {os.path.basename(out_path)}.")
            messagebox.showinfo(APP_NAME, f"PDF salvat:\n{out_path}")
        finally:
            self._busy_off()

    def split_every_dialog(self):
        items = self.listbox.get(0, tk.END)
        if not items:
            messagebox.showwarning("Atenție", "Adaugă cel puțin un PDF și selectează-l."); return
        sel = self.selected_indices()
        if len(sel) != 1:
            messagebox.showwarning("Atenție", "Selectează un singur PDF din listă pentru split."); return
        path = items[sel[0]]; reader = safe_open_reader(path)
        if not reader: return
        total = len(reader.pages)
        n = simpledialog.askinteger("Split PDF", "Împarte în fișiere de câte N pagini (ex: 10):", minvalue=1, initialvalue=10)
        if n is None: return
        out_dir = filedialog.askdirectory(title="Alege directorul unde salvez fișierele rezultate")
        if not out_dir: return
        base = os.path.splitext(os.path.basename(path))[0]
        self._busy_on(); created = 0
        try:
            for start in range(0, total, n):
                writer = PdfWriter(); end = min(start + n, total)
                for i in range(start, end):
                    writer.add_page(reader.pages[i])
                    if i % 8 == 0: self.update_idletasks()
                out_path = os.path.join(out_dir, f"{base}_part_{start+1}-{end}.pdf")
                with open(out_path, "wb") as f: writer.write(f)
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
