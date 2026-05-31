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
        tk.Button(self.sidebar, text="Logout", command=self.do_logout, bg="#e74c3c", fg="white").pack(side="bottom", fill="x", padx=15, pady=(5, 20))
        tk.Button(self.sidebar, text="Tool Updaten", command=self.check_for_update).pack(side="bottom", fill="x", padx=15, pady=(5, 5))

    # ==========================================
    # MODUL: MAIN ANSICHTEN (Rechts)
    # ==========================================
    def show_welcome_main(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()
        
        # Grauen Hintergrund für den Container sicherstellen
        self.main_container.config(bg="#ecf0f1")
        tk.Label(self.main_container, text="Willkommen in der Proxmox Toolbox", bg="#ecf0f1", font=("Arial", 18, "bold"), fg="#333333").pack(expand=True)

    def show_vm_view(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

        # Header Bereich
        header_frame = tk.Frame(self.main_container, bg="#ecf0f1")
        header_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(header_frame, text="Virtuelle Maschinen", bg="#ecf0f1", font=("Arial", 16, "bold"), fg="#333333").pack(side="left")
        tk.Button(header_frame, text="Aktualisieren", command=self.load_vms, bg="#3498db", fg="white").pack(side="right")

        # Tabelle (Treeview)
        columns = ("ID", "Name", "Status", "Node")
        self.tree = ttk.Treeview(self.main_container, columns=columns, show="headings")
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center")
            
        self.tree.pack(fill="both", expand=True)

        # Daten sofort laden
        self.load_vms()

    # ==========================================
    # MODUL: LOGIK (Login, Proxmox, Update)
    # ==========================================
    def do_login(self):
        host = self.entry_host.get()
        user = self.entry_user.get()
        password = self.entry_pw.get()

        try:
            self.proxmox = ProxmoxAPI(host, user=user, password=password, verify_ssl=False)
            self.proxmox.version.get() # Testcall
            
            # Ansichten wechseln
            self.show_sidebar_menu()
            self.show_vm_view()
            
        except Exception as e:
            messagebox.showerror("Login Fehler", f"Verbindung fehlgeschlagen:\n{str(e)}")

    def do_logout(self):
        self.proxmox = None
        self.show_sidebar_login()
        self.show_welcome_main()

    def load_vms(self):
        if not self.proxmox:
            return

        # Tabelle leeren
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        try:
            nodes = self.proxmox.nodes.get()
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte Cluster-Nodes nicht abrufen:\n{str(e)}")
            return

        for node in nodes:
            node_name = node['node']
            
            if node.get('status') != 'online':
                self.tree.insert("", "end", values=("-", f"[{node_name} OFFLINE]", "-", node_name))
                continue
                
            try:
                vms = self.proxmox.nodes(node_name).qemu.get()
                for vm in vms:
                    self.tree.insert("", "end", values=(vm.get("vmid", "N/A"), vm.get("name", "Unbekannt"), vm.get("status", "N/A"), node_name))
            except Exception as e:
                print(f"Warnung bei Node '{node_name}': {e}")
                self.tree.insert("", "end", values=("-", f"Fehler bei {node_name}", "Fehler", node_name))

    def check_for_update(self):
        if "DEIN_NAME" in GITHUB_API_URL:
            messagebox.showwarning("Hinweis", "Bitte trage erst deine echte GitHub API-URL im Skript ein (Variable GITHUB_API_URL).")
            return

        try:
            headers = {"Accept": "application/vnd.github.v3.raw", "Cache-Control": "no-cache"}
            response = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
            response.raise_for_status() 
            
            new_code = response.text
            
            if "class ProxmoxToolbox:" not in new_code:
                messagebox.showerror("Update-Fehler", "Skript ungültig.")
                return

            current_file = os.path.abspath(__file__)
            with open(current_file, 'w', encoding='utf-8') as f:
                f.write(new_code)
                
            messagebox.showinfo("Update", "Tool aktualisiert. Startet neu!")
            os.execv(sys.executable, [sys.executable, current_file])

        except Exception as e:
            messagebox.showerror("Update fehlgeschlagen", f"Fehler:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ProxmoxToolbox(root)
    root.mainloop()
