import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import json
from proxmoxer import ProxmoxAPI
import urllib3

# Warnungen für selbstsignierte Zertifikate deaktivieren
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- KONFIGURATION ---
CONFIG_FILE = "proxmox_profiles.json"

# --- FARBEN (PROXMOX DARK MODE) ---
BG_MAIN = "#1a1c23"       
BG_SIDEBAR = "#21242d"    
BG_ELEMENTS = "#2b2f3a"   
FG_TEXT = "#e0e0e0"       
PX_ORANGE = "#e36b22"     
GREEN = "#2ecc71"
RED = "#e74c3c"
YELLOW = "#f1c40f"

class ProxmoxToolbox:
    def __init__(self, root):
        self.root = root
        self.root.title("Proxmox Toolbox Pro")
        self.root.geometry("1000x700")
        self.root.configure(bg=BG_MAIN)
        
        # Profile laden
        self.profiles = self.load_profiles_from_file()
        self.proxmox = None
        self.connected_host = None

        # --- STYLING ---
        self.style = ttk.Style()
        self.style.theme_use("default")
        
        self.style.configure("Treeview", background=BG_ELEMENTS, foreground=FG_TEXT, fieldbackground=BG_ELEMENTS, borderwidth=0)
        self.style.map('Treeview', background=[('selected', PX_ORANGE)])
        self.style.configure("Treeview.Heading", background=BG_SIDEBAR, foreground=FG_TEXT, relief="flat", font=("Arial", 10, "bold"))
        self.style.map("Treeview.Heading", background=[('active', BG_MAIN)])
        self.style.configure("TCombobox", fieldbackground=BG_ELEMENTS, background=BG_SIDEBAR, foreground="white")
        self.style.configure("Orange.Horizontal.TProgressbar", background=PX_ORANGE, troughcolor=BG_ELEMENTS, bordercolor=BG_MAIN, lightcolor=PX_ORANGE, darkcolor=PX_ORANGE)

        # --- GRID LAYOUT ---
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(self.root, bg=BG_SIDEBAR, width=250)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        # Scrollbarer Bereich für Main
        self.main_canvas = tk.Canvas(self.root, bg=BG_MAIN, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
        self.main_container = tk.Frame(self.main_canvas, bg=BG_MAIN)

        self.main_container.bind("<Configure>", lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all")))
        self.main_canvas.create_window((0, 0), window=self.main_container, anchor="nw", width=700)
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.main_canvas.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.scrollbar.grid(row=0, column=2, sticky="ns")

        # UI initialisieren
        self.show_sidebar_menu()
        self.show_settings_view() 

    # ==========================================
    # JSON PROFILE SPEICHERUNG
    # ==========================================
    def load_profiles_from_file(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)
            except Exception: return {}
        return {}

    def save_profiles_to_file(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(self.profiles, f, indent=4)
        except Exception as e: messagebox.showerror("Fehler", f"Konnte Profile nicht speichern:\n{e}")

    # ==========================================
    # SIDEBAR
    # ==========================================
    def show_sidebar_menu(self):
        for widget in self.sidebar.winfo_children(): widget.destroy()

        tk.Label(self.sidebar, text="Proxmox Toolbox", bg=BG_SIDEBAR, fg=PX_ORANGE, font=("Arial", 16, "bold")).pack(pady=(30, 5))
        
        status_text = f"Verbunden mit:\n{self.connected_host}" if self.proxmox else "Nicht verbunden"
        status_color = GREEN if self.proxmox else RED
        tk.Label(self.sidebar, text=status_text, bg=BG_SIDEBAR, fg=status_color, font=("Arial", 9, "italic")).pack(pady=(0, 20))

        btn_style = {"bg": BG_ELEMENTS, "fg": FG_TEXT, "relief": "flat", "font": ("Arial", 11), "cursor": "hand2"}
        
        tk.Button(self.sidebar, text="Verbindung & Profile", command=self.show_settings_view, **btn_style).pack(fill="x", padx=15, pady=5, ipady=4)
        
        if self.proxmox:
            tk.Button(self.sidebar, text="VMs auflisten", command=self.show_vm_view, **btn_style).pack(fill="x", padx=15, pady=5, ipady=4)
            tk.Button(self.sidebar, text="Node Status", command=self.show_node_status_view, **btn_style).pack(fill="x", padx=15, pady=5, ipady=4)
            tk.Button(self.sidebar, text="Logout", command=self.do_logout, bg=RED, fg="white", relief="flat", cursor="hand2").pack(side="bottom", fill="x", padx=15, pady=20, ipady=4)

    # ==========================================
    # MAIN VIEWS
    # ==========================================
    def show_settings_view(self):
        for widget in self.main_container.winfo_children(): widget.destroy()

        tk.Label(self.main_container, text="Verbindung & Profilverwaltung", bg=BG_MAIN, font=("Arial", 16, "bold"), fg=FG_TEXT).pack(anchor="w", pady=(0, 20))

        login_box = tk.LabelFrame(self.main_container, text=" Login ", bg=BG_MAIN, fg=PX_ORANGE, font=("Arial", 11, "bold"), padx=15, pady=15)
        login_box.pack(fill="x", pady=(0, 20))

        tk.Label(login_box, text="Profil wählen:", bg=BG_MAIN, fg=FG_TEXT).grid(row=0, column=0, sticky="w", pady=5)
        self.profile_var = tk.StringVar()
        self.profile_dropdown = ttk.Combobox(login_box, textvariable=self.profile_var, state="readonly", font=("Arial", 10))
        self.profile_dropdown.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        self.profile_dropdown.bind("<<ComboboxSelected>>", self.on_profile_select)

        tk.Label(login_box, text="Passwort:", bg=BG_MAIN, fg=FG_TEXT).grid(row=1, column=0, sticky="w", pady=5)
        self.entry_pw = tk.Entry(login_box, show="*", bg=BG_ELEMENTS, fg="white", insertbackground="white", relief="flat")
        self.entry_pw.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        
        self.btn_connect = tk.Button(login_box, text="Verbinden", command=self.do_login, bg=GREEN, fg="white", relief="flat", cursor="hand2", font=("Arial", 10, "bold"))
        self.btn_connect.grid(row=2, column=1, sticky="e", padx=10, pady=10, ipadx=15, ipady=2)
        login_box.grid_columnconfigure(1, weight=1)

        manage_box = tk.LabelFrame(self.main_container, text=" Profile verwalten ", bg=BG_MAIN, fg=PX_ORANGE, font=("Arial", 11, "bold"), padx=15, pady=15)
        manage_box.pack(fill="x")

        tk.Label(manage_box, text="Profil-Name:", bg=BG_MAIN, fg=FG_TEXT).grid(row=0, column=0, sticky="w", pady=5)
        self.entry_prof_name = tk.Entry(manage_box, bg=BG_ELEMENTS, fg="white", insertbackground="white", relief="flat")
        self.entry_prof_name.grid(row=0, column=1, sticky="ew", padx=10, pady=5)

        tk.Label(manage_box, text="Host (IP/FQDN):", bg=BG_MAIN, fg=FG_TEXT).grid(row=1, column=0, sticky="w", pady=5)
        self.entry_prof_host = tk.Entry(manage_box, bg=BG_ELEMENTS, fg="white", insertbackground="white", relief="flat")
        self.entry_prof_host.grid(row=1, column=1, sticky="ew", padx=10, pady=5)

        tk.Label(manage_box, text="Benutzer:", bg=BG_MAIN, fg=FG_TEXT).grid(row=2, column=0, sticky="w", pady=5)
        self.entry_prof_user = tk.Entry(manage_box, bg=BG_ELEMENTS, fg="white", insertbackground="white", relief="flat")
        self.entry_prof_user.grid(row=2, column=1, sticky="ew", padx=10, pady=5)

        btn_action_frame = tk.Frame(manage_box, bg=BG_MAIN)
        btn_action_frame.grid(row=3, column=1, sticky="e", padx=10, pady=10)
        
        tk.Button(btn_action_frame, text="Löschen", command=self.delete_profile, bg=RED, fg="white", relief="flat", cursor="hand2").pack(side="left", padx=5, ipady=2, ipadx=10)
        tk.Button(btn_action_frame, text="Speichern", command=self.save_profile, bg=PX_ORANGE, fg="white", relief="flat", cursor="hand2", font=("Arial", 10, "bold")).pack(side="left", padx=5, ipady=2, ipadx=10)
        
        manage_box.grid_columnconfigure(1, weight=1)
        self.update_profile_dropdown()

    def show_vm_view(self):
        if not self.proxmox: return

        for widget in self.main_container.winfo_children(): widget.destroy()

        header = tk.Frame(self.main_container, bg=BG_MAIN)
        header.pack(fill="x", pady=(0, 15))
        tk.Label(header, text="Virtuelle Maschinen", bg=BG_MAIN, font=("Arial", 16, "bold"), fg=FG_TEXT).pack(side="left")
        tk.Button(header, text="Aktualisieren", command=self.load_vms, bg=PX_ORANGE, fg="white", relief="flat", cursor="hand2").pack(side="right", ipady=2, ipadx=10)

        # Tabelle anpassen (Breiten und Ankerpunkte)
        columns = ("ID", "Name", "Status", "Node")
        self.tree = ttk.Treeview(self.main_container, columns=columns, show="headings", style="Treeview", height=15)
        
        self.tree.heading("ID", text="ID")
        self.tree.column("ID", width=60, anchor="center", stretch=False)
        
        self.tree.heading("Name", text="Name")
        self.tree.column("Name", width=250, anchor="w", stretch=True)
        
        self.tree.heading("Status", text="Status")
        self.tree.column("Status", width=100, anchor="center", stretch=False)
        
        self.tree.heading("Node", text="Node")
        self.tree.column("Node", width=150, anchor="w", stretch=False)
        
        self.tree.pack(fill="both", expand=True, pady=(0, 15))
        
        # Event für das Auswählen einer VM binden
        self.tree.bind("<<TreeviewSelect>>", self.on_vm_select)

        # VM Aktions-Buttons (initial deaktiviert)
        action_frame = tk.Frame(self.main_container, bg=BG_MAIN)
        action_frame.pack(fill="x")
        
        tk.Label(action_frame, text="Ausgewählte VM:", bg=BG_MAIN, fg=FG_TEXT).pack(side="left", padx=(0, 10))
        
        self.btn_vm_start = tk.Button(action_frame, text="Start", command=lambda: self.vm_action("start"), bg=BG_ELEMENTS, fg="white", relief="flat", font=("Arial", 9, "bold"), state="disabled")
        self.btn_vm_start.pack(side="left", padx=5, ipadx=10, ipady=2)
        
        self.btn_vm_shutdown = tk.Button(action_frame, text="Shutdown", command=lambda: self.vm_action("shutdown"), bg=BG_ELEMENTS, fg="white", relief="flat", font=("Arial", 9, "bold"), state="disabled")
        self.btn_vm_shutdown.pack(side="left", padx=5, ipadx=10, ipady=2)
        
        self.btn_vm_kill = tk.Button(action_frame, text="Kill", command=lambda: self.vm_action("stop"), bg=BG_ELEMENTS, fg="white", relief="flat", font=("Arial", 9, "bold"), state="disabled")
        self.btn_vm_kill.pack(side="left", padx=5, ipadx=10, ipady=2)

        self.load_vms()

    def show_node_status_view(self):
        if not self.proxmox: return

        for widget in self.main_container.winfo_children(): widget.destroy()

        # Header mit Aktualisieren-Button
        header = tk.Frame(self.main_container, bg=BG_MAIN)
        header.pack(fill="x", pady=(0, 20))
        tk.Label(header, text="Node Dashboard", bg=BG_MAIN, font=("Arial", 16, "bold"), fg=FG_TEXT).pack(side="left")
        tk.Button(header, text="Aktualisieren", command=self.load_node_stats, bg=PX_ORANGE, fg="white", relief="flat", cursor="hand2").pack(side="right", ipady=2, ipadx=10)

        control_frame = tk.Frame(self.main_container, bg=BG_MAIN)
        control_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(control_frame, text="Node auswählen:", bg=BG_MAIN, fg=FG_TEXT, font=("Arial", 11)).pack(side="left", padx=(0, 10))
        
        self.node_var = tk.StringVar()
        self.node_dropdown = ttk.Combobox(control_frame, textvariable=self.node_var, state="readonly", font=("Arial", 11))
        self.node_dropdown.pack(side="left")
        self.node_dropdown.bind("<<ComboboxSelected>>", self.load_node_stats)

        self.stats_frame = tk.Frame(self.main_container, bg=BG_ELEMENTS, padx=20, pady=20)
        self.stats_frame.pack(fill="x")

        self.populate_node_dropdown()

    # ==========================================
    # LOGIK & EVENTS
    # ==========================================
    def update_profile_dropdown(self):
        names = list(self.profiles.keys())
        self.profile_dropdown['values'] = names
        if names:
            self.profile_dropdown.set(names[0])
            self.on_profile_select()
        else:
            self.profile_dropdown.set("")

    def on_profile_select(self, event=None):
        name = self.profile_var.get()
        if name in self.profiles:
            prof = self.profiles[name]
            self.entry_prof_name.delete(0, tk.END)
            self.entry_prof_name.insert(0, name)
            self.entry_prof_host.delete(0, tk.END)
            self.entry_prof_host.insert(0, prof['host'])
            self.entry_prof_user.delete(0, tk.END)
            self.entry_prof_user.insert(0, prof['user'])

    def save_profile(self):
        name = self.entry_prof_name.get().strip()
        host = self.entry_prof_host.get().strip()
        user = self.entry_prof_user.get().strip()

        if not name or not host or not user:
            messagebox.showwarning("Eingabe fehlt", "Bitte alle Felder ausfüllen.")
            return

        self.profiles[name] = {"host": host, "user": user}
        self.save_profiles_to_file()
        self.update_profile_dropdown()
        self.profile_dropdown.set(name)
        messagebox.showinfo("Erfolg", f"Profil '{name}' gespeichert.")

    def delete_profile(self):
        name = self.profile_var.get()
        if not name or name not in self.profiles: return
        if messagebox.askyesno("Löschen", f"Profil '{name}' wirklich löschen?"):
            del self.profiles[name]
            self.save_profiles_to_file()
            self.update_profile_dropdown()

    def do_login(self):
        name = self.profile_var.get()
        password = self.entry_pw.get()

        if not name or name not in self.profiles: return
        if not password:
            messagebox.showwarning("Fehler", "Bitte Passwort eingeben.")
            return

        prof = self.profiles[name]
        try:
            self.proxmox = ProxmoxAPI(prof['host'], user=prof['user'], password=password, verify_ssl=False)
            self.proxmox.version.get()
            self.connected_host = prof['host']
            self.show_sidebar_menu() 
            self.show_vm_view() 
        except Exception as e:
            self.proxmox = None
            self.connected_host = None
            messagebox.showerror("Login Fehler", f"Verbindung fehlgeschlagen:\n{str(e)}")

    def do_logout(self):
        self.proxmox = None
        self.connected_host = None
        self.show_sidebar_menu()
        self.show_settings_view()

    # --- PROXMOX VM DATA & ACTIONS ---
    def reset_vm_buttons(self):
        # Setzt alle Buttons auf inaktiv zurück
        try:
            self.btn_vm_start.config(state="disabled", bg=BG_ELEMENTS, cursor="arrow")
            self.btn_vm_shutdown.config(state="disabled", bg=BG_ELEMENTS, fg="white", cursor="arrow")
            self.btn_vm_kill.config(state="disabled", bg=BG_ELEMENTS, cursor="arrow")
        except AttributeError:
            pass

    def on_vm_select(self, event):
        selected = self.tree.focus()
        if not selected:
            self.reset_vm_buttons()
            return
            
        values = self.tree.item(selected, 'values')
        if not values: return
        
        status = values[2].lower()
        
        # Logik für das Einfärben/Aktivieren
        if status == "running":
            self.btn_vm_start.config(state="disabled", bg=BG_ELEMENTS, cursor="arrow")
            self.btn_vm_shutdown.config(state="normal", bg=YELLOW, fg="black", cursor="hand2")
            self.btn_vm_kill.config(state="normal", bg=RED, fg="white", cursor="hand2")
        else:
            self.btn_vm_start.config(state="normal", bg=GREEN, fg="white", cursor="hand2")
            self.btn_vm_shutdown.config(state="disabled", bg=BG_ELEMENTS, fg="white", cursor="arrow")
            self.btn_vm_kill.config(state="disabled", bg=BG_ELEMENTS, fg="white", cursor="arrow")

    def load_vms(self):
        if not self.proxmox: return
        self.reset_vm_buttons() # Buttons beim Aktualisieren zurücksetzen
        for item in self.tree.get_children(): self.tree.delete(item)
        try:
            for node in self.proxmox.nodes.get():
                node_name = node['node']
                if node.get('status') != 'online': continue
                try:
                    for vm in self.proxmox.nodes(node_name).qemu.get():
                        self.tree.insert("", "end", values=(vm.get("vmid"), vm.get("name"), vm.get("status"), node_name))
                except Exception: pass
        except Exception as e: messagebox.showerror("Fehler", f"Laden fehlgeschlagen:\n{e}")

    def vm_action(self, action):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Fehler", "Bitte wähle zuerst eine VM aus.")
            return
            
        values = self.tree.item(selected, 'values')
        vmid = values[0]
        node = values[3]
        
        try:
            if action == "start":
                self.proxmox.nodes(node).qemu(vmid).status.start.post()
            elif action == "shutdown":
                self.proxmox.nodes(node).qemu(vmid).status.shutdown.post()
            elif action == "stop":
                if not messagebox.askyesno("Sicherheit", f"VM {vmid} wirklich hart ausschalten (Kill)?"): return
                self.proxmox.nodes(node).qemu(vmid).status.stop.post()
                
            messagebox.showinfo("Befehl gesendet", f"Befehl an VM {vmid} gesendet.\nEs kann einen Moment dauern, bis der Status sich ändert.")
            self.load_vms()
        except Exception as e:
            messagebox.showerror("Fehler", f"Aktion fehlgeschlagen:\n{e}")

    # --- PROXMOX STATS DATA ---
    def populate_node_dropdown(self):
        if not self.proxmox: return
        try:
            node_names = [n['node'] for n in self.proxmox.nodes.get() if n.get('status') == 'online']
            self.node_dropdown['values'] = node_names
            if node_names:
                self.node_dropdown.set(node_names[0])
                self.load_node_stats()
        except Exception as e: print(e)

    def load_node_stats(self, event=None):
        node = self.node_var.get()
        if not node or not self.proxmox: return
        for widget in self.stats_frame.winfo_children(): widget.destroy()

        try:
            status = self.proxmox.nodes(node).status.get()
            version_info = self.proxmox.version.get()
            storages = self.proxmox.nodes(node).storage.get()

            tk.Label(self.stats_frame, text=f"Proxmox Version: {version_info.get('release')} (v{version_info.get('version')})", bg=BG_ELEMENTS, fg=PX_ORANGE, font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 15))

            def create_stat_bar(label, used, total, is_percent=False):
                frame = tk.Frame(self.stats_frame, bg=BG_ELEMENTS)
                frame.pack(fill="x", pady=5)
                percent = (used / total) * 100 if total > 0 else 0
                text = f"{label}: {percent:.1f}%" if is_percent else f"{label}: {used/(1024**3):.1f} GB belegt / {total/(1024**3):.1f} GB gesamt ({percent:.1f}%)"
                tk.Label(frame, text=text, bg=BG_ELEMENTS, fg=FG_TEXT, font=("Arial", 10)).pack(anchor="w")
                bar = ttk.Progressbar(frame, style="Orange.Horizontal.TProgressbar", length=400, mode='determinate')
                bar.pack(fill="x", pady=(2, 10))
                bar['value'] = percent

            create_stat_bar("CPU Auslastung", status.get('cpu', 0), 1.0, is_percent=True)
            create_stat_bar("RAM Auslastung", status.get('memory', {}).get('used', 0), status.get('memory', {}).get('total', 1))
            
            tk.Frame(self.stats_frame, height=1, bg=BG_MAIN).pack(fill="x", pady=15)
            tk.Label(self.stats_frame, text="Verfügbare Storages:", bg=BG_ELEMENTS, fg=PX_ORANGE, font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 10))

            for st in storages:
                if st.get('active') == 1 and st.get('total', 0) > 0:
                    create_stat_bar(f"Storage: {st.get('storage')}", st.get('used', 0), st.get('total', 1))

            tk.Frame(self.stats_frame, height=1, bg=BG_MAIN).pack(fill="x", pady=15)
            btn_frame = tk.Frame(self.stats_frame, bg=BG_ELEMENTS)
            btn_frame.pack(fill="x", pady=(10, 0))
            tk.Button(btn_frame, text="Wartungsmodus umschalten (HA)", command=lambda: self.toggle_maintenance(node), bg=RED, fg="white", relief="flat", cursor="hand2", font=("Arial", 10, "bold")).pack(side="left", ipady=4, ipadx=10)

        except Exception as e:
            tk.Label(self.stats_frame, text=f"Fehler beim Laden der Stats:\n{e}", bg=BG_ELEMENTS, fg=RED).pack()

    def toggle_maintenance(self, node):
        if not messagebox.askyesno("Sicherheitsabfrage", f"HA-Wartungsstatus für '{node}' umschalten?"): return
        try:
            current_state = self.proxmox.cluster.ha.nodes(node).get()
            new_state = "online" if current_state.get('state') == "maintenance" else "maintenance"
            self.proxmox.cluster.ha.nodes(node).put(state=new_state)
            messagebox.showinfo("Erfolg", f"Node '{node}' ist nun: {new_state}")
        except Exception as e:
            messagebox.showwarning("Hinweis", f"Wartungsmodus konnte nicht gesetzt werden.\nDetails: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ProxmoxToolbox(root)
    root.mainloop()
