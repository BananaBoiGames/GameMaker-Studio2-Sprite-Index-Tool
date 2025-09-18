import os
import re
import shutil
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

CODE_EXTENSIONS = ['.gml', '.yy', '.yyp']
SPRITE_VARS = [
    r'sprite_index',
    r'\w*spr\w*',
]
LOG_FILENAME = "spritereplacement_log.txt"
ICON_FILE = "icon.ico"

def load_sprite_map(mapping_file):
    mapping = {}
    with open(mapping_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '-' not in line:
                continue
            key, value = line.split('-', 1)
            key = key.strip()
            value = value.strip()
            mapping[key] = value
    return mapping

def backup_file(filepath):
    if not os.path.exists(filepath + '.bak'):
        shutil.copy(filepath, filepath + '.bak')

def replace_in_file(filename, sprite_map, gui_log_callback=None, file_log_callback=None):
    changed = False
    replacements = []
    with open(filename, encoding='utf-8') as f:
        lines = f.readlines()
    new_lines = []
    for idx, line in enumerate(lines, 1):
        orig_line = line
        for var in SPRITE_VARS:
            pattern = r'(' + var + r')\s*=\s*(\d+)\s*;'
            def repl(match):
                varname = match.group(1)
                num = match.group(2)
                if num in sprite_map:
                    new_line = f"{varname} = {sprite_map[num]};"
                    msg = f"[{os.path.basename(filename)}:{idx}] {orig_line.strip()} → {new_line}"
                    if gui_log_callback:
                        gui_log_callback(msg)
                    if file_log_callback:
                        file_log_callback(msg)
                    replacements.append((orig_line, new_line, idx))
                    return new_line
                else:
                    return match.group(0)
            line = re.sub(pattern, repl, line)
        if line != orig_line:
            changed = True
        new_lines.append(line)
    if changed:
        backup_file(filename)
        with open(filename, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
    return changed, replacements

def scan_and_replace(project_dir, mapping_file, gui_log_callback=None, status_callback=None):
    sprite_map = load_sprite_map(mapping_file)
    replaced_files = []
    all_replacements = []
    log_path = os.path.join(os.path.dirname(sys.argv[0]), LOG_FILENAME)
    with open(log_path, "w", encoding="utf-8") as log_f:
        def file_log_callback(msg):
            log_f.write(msg + "\n")
        for root, dirs, files in os.walk(project_dir):
            for file in files:
                if any(file.endswith(ext) for ext in CODE_EXTENSIONS):
                    filepath = os.path.join(root, file)
                    if status_callback:
                        status_callback(f"Scanning: {filepath}")
                    if gui_log_callback:
                        gui_log_callback(f"Checking: {filepath}")
                    changed, replacements = replace_in_file(
                        filepath, sprite_map, gui_log_callback, file_log_callback
                    )
                    if changed:
                        replaced_files.append(filepath)
                        all_replacements.extend([(filepath, *rep) for rep in replacements])
        summary = f"\nReplacements done in {len(replaced_files)} files.\nLog saved to {log_path}\n"
        if gui_log_callback:
            gui_log_callback(summary)
        log_f.write(summary)
        if status_callback:
            status_callback("Done.")
    return replaced_files, all_replacements, log_path

def set_custom_theme(root):
    bg = "#23272e"
    fg = "#EEE"
    entry_bg = "#23272e"
    text_bg = "#18191c"
    root.configure(bg=bg)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except:
        pass
    style.configure('.', background=bg, foreground=fg, fieldbackground=entry_bg, bordercolor=bg)
    style.configure('TButton', background=entry_bg, foreground=fg, borderwidth=1, padding=6)
    style.configure('TLabel', background=bg, foreground=fg)
    style.configure('TEntry', fieldbackground=entry_bg, foreground=fg)
    style.configure('TFrame', background=bg)
    style.configure('TScrollbar', background=entry_bg)
    style.map('TButton', background=[('active', entry_bg)])
    return bg, fg, entry_bg, text_bg

class SpriteReplacerGUI:
    def __init__(self, root):
        self.root = root
        root.title("GM2 Sprite Index Tool")
        if os.path.isfile(ICON_FILE):
            try:
                root.iconbitmap(ICON_FILE)
            except Exception:
                pass
        bg, fg, entry_bg, text_bg = set_custom_theme(root)
        mainframe = ttk.Frame(root, padding="10")
        mainframe.grid(row=0, column=0, sticky="nsew")
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        self.project_dir = tk.StringVar()
        self.mapping_file = tk.StringVar()
        ttk.Label(mainframe, text="GameMaker Project Folder:").grid(row=0, column=0, sticky="w")
        project_entry = ttk.Entry(mainframe, textvariable=self.project_dir, width=40)
        project_entry.grid(row=0, column=1, sticky="ew")
        browse_project_btn = ttk.Button(mainframe, text="Browse", command=self.browse_project)
        browse_project_btn.grid(row=0, column=2, padx=(8,0), ipadx=8, ipady=2, sticky="ew")
        ttk.Label(mainframe, text="Mapping File:").grid(row=1, column=0, sticky="w")
        mapping_entry = ttk.Entry(mainframe, textvariable=self.mapping_file, width=40)
        mapping_entry.grid(row=1, column=1, sticky="ew")
        browse_mapping_btn = ttk.Button(mainframe, text="Browse", command=self.browse_mapping)
        browse_mapping_btn.grid(row=1, column=2, padx=(8,0), ipadx=8, ipady=2, sticky="ew")
        run_btn = ttk.Button(mainframe, text="Run Replacement", command=self.run_replacement_thread, style="Accent.TButton")
        run_btn.grid(row=2, column=0, columnspan=3, pady=12, sticky="ew")
        self.status = ttk.Label(mainframe, text="Status: Ready")
        self.status.grid(row=3, column=0, columnspan=3, sticky="w", pady=(0,5))
        self.output = scrolledtext.ScrolledText(mainframe, width=80, height=20, state='disabled', bg=text_bg, fg=fg, insertbackground=fg)
        self.output.grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        mainframe.columnconfigure(1, weight=1)
        mainframe.rowconfigure(4, weight=1)

    def browse_project(self):
        directory = filedialog.askdirectory()
        if directory:
            self.project_dir.set(directory)
    def browse_mapping(self):
        file = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file:
            self.mapping_file.set(file)
    def log(self, msg):
        self.output.config(state='normal')
        self.output.insert(tk.END, msg + "\n")
        self.output.see(tk.END)
        self.output.config(state='disabled')
        self.root.update_idletasks()
    def set_status(self, msg):
        self.status.config(text=f"Status: {msg}")
        self.root.update_idletasks()
    def run_replacement_thread(self):
        self.output.config(state='normal')
        self.output.delete(1.0, tk.END)
        self.output.config(state='disabled')
        self.set_status("Working...")
        thread = threading.Thread(target=self.run_replacement, daemon=True)
        thread.start()
    def run_replacement(self):
        project_dir = self.project_dir.get()
        mapping_file = self.mapping_file.get()
        if not os.path.isdir(project_dir):
            self.set_status("Ready")
            messagebox.showerror("Error", "Please select a valid GameMaker project folder.")
            return
        if not os.path.isfile(mapping_file):
            self.set_status("Ready")
            messagebox.showerror("Error", "Please select a valid mapping file.")
            return
        try:
            scan_and_replace(
                project_dir, mapping_file, gui_log_callback=self.log, status_callback=self.set_status
            )
        except Exception as e:
            self.set_status("Ready")
            messagebox.showerror("Error", f"An error occurred:\n{e}")
        self.set_status("Ready")

if __name__ == '__main__':
    root = tk.Tk()
    gui = SpriteReplacerGUI(root)
    root.mainloop()