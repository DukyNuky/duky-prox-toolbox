import tkinter as tk
from tkinter import ttk, messagebox
import requests
import os
import sys
from proxmoxer import ProxmoxAPI
import urllib3

# Warnungen für selbstsignierte Zertifikate deaktivieren
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- KONFIGURATION ---
# Bitte hier wieder deine echte GitHub API URL eintragen!
GITHUB_API_URL = "https://api.github.com/repos/DEIN_NAME/DEIN_REPO/contents/proxmox_toolbox.py"

class ProxmoxToolbox:
    def __init__(self, root):
        self.root = root
        self.root.title("Proxmox Toolbox")
        self.root.geometry("1000x600")
        
        # --- GRID LAYOUT ---
        # Spalte 0 (Sidebar) ist fixiert, Spalte 1 (Main) wächst dynamisch
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # 1. Sidebar Frame erstellen (Dunkles Design)
        self.sidebar = tk.Frame(self.root, bg="#2c3e50", width=250)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False) # Verhindert, dass die Sidebar schrumpft

        # 2. Main Frame erstellen (Helles Design)
        self.main_container = tk.Frame(self.root, bg="#ecf0f1")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self.proxmox = None

        # Start: Login in der Sidebar anzeigen
        self.show_sidebar_login()
        self.show_welcome_main()

    # ==========================================
    # MODUL: SIDEBAR ANSICHTEN
    # ==========================================
    def show_sidebar_login(self):
        # Sidebar leeren
        for widget in self.sidebar.winfo_children():
            widget.destroy()

        # Titel
        tk.Label(self.sidebar, text="Proxmox Login", bg="#2c3e50", fg="white", font=("Arial", 16, "bold")).pack(pady=(20, 20))

        # Host
        tk.Label(self.sidebar, text="Host (IP oder FQDN):", bg="#2c3e50", fg="white").pack(anchor="w", padx=15)
        self.entry_host = tk.Entry(self.sidebar)
        self.entry_host.pack(fill="x", padx=15, pady=(0, 15))
        self.entry_host.insert(0, "192.168.x.x")

        # User
        tk.Label(self.sidebar, text="Benutzer:", bg="#2c3e50", fg="white").pack(anchor="w", padx=15)
        self.entry_user = tk.Entry(self.sidebar)
        self.entry_user.pack(fill="x", padx=15, pady=(0, 15))
        self.entry_user.insert(0, "root@pam")

        # Passwort
        tk.Label(self.sidebar, text="Passwort:", bg="#2c3e50", fg="white").pack(anchor="w", padx=15)
        self.entry_pw = tk.Entry(self.sidebar, show="*")
        self.entry_pw.pack(fill="x", padx=15, pady=(0, 20))

        # Login Button
        tk.Button(self.sidebar, text="Verbinden", command=self.do_login, bg="#27ae60", fg="white", font=("Arial", 10, "bold")).pack(fill="x", padx=15)

        # Update Button ganz unten
        tk.Button(self.sidebar, text="Tool Updaten", command=self.check_for_update).pack(side="bottom", fill="x", padx=15, pady=20)

    def show_sidebar_menu(self):
        # Sidebar leeren
        for widget in self.sidebar.winfo_children():
            widget.destroy()

        # Titel
        tk.Label(self.sidebar, text="Toolbox Menu", bg="#2c3e50", fg="#2ecc71", font=("Arial", 16, "bold")).pack(pady=(20, 20))

        # Funktionen
        tk.Button(self.sidebar, text="VMs auflisten", command=self.show_vm_view, font=("Arial", 11)).pack(fill="x", padx=15, pady=5)
        
        # Hier kannst du später weitere Buttons einfügen, z.B.:
        # tk.Button(self.sidebar, text="Backups prüfen", command=self.show_backup_view).pack(fill="x", padx=15, pady=5)

        # Logout & Update ganz unten
        tk.Button(self.sidebar, text="Logout", command=self.do_logout, bg="#e74c3c", fg
