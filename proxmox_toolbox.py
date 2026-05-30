import tkinter as tk
from tkinter import ttk, messagebox
import requests
import sys
import os
from proxmoxer import ProxmoxAPI
import urllib3

# Warnungen für selbstsignierte Zertifikate deaktivieren (Standard bei Proxmox)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- KONFIGURATION ---
GITHUB_RAW_URL = "https://raw.githubusercontent.com/DukyNuky/duky-prox-toolbox/refs/heads/main/proxmox_toolbox.py"
CURRENT_VERSION = "0.1"

class ProxmoxToolbox:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Proxmox Toolbox! v{CURRENT_VERSION}")
        self.root.geometry("600x450")
        self.proxmox = None
        
        # UI Container
        self.login_frame = tk.Frame(self.root)
        self.main_frame = tk.Frame(self.root)
        
        # Start
        self.create_login_screen()
        self.login_frame.pack(fill="both", expand=True)

    # ==========================================
    # MODUL: UPDATE SYSTEM
    # ==========================================
    def check_for_update(self):
        """Lädt die aktuelle Version von GitHub, überschreibt sich selbst und startet neu."""
        
        # WICHTIG: GITHUB_RAW_URL oben im Skript muss auf die RAW-Ansicht deiner Datei zeigen!
        if "DEIN_NAME" in GITHUB_RAW_URL:
            messagebox.showwarning("Hinweis", "Bitte trage erst deine echte GitHub RAW-URL im Skript ein (Variable GITHUB_RAW_URL).")
            return

        try:
            # Lade den Code von GitHub
            response = requests.get(GITHUB_RAW_URL, timeout=10)
            response.raise_for_status() # Löst einen Fehler aus, wenn die Seite nicht 200 OK meldet (z.B. 404)
            
            new_code = response.text
            
            # Ein kleiner Sicherheitscheck, ob das, was wir geladen haben, auch wirklich unser Skript ist
            if "class ProxmoxToolbox:" not in new_code:
                messagebox.showerror("Update-Fehler", "Die heruntergeladene Datei scheint nicht das korrekte Skript zu sein.")
                return

            # Ermittle den absoluten Pfad der Datei, die gerade ausgeführt wird
            current_file = os.path.abspath(__file__)
            
            # Überschreibe die eigene Datei mit dem neuen Code
            with open(current_file, 'w', encoding='utf-8') as f:
                f.write(new_code)
                
            messagebox.showinfo("Update erfolgreich", "Das Tool wurde erfolgreich aktualisiert und startet nun neu!")
            
            # Prozess sauber durch den neuen ersetzen (Cross-Plattform kompatibel)
            os.execv(sys.executable, [sys.executable, current_file])

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Netzwerkfehler", f"Konnte GitHub nicht erreichen:\n{str(e)}")
        except Exception as e:
            messagebox.showerror("Update fehlgeschlagen", f"Ein unerwarteter Fehler ist aufgetreten:\n{str(e)}")

    # ==========================================
    # MODUL: GUI AUFBAU
    # ==========================================
    def create_login_screen(self):
        tk.Label(self.login_frame, text="Proxmox Login", font=("Arial", 16, "bold")).pack(pady=20)

        # Host
        tk.Label(self.login_frame, text="Host (IP oder FQDN):").pack()
        self.entry_host = tk.Entry(self.login_frame, width=30)
        self.entry_host.pack(pady=5)
        self.entry_host.insert(0, "192.168.x.x")

        # User
        tk.Label(self.login_frame, text="Benutzer (z.B. root@pam):").pack()
        self.entry_user = tk.Entry(self.login_frame, width=30)
        self.entry_user.pack(pady=5)
        self.entry_user.insert(0, "root@pam")

        # Passwort
        tk.Label(self.login_frame, text="Passwort:").pack()
        self.entry_pw = tk.Entry(self.login_frame, width=30, show="*")
        self.entry_pw.pack(pady=5)

        # Login Button
        tk.Button(self.login_frame, text="Verbinden", command=self.do_login, bg="#4CAF50", fg="white").pack(pady=20)
        
        # Update Button
        tk.Button(self.login_frame, text="Nach Updates suchen", command=self.check_for_update).pack(pady=5)

    def create_main_screen(self):
        # Header
        header = tk.Frame(self.main_frame)
        header.pack(fill="x", padx=10, pady=10)
        tk.Label(header, text="Aktuelle VMs", font=("Arial", 14, "bold")).pack(side="left")
        tk.Button(header, text="Aktualisieren", command=self.load_vms).pack(side="right")
        tk.Button(header, text="Logout", command=self.do_logout).pack(side="right", padx=10)

        # Tabelle für VMs
        columns = ("ID", "Name", "Status", "Node")
        self.tree = ttk.Treeview(self.main_frame, columns=columns, show="headings")
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="center")
            
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

    # ==========================================
    # MODUL: PROXMOX LOGIK
    # ==========================================
    def do_login(self):
        host = self.entry_host.get()
        user = self.entry_user.get()
        password = self.entry_pw.get()

        try:
            # Verbindung aufbauen
            self.proxmox = ProxmoxAPI(
                host, user=user, password=password, verify_ssl=False
            )
            # Test-Call um zu prüfen ob Login erfolgreich war
            self.proxmox.version.get()
            
            # Ansicht wechseln
            self.login_frame.pack_forget()
            self.create_main_screen()
            self.main_frame.pack(fill="both", expand=True)
            
            # Daten initial laden
            self.load_vms()
            
        except Exception as e:
            messagebox.showerror("Login Fehler", f"Verbindung fehlgeschlagen:\n{str(e)}")

    def do_logout(self):
        self.proxmox = None
        # Tabelleninhalt löschen
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Ansicht zurückwechseln
        self.main_frame.pack_forget()
        self.login_frame.pack(fill="both", expand=True)

    def load_vms(self):
        # Alte Einträge löschen
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        try:
            # Liste aller Nodes im Cluster abrufen
            nodes = self.proxmox.nodes.get()
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte Cluster-Nodes nicht abrufen:\n{str(e)}")
            return

        for node in nodes:
            node_name = node['node']
            
            # 1. Check: Ist die Node laut Proxmox-Status überhaupt online?
            if node.get('status') != 'online':
                print(f"Node '{node_name}' ist nicht online. Überspringe...")
                # Optional: Einen visuellen Platzhalter in die Tabelle packen
                self.tree.insert("", "end", values=("-", f"[{node_name} OFFLINE]", "-", node_name))
                continue
                
            # 2. Versuch, die VMs abzurufen
            try:
                vms = self.proxmox.nodes(node_name).qemu.get()
                
                for vm in vms:
                    vmid = vm.get("vmid", "N/A")
                    name = vm.get("name", "Unbekannt")
                    status = vm.get("status", "N/A")
                    
                    self.tree.insert("", "end", values=(vmid, name, status, node_name))
                    
            except Exception as e:
                # Falls trotz "online" Status ein Timeout/595 Fehler auftritt: 
                # Fehler in die Konsole drucken, aber Skript läuft für die nächsten Nodes weiter.
                print(f"Warnung: Konnte VMs von Node '{node_name}' nicht laden: {e}")
                self.tree.insert("", "end", values=("-", f"API-Fehler bei {node_name}", "Fehler", node_name))

if __name__ == "__main__":
    root = tk.Tk()
    app = ProxmoxToolbox(root)
    root.mainloop()
