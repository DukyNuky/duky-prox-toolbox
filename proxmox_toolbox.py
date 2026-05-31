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
GITHUB_API_URL = "https://api.github.com/repos/DEIN_NAME/DEIN_REPO/contents/proxmox_toolbox.py"

# --- FARBEN (PROXMOX DARK MODE) ---
BG_MAIN = "#1a1c23"       # Dunkler Hintergrund (Hauptbereich)
BG_SIDEBAR = "#21242d"    # Etwas heller (Sidebar)
BG_ELEMENTS = "#2b2f3a"   # Eingabefelder etc.
FG_TEXT = "#e0e0e0"       # Helle Schrift
PX_ORANGE = "#e36b22"     # Proxmox Akzentfarbe (Orange)
GREEN = "#2ecc71"
RED = "#e74c3c"

class ProxmoxToolbox:
    def __init__(self, root):
        self.root = root
        self.root.title("Proxmox Toolbox Pro")
        self.root.geometry("1000x650")
        self.root.configure(bg=BG_MAIN)
        
        # --- STYLING (für moderne Balken und Tabellen) ---
        self.style = ttk.Style()
        self.style.theme_use("default")
        
        # Tabelle (Treeview) Dark Mode
        self.style.configure("Treeview", background=BG_ELEMENTS, foreground=FG_TEXT, fieldbackground=BG_ELEMENTS, borderwidth=0)
        self.style.map('Treeview', background=[('selected', PX_ORANGE)])
        self.style.configure("Treeview.Heading", background=BG_SIDEBAR, foreground=FG_TEXT, relief="flat", font=("Arial", 10, "bold"))
        self.style.map("Treeview.Heading", background=[('active', BG_MAIN)])
        
        # Progressbar (für CPU/RAM)
        self.style.configure("Orange.Horizontal.TProgressbar", background=PX_ORANGE, troughcolor=BG_ELEMENTS, bordercolor=BG_MAIN, lightcolor=PX_ORANGE, darkcolor=PX_ORANGE)

        # --- GRID LAYOUT ---
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(self.root, bg=BG_SIDEBAR, width=250)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        self.main_container = tk.Frame(self.root, bg=BG_MAIN)
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        self.proxmox = None

        self.show_sidebar_login()
        self.show_welcome_main()

    # ==========================================
    # SIDEBAR
    # ==========================================
    def show_sidebar_login(self):
        for widget in self.sidebar.winfo_children(): widget.destroy()

        tk.Label(self.sidebar, text="Proxmox Login", bg=BG_SIDEBAR, fg=PX_ORANGE, font=("Arial", 16, "bold")).pack(pady=(30, 20))

        # Helper Funktion für schöne Eingabefelder
        def create_input(label_text, default_val="", is_pw=False):
            tk.Label(self.sidebar, text=label_text, bg=BG_SIDEBAR, fg=FG_TEXT).pack(anchor="w", padx=15)
            entry = tk.Entry(self.sidebar, bg=BG_ELEMENTS, fg="white", insertbackground="white", relief="flat", highlightbackground=BG_MAIN, highlightthickness=1)
            entry.pack(fill="x", padx=15, pady=(0, 15), ipady=4)
            if default_val: entry.insert(0, default_val)
            if is_pw: entry.config(show="*")
            return entry

        self.entry_host = create_input("Host (IP oder FQDN):", "192.168.x.x")
        self.entry_user = create_input("Benutzer:", "root@pam")
        self.entry_pw = create_input("Passwort:", is_pw=True)

        tk.Button(self.sidebar, text="Verbinden", command=self.do_login, bg=PX_ORANGE, fg="white", font=("Arial", 10, "bold"), relief="flat", cursor="hand2").pack(fill="x", padx=15, pady=10, ipady=4)
        tk.Button(self.sidebar, text="Tool Updaten", command=self.check_for_update, bg=BG_ELEMENTS, fg=FG_TEXT, relief="flat", cursor="hand2").pack(side="bottom", fill="x", padx=15, pady=20, ipady=4)

    def show_sidebar_menu(self):
        for widget in self.sidebar.winfo_children(): widget.destroy()

        tk.Label(self.sidebar, text="Toolbox Menu", bg=BG_SIDEBAR, fg=PX_ORANGE, font=("Arial", 16, "bold")).pack(pady=(30, 20))

        # Menü Buttons
        btn_style = {"bg": BG_ELEMENTS, "fg": FG_TEXT, "relief": "flat", "font": ("Arial", 11), "cursor": "hand2"}
        tk.Button(self.sidebar, text="VMs auflisten", command=self.show_vm_view, **btn_style).pack(fill="x", padx=15, pady=5, ipady=4)
        tk.Button(self.sidebar, text="Node Status", command=self.show_node_status_view, **btn_style).pack(fill="x", padx=15, pady=5, ipady=4)

        tk.Button(self.sidebar, text="Logout", command=self.do_logout, bg=RED, fg="white", relief="flat", cursor="hand2").pack(side="bottom", fill="x", padx=15, pady=(5, 20), ipady=4)
        tk.Button(self.sidebar, text="Tool Updaten", command=self.check_for_update, bg=BG_ELEMENTS, fg=FG_TEXT, relief="flat", cursor="hand2").pack(side="bottom", fill="x", padx=15, pady=(5, 5), ipady=4)

    # ==========================================
    # MAIN VIEWS
    # ==========================================
    def show_welcome_main(self):
        for widget in self.main_container.winfo_children(): widget.destroy()
        tk.Label(self.main_container, text="Willkommen in der Proxmox Toolbox", bg=BG_MAIN, font=("Arial", 18, "bold"), fg=FG_TEXT).pack(expand=True)

    def show_vm_view(self):
        for widget in self.main_container.winfo_children(): widget.destroy()

        header = tk.Frame(self.main_container, bg=BG_MAIN)
        header.pack(fill="x", pady=(0, 15))
        tk.Label(header, text="Virtuelle Maschinen", bg=BG_MAIN, font=("Arial", 16, "bold"), fg=FG_TEXT).pack(side="left")
        tk.Button(header, text="Aktualisieren", command=self.load_vms, bg=PX_ORANGE, fg="white", relief="flat", cursor="hand2").pack(side="right", ipady=2, ipadx=10)

        columns = ("ID", "Name", "Status", "Node")
        self.tree = ttk.Treeview(self.main_container, columns=columns, show="headings", style="Treeview")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center")
        self.tree.pack(fill="both", expand=True)

        self.load_vms()

    # --- NEU: NODE STATUS VIEW ---
    def show_node_status_view(self):
        for widget in self.main_container.winfo_children(): widget.destroy()

        # Header
        header = tk.Frame(self.main_container, bg=BG_MAIN)
        header.pack(fill="x", pady=(0, 20))
        tk.Label(header, text="Node Dashboard", bg=BG_MAIN, font=("Arial", 16, "bold"), fg=FG_TEXT).pack(side="left")

        # Controls (Dropdown)
        control_frame = tk.Frame(self.main_container, bg=BG_MAIN)
        control_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(control_frame, text="Node auswählen:", bg=BG_MAIN, fg=FG_TEXT, font=("Arial", 11)).pack(side="left", padx=(0, 10))
        
        self.node_var = tk.StringVar()
        self.node_dropdown = ttk.Combobox(control_frame, textvariable=self.node_var, state="readonly", font=("Arial", 11))
        self.node_dropdown.pack(side="left")
        self.node_dropdown.bind("<<ComboboxSelected>>", self.load_node_stats)

        # Content Frame für die Stats
        self.stats_frame = tk.Frame(self.main_container, bg=BG_ELEMENTS, padx=20, pady=20)
        self.stats_frame.pack(fill="x")

        # Initiale Füllung
        self.populate_node_dropdown()

    # ==========================================
    # LOGIK (Proxmox, Update, Stats)
    # ==========================================
    def do_login(self):
        try:
            self.proxmox = ProxmoxAPI(self.entry_host.get(), user=self.entry_user.get(), password=self.entry_pw.get(), verify_ssl=False)
            self.proxmox.version.get() # Test
            self.show_sidebar_menu()
            self.show_node_status_view() # Startet direkt im schicken neuen Dashboard
        except Exception as e:
            messagebox.showerror("Login Fehler", f"Verbindung fehlgeschlagen:\n{str(e)}")

    def do_logout(self):
        self.proxmox = None
        self.show_sidebar_login()
        self.show_welcome_main()

    def load_vms(self):
        if not self.proxmox: return
        for item in self.tree.get_children(): self.tree.delete(item)
        try:
            nodes = self.proxmox.nodes.get()
            for node in nodes:
                node_name = node['node']
                if node.get('status') != 'online':
                    self.tree.insert("", "end", values=("-", f"[{node_name} OFFLINE]", "-", node_name))
                    continue
                try:
                    for vm in self.proxmox.nodes(node_name).qemu.get():
                        self.tree.insert("", "end", values=(vm.get("vmid"), vm.get("name"), vm.get("status"), node_name))
                except Exception: pass
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Laden:\n{str(e)}")

    # --- NEU: STATS LOGIK ---
    def populate_node_dropdown(self):
        if not self.proxmox: return
        try:
            nodes = self.proxmox.nodes.get()
            node_names = [n['node'] for n in nodes if n.get('status') == 'online']
            self.node_dropdown['values'] = node_names
            if node_names:
                self.node_dropdown.set(node_names[0])
                self.load_node_stats()
        except Exception as e:
            print(f"Fehler Nodes laden: {e}")

    def load_node_stats(self, event=None):
        node = self.node_var.get()
        if not node or not self.proxmox: return

        # Stats-Frame leeren für neuen Aufbau
        for widget in self.stats_frame.winfo_children(): widget.destroy()

        try:
            # Daten von API holen
            status = self.proxmox.nodes(node).status.get()
            version_info = self.proxmox.version.get()

            # Version
            tk.Label(self.stats_frame, text=f"Proxmox Version: {version_info.get('release')} (v{version_info.get('version')})", bg=BG_ELEMENTS, fg=PX_ORANGE, font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 15))

            # Helper für Progressbars
            def create_stat_bar(label, used, total, is_percent=False):
                frame = tk.Frame(self.stats_frame, bg=BG_ELEMENTS)
                frame.pack(fill="x", pady=5)
                
                percent = (used / total) * 100 if total > 0 else 0
                
                if is_percent:
                    text = f"{label}: {percent:.1f}%"
                else:
                    # Umrechnung in GB
                    used_gb = used / (1024**3)
                    total_gb = total / (1024**3)
                    text = f"{label}: {used_gb:.1f} GB / {total_gb:.1f} GB ({percent:.1f}%)"

                tk.Label(frame, text=text, bg=BG_ELEMENTS, fg=FG_TEXT, font=("Arial", 10)).pack(anchor="w")
                bar = ttk.Progressbar(frame, style="Orange.Horizontal.TProgressbar", length=400, mode='determinate')
                bar.pack(fill="x", pady=(2, 10))
                bar['value'] = percent

            # CPU
            cpu_usage = status.get('cpu', 0)
            create_stat_bar("CPU Auslastung", cpu_usage, 1.0, is_percent=True)

            # RAM
            mem = status.get('memory', {})
            create_stat_bar("RAM Auslastung", mem.get('used', 0), mem.get('total', 1))

            # RootFS (Partition)
            rootfs = status.get('rootfs', {})
            create_stat_bar("Root Partition (/)", rootfs.get('used', 0), rootfs.get('total', 1))

            # Wartungsmodus Button
            btn_frame = tk.Frame(self.stats_frame, bg=BG_ELEMENTS)
            btn_frame.pack(fill="x", pady=(20, 0))
            tk.Button(btn_frame, text="Wartungsmodus umschalten (HA)", command=lambda: self.toggle_maintenance(node), bg=RED, fg="white", relief="flat", cursor="hand2", font=("Arial", 10, "bold")).pack(side="left", ipady=4, ipadx=10)

        except Exception as e:
            tk.Label(self.stats_frame, text=f"Fehler beim Laden der Stats:\n{e}", bg=BG_ELEMENTS, fg=RED).pack()

    def toggle_maintenance(self, node):
        # Sicherheitsabfrage
        if not messagebox.askyesno("Sicherheitsabfrage", f"Möchtest du den HA-Wartungsstatus für '{node}' wirklich umschalten?"):
            return
            
        try:
            # Info: Dies funktioniert, wenn High Availability (HA) konfiguriert ist. 
            # Ohne HA wirft die API hier evt. einen Fehler, den wir abfangen.
            current_state = self.proxmox.cluster.ha.nodes(node).get()
            
            # Sehr rudimentärer Toggle (online <-> maintenance)
            new_state = "online" if current_state.get('state') == "maintenance" else "maintenance"
            
            self.proxmox.cluster.ha.nodes(node).put(state=new_state)
            messagebox.showinfo("Erfolg", f"Node '{node}' ist nun: {new_state}")
            
        except Exception as e:
            messagebox.showwarning("Hinweis", f"Wartungsmodus konnte nicht gesetzt werden.\nVermutlich ist Proxmox HA auf diesem Node nicht aktiv.\n\nDetails: {str(e)}")

    # ==========================================
    # UPDATE
    # ==========================================
    def check_for_update(self):
        if "DEIN_NAME" in GITHUB_API_URL:
            messagebox.showwarning("Hinweis", "Bitte GitHub API-URL eintragen.")
            return
        try:
            headers = {"Accept": "application/vnd.github.v3.raw", "Cache-Control": "no-cache"}
            response = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
            response.raise_for_status() 
            new_code = response.text
            if "class ProxmoxToolbox:" not in new_code:
                messagebox.showerror("Fehler", "Skript ungültig.")
                return
            with open(os.path.abspath(__file__), 'w', encoding='utf-8') as f:
                f.write(new_code)
            messagebox.showinfo("Update", "Tool aktualisiert. Startet neu!")
            os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
        except Exception as e:
            messagebox.showerror("Update fehlgeschlagen", f"Fehler:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ProxmoxToolbox(root)
    root.mainloop()
