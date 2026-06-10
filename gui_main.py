"""
Crafted by Mehrdad Y. Kalhori, straight out of the Wild West of Lorestan, Iran 🤠
GUI and Visualization Engine for Holographic Optical Tweezers Studio
Handles CustomTkinter interface, Matplotlib real-time rendering, and user interactions.
"""

import numpy as np
import customtkinter as ctk
import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.animation as animation
import warnings
import csv
from tkinter import messagebox
import os
import threading
import time

# وارد کردن هسته فیزیکی از فایل مجزا
from physics_engine import OpticalTweezersSimulation

try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

warnings.filterwarnings("ignore", category=UserWarning)

CMAP_GREEN = LinearSegmentedColormap.from_list('argon_green', ['#000000', '#004411', '#00ff44', '#ffffff'])
CMAP_RED = LinearSegmentedColormap.from_list('ti_sapphire', ['#000000', '#550000', '#ff2222', '#ffffff'])

# ==========================================
# 0. INTERACTIVE TOOLTIP WIDGET
# ==========================================
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tw = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tw, text=self.text, justify='left',
                         background="#1a1a1a", foreground="#10b981", 
                         relief='solid', borderwidth=1,
                         font=("Consolas", 11, "bold"), padx=8, pady=5)
        label.pack()

    def leave(self, event=None):
        if self.tw:
            self.tw.destroy()
            self.tw = None

# ==========================================
# 2. THE ULTIMATE GUI (CUSTOMTKINTER)
# ==========================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AdvancedTweezersApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Optical Tweezers Studio - Ultimate Photonics Edition")
        self.geometry("1550x900")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.gs_cache_field = None
        self.gs_cache_phase = None
        self.aberration_phase = None 
        self.aberration_coeff_val = 0.0 
        self.last_beep = 0
        self.cb_phase = None 

        self.setup_sidebar()
        self.setup_main_tabs()
        
        self.ani_mc = None 
        self.ani_micro = None
        self.update_topo_plot()

    def get_laser_properties(self):
        choice = self.laser_var.get()
        if "1064" in choice: return 1064e-9, 0.05
        elif "700" in choice: return 700e-9, 0.12
        else: return 532e-9, 0.28

    def beep_geiger(self):
        if HAS_SOUND and self.audio_var.get() == "On":
            current_time = time.time()
            if current_time - self.last_beep > 0.1: 
                threading.Thread(target=winsound.Beep, args=(3000, 50), daemon=True).start()
                self.last_beep = current_time

    def create_header_with_tooltip(self, parent, title_text, tooltip_text, color):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(pady=(15, 0), fill="x")
        lbl = ctk.CTkLabel(frame, text=title_text, font=("Arial", 12, "bold"), text_color=color)
        lbl.pack(side="left")
        info = ctk.CTkLabel(frame, text=" [?]", text_color=color, font=("Arial", 12, "bold"), cursor="hand2")
        info.pack(side="left", padx=(5, 0))
        ToolTip(info, tooltip_text)

    def setup_sidebar(self):
        self.sidebar = ctk.CTkScrollableFrame(self, width=320, corner_radius=10, fg_color="#141414")
        self.sidebar.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

        ctk.CTkLabel(self.sidebar, text="LAB CONTROLS", font=("Arial", 20, "bold"), text_color="#4da6ff").pack(pady=(10, 20))

        # --- 1. Laser Source & Beam Type ---
        ctk.CTkLabel(self.sidebar, text="Laser Source & Beam", font=("Arial", 12, "bold"), text_color="#38bdf8").pack(pady=(5,0))
        self.laser_var = ctk.StringVar(value="Nd:YAG (1064 nm)")
        self.laser_menu = ctk.CTkOptionMenu(self.sidebar, variable=self.laser_var, 
                          values=["Nd:YAG (1064 nm)", "Ti:Sapphire (700 nm)", "Argon Green (532 nm)"], 
                          fg_color="#0284c7", button_color="#0369a1", command=self.on_sidebar_change_callback)
        self.laser_menu.pack(pady=3)

        self.beam_var = ctk.StringVar(value="Gaussian")
        self.beam_menu = ctk.CTkOptionMenu(self.sidebar, variable=self.beam_var, values=["Gaussian", "Vortex (OAM)"], command=self.on_sidebar_change_callback)
        self.beam_menu.pack(pady=3)

        # --- 2. Particle Mix ---
        self.create_header_with_tooltip(self.sidebar, "Particle Population", 
            "Rayleigh Regime (a << \u03BB): Gradient force dominates.\nMie Regime (a > \u03BB): Radiation pressure pushes\nparticle along the beam propagation.", "#ffea00")
        self.mix_var = ctk.StringVar(value="Uniform (Rayleigh)")
        self.mix_menu = ctk.CTkOptionMenu(self.sidebar, variable=self.mix_var, values=["Uniform (Rayleigh)", "Mixed (Rayleigh + Mie)"], 
                          fg_color="#ffaa00", button_color="#cc8800", button_hover_color="#b37700", command=self.on_mix_change_callback)
        self.mix_menu.pack(pady=5)

        # --- 3. Objective NA ---
        self.create_header_with_tooltip(self.sidebar, "Lens Optics (Radiation Pressure)", 
            "Numerical Aperture (NA = n\u00B7sin\u03B8)\nDetermines focal spot size and gradient force.\nWarning: NA > 1.33 requires immersion media.", "#10b981")
        self.lbl_na = ctk.CTkLabel(self.sidebar, text="Objective NA: 1.20", font=("Arial", 13))
        self.lbl_na.pack()
        self.na_slider = ctk.CTkSlider(self.sidebar, from_=0.6, to=1.4, command=self.on_sidebar_change_callback, button_color="#10b981", progress_color="#059669")
        self.na_slider.set(1.20)
        self.na_slider.pack(pady=5)

        # --- 4. Adaptive Optics ---
        self.create_header_with_tooltip(self.sidebar, "Adaptive Optics (Zernike)", 
            "Zernike Polynomial Phase Masks:\n• Spherical: 6\u03C1\u2074 - 6\u03C1\u00B2 + 1\n• Astigmatism: \u03C1\u00B2 cos(2\u03B8)\n• Coma: (3\u03C1\u00B3 - 2\u03C1) cos(\u03B8)", "#d946ef")
        self.zernike_type_var = ctk.StringVar(value="Spherical (Depth Mismatch)")
        self.zernike_type_menu = ctk.CTkOptionMenu(self.sidebar, variable=self.zernike_type_var, 
                          values=["Spherical (Depth Mismatch)", "Astigmatism (Tilted Sample)", "Coma (Misaligned)"], 
                          fg_color="#c026d3", button_color="#a21caf", button_hover_color="#86198f", command=self.on_sidebar_change_callback)
        self.zernike_type_menu.pack(pady=3)
        
        self.lbl_depth = ctk.CTkLabel(self.sidebar, text="Aberration Intensity: 0", font=("Arial", 13))
        self.lbl_depth.pack()
        self.depth_slider = ctk.CTkSlider(self.sidebar, from_=0, to=50, command=self.on_sidebar_change_callback, button_color="#d946ef", progress_color="#c026d3")
        self.depth_slider.set(0)
        self.depth_slider.pack(pady=5)
        
        self.zernike_var = ctk.StringVar(value="Off")
        self.zernike_switch = ctk.CTkSwitch(self.sidebar, text="Apply Phase Correction", variable=self.zernike_var, onvalue="On", offvalue="Off", progress_color="#10b981", command=self.on_sidebar_change_callback)
        self.zernike_switch.pack(pady=5)

        # --- 5. Laser Power & Environment ---
        self.lbl_power = ctk.CTkLabel(self.sidebar, text="Laser Power: 200 mW", font=("Arial", 13))
        self.lbl_power.pack(pady=(15, 0))
        self.power_slider = ctk.CTkSlider(self.sidebar, from_=0, to=1000, command=self.on_sidebar_change_callback, progress_color="#ff4d4d")
        self.power_slider.set(200)
        self.power_slider.pack(pady=5)
        
        # Turbidity with Tooltip
        frame_scatter = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        frame_scatter.pack(pady=(15, 0))
        self.lbl_scattering = ctk.CTkLabel(frame_scatter, text="Tissue Turbidity (\u03BC_s): 0 mm^-1", font=("Arial", 13))
        self.lbl_scattering.pack(side="left")
        info_scatter = ctk.CTkLabel(frame_scatter, text=" [?]", text_color="#10b981", font=("Arial", 12, "bold"), cursor="hand2")
        info_scatter.pack(side="left")
        ToolTip(info_scatter, "Beer-Lambert Law: I(z) = I\u2080 exp(-\u03BC_s\u00B7z)\nSimulates photon scattering and optical\npower loss in deep biological tissues.")

        self.scatter_slider = ctk.CTkSlider(self.sidebar, from_=0, to=50, command=self.on_sidebar_change_callback)
        self.scatter_slider.set(0)
        self.scatter_slider.pack(pady=5)

        self.lbl_radius = ctk.CTkLabel(self.sidebar, text="Base Radius (Rayleigh): 150 nm", font=("Arial", 13))
        self.lbl_radius.pack(pady=(15, 0))
        self.radius_slider = ctk.CTkSlider(self.sidebar, from_=50, to=500, command=self.on_sidebar_change_callback)
        self.radius_slider.set(150)
        self.radius_slider.pack(pady=5)
        
        # Fluid Drag with Tooltip
        frame_fluid = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        frame_fluid.pack(pady=(15, 0))
        self.lbl_fluid = ctk.CTkLabel(frame_fluid, text="Fluid Drag: 0 μm/s", text_color="#00ffcc", font=("Arial", 13, "bold"))
        self.lbl_fluid.pack(side="left")
        info_fluid = ctk.CTkLabel(frame_fluid, text=" [?]", text_color="#00ffcc", font=("Arial", 12, "bold"), cursor="hand2")
        info_fluid.pack(side="left")
        ToolTip(info_fluid, "Stokes' Law: F_drag = 6\u03C0\u00B7\u03B7\u00B7r\u00B7v\nSimulates micro-fluidic flow pushing\nthe particle out of the optical trap.")

        self.fluid_slider = ctk.CTkSlider(self.sidebar, from_=0, to=100, button_color="#00ffcc", button_hover_color="#00ccaa", command=self.on_sidebar_change_callback)
        self.fluid_slider.set(0)
        self.fluid_slider.pack(pady=5)

        self.audio_var = ctk.StringVar(value="Off")
        self.audio_switch = ctk.CTkSwitch(self.sidebar, text="☢️ Geiger Audio Counter", variable=self.audio_var, onvalue="On", offvalue="Off", progress_color="#ff4444")
        self.audio_switch.pack(pady=(20, 10))
        
        # --- Export & Controls ---
        ctk.CTkLabel(self.sidebar, text="─" * 30, text_color="#333333").pack(pady=5)
        
        self.reset_btn = ctk.CTkButton(self.sidebar, text="🔄 Reset Configuration", font=("Arial", 13, "bold"), fg_color="#d35400", hover_color="#e67e22", command=self.reset_to_defaults)
        self.reset_btn.pack(pady=5, fill="x", padx=10)
        
        self.comsol_btn = ctk.CTkButton(self.sidebar, text="⚙️ Export 3D for COMSOL", fg_color="#17a2b8", hover_color="#138496", command=self.export_comsol)
        self.comsol_btn.pack(pady=5, fill="x", padx=10)
        self.export_btn = ctk.CTkButton(self.sidebar, text="💾 Save UI Params (CSV)", fg_color="#28a745", hover_color="#218838", command=self.export_data)
        self.export_btn.pack(pady=5, fill="x", padx=10)
        self.exit_btn = ctk.CTkButton(self.sidebar, text="🚪 Exit Studio", fg_color="#dc3545", hover_color="#c82333", command=self.close_app)
        self.exit_btn.pack(pady=(20, 10), fill="x", padx=10)

        ctk.CTkLabel(self.sidebar, text="Developed by M Y. K", font=("Arial", 11, "italic"), text_color="#666666").pack(side="bottom", pady=(10, 5))

    def reset_to_defaults(self):
        if self.ani_mc is not None: self.ani_mc.event_source.stop()
        if self.ani_micro is not None: self.ani_micro.event_source.stop()
        
        self.laser_var.set("Nd:YAG (1064 nm)")
        self.beam_var.set("Gaussian")
        self.mix_var.set("Uniform (Rayleigh)")
        self.zernike_type_var.set("Spherical (Depth Mismatch)")
        self.pattern_var.set("4 Traps (Square)")
        self.pattern_menu.configure(variable=self.pattern_var)
        
        self.na_slider.set(1.20)
        self.depth_slider.set(0)
        self.zernike_var.set("Off")
        self.zernike_switch.deselect()
        self.power_slider.set(200)
        self.scatter_slider.set(0)
        self.radius_slider.set(150)
        self.fluid_slider.set(0)
        self.audio_var.set("Off")
        self.audio_switch.deselect()
        
        self.on_slider_change()
        self.calculate_gs(self.pattern_var.get())
        
        self.run_monte_carlo()
        self.run_microscope()
        
        messagebox.showinfo("Lab Reset", "All system configurations successfully restored to baseline.")

    def export_comsol(self):
        filename = "COMSOL_Optical_Field.txt"
        try:
            power = self.power_slider.get() * 1e-3  
            radius = self.radius_slider.get() * 1e-9 
            mu_s = self.scatter_slider.get() * 1e3 
            mode = self.beam_var.get()
            wl, _ = self.get_laser_properties()
            lens_na = self.na_slider.get()
            waist = wl / (2 * lens_na)
            sim = OpticalTweezersSimulation(wl, power, waist, 1.33, 1.50, radius, mode, mu_s)
            
            grid_pts = 30
            lim = 2e-6
            z_lim = 5e-6
            x = np.linspace(-lim, lim, grid_pts)
            y = np.linspace(-lim, lim, grid_pts)
            z = np.linspace(-z_lim, z_lim, grid_pts)
            X, Y, Z = np.meshgrid(x, y, z, indexing='ij')
            Intensity, _ = sim.calculate_intensity(X, Y, Z)
            
            with open(filename, mode='w') as file:
                file.write("% x (m) \t y (m) \t z (m) \t Intensity (W/m^2)\n")
                for i in range(grid_pts):
                    for j in range(grid_pts):
                        for k in range(grid_pts):
                            file.write(f"{X[i,j,k]:.6e}\t{Y[i,j,k]:.6e}\t{Z[i,j,k]:.6e}\t{Intensity[i,j,k]:.6e}\n")
            messagebox.showinfo("COMSOL Export Ready", f"3D Field Data formatted for COMSOL Interpolation.\nSaved to: {os.path.abspath(filename)}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def export_data(self):
        filename = "tweezers_parameters.csv"
        try:
            with open(filename, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Parameter", "Value", "Unit"])
                writer.writerow(["Laser Type", self.laser_var.get(), "-"])
                writer.writerow(["Beam Mode", self.beam_var.get(), "-"])
                writer.writerow(["Laser Power", f"{self.power_slider.get():.2f}", "mW"])
                writer.writerow(["Parameter Radius", f"{self.radius_slider.get():.2f}", "nm"])
            messagebox.showinfo("Export Successful", f"Data saved to:\n{os.path.abspath(filename)}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def close_app(self):
        if messagebox.askyesno("Exit Studio", "Close the application?"):
            if self.ani_mc is not None: self.ani_mc.event_source.stop()
            if self.ani_micro is not None: self.ani_micro.event_source.stop()
            self.quit()
            self.destroy()
            os._exit(0)

    def on_sidebar_change_callback(self, *args):
        self.on_slider_change()
        
    def on_mix_change_callback(self, choice):
        self.on_slider_change()
        active_tab = self.tabview.get() if hasattr(self, 'tabview') else ""
        if active_tab == "Photothermal Langevin Dynamics":
            self.run_monte_carlo()

    def setup_main_tabs(self):
        self.tabview = ctk.CTkTabview(self, corner_radius=10, fg_color="#1a1a1a", command=self.on_tab_change)
        self.tabview.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="nsew")

        self.tab_topo = self.tabview.add("Topology (Tissue Interaction)")
        self.tab_micro = self.tabview.add("Virtual Microscope")
        self.tab_mc = self.tabview.add("Photothermal Langevin Dynamics")
        self.tab_holo = self.tabview.add("Holographic Array (SLM)")

        # --- Tab 1: Topology ---
        self.fig_topo = plt.Figure(figsize=(10, 6), facecolor='#1e1e1e')
        gs = self.fig_topo.add_gridspec(2, 2, width_ratios=[1, 1.15], wspace=0.3, hspace=0.4)
        self.ax_cross = self.fig_topo.add_subplot(gs[0, 0])
        self.ax_quiver = self.fig_topo.add_subplot(gs[1, 0])
        self.ax_3d = self.fig_topo.add_subplot(gs[:, 1], projection='3d')
        for ax in [self.ax_cross, self.ax_quiver, self.ax_3d]: ax.set_facecolor('#1e1e1e')
        self.canvas_topo = FigureCanvasTkAgg(self.fig_topo, master=self.tab_topo)
        self.canvas_topo.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # --- Tab 2: Virtual Microscope ---
        self.btn_run_micro = ctk.CTkButton(self.tab_micro, text="Start Microscope Camera", command=self.run_microscope, font=("Arial", 14, "bold"))
        self.btn_run_micro.pack(pady=10)
        self.fig_micro, self.ax_micro = plt.subplots(figsize=(8, 6), facecolor='#000000')
        self.ax_micro.set_facecolor('#000000')
        self.canvas_micro = FigureCanvasTkAgg(self.fig_micro, master=self.tab_micro)
        self.canvas_micro.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # --- Tab 3: Monte Carlo ---
        self.mc_io_frame = ctk.CTkFrame(self.tab_mc, fg_color="transparent")
        self.mc_io_frame.pack(fill="x", padx=10, pady=5)
        
        self.btn_run_mc = ctk.CTkButton(self.mc_io_frame, text="Restart Live Tracking Data", command=self.run_monte_carlo, font=("Arial", 14, "bold"))
        self.btn_run_mc.pack(pady=5, fill="x")
        
        self.ctk_metrics_label = ctk.CTkLabel(self.mc_io_frame, text="Langevin Diagnostics Dashboard (Awaiting Stream...)", 
                                             font=("Consolas", 13), text_color="#00ffcc", anchor="w", justify="left",
                                             fg_color="#0a0a0a", corner_radius=8, padx=15, pady=12)
        self.ctk_metrics_label.pack(fill="x", expand=True, pady=5)

        self.fig_mc = plt.Figure(figsize=(10, 4.5), facecolor='#1e1e1e')
        gs_mc = self.fig_mc.add_gridspec(1, 2, width_ratios=[2.5, 1], wspace=0.25)
        self.ax_mc = self.fig_mc.add_subplot(gs_mc[0])
        self.ax_hist = self.fig_mc.add_subplot(gs_mc[1])
        
        self.canvas_mc = FigureCanvasTkAgg(self.fig_mc, master=self.tab_mc)
        self.canvas_mc.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # --- Tab 4: Holographic Array ---
        self.holo_control_frame = ctk.CTkFrame(self.tab_holo, fg_color="transparent")
        self.holo_control_frame.pack(pady=10)
        ctk.CTkLabel(self.holo_control_frame, text="Select GS Hologram Pattern:", font=("Arial", 14)).pack(side="left", padx=10)
        self.pattern_var = ctk.StringVar(value="4 Traps (Square)")
        self.pattern_menu = ctk.CTkOptionMenu(self.holo_control_frame, variable=self.pattern_var, values=["1 Trap (Center)", "2 Traps (Line)", "4 Traps (Square)", "8 Traps (Ring)"], command=self.calculate_gs_callback)
        self.pattern_menu.pack(side="left", padx=10)
        
        self.fig_holo = plt.Figure(figsize=(12, 4.5), facecolor='#1e1e1e')
        gs_holo = self.fig_holo.add_gridspec(1, 3, wspace=0.3)
        self.ax_target = self.fig_holo.add_subplot(gs_holo[0])
        self.ax_phase = self.fig_holo.add_subplot(gs_holo[1])
        self.ax_holo_3d = self.fig_holo.add_subplot(gs_holo[2], projection='3d')
        for ax in [self.ax_target, self.ax_phase, self.ax_holo_3d]: ax.set_facecolor('#1e1e1e')
        self.canvas_holo = FigureCanvasTkAgg(self.fig_holo, master=self.tab_holo)
        self.canvas_holo.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        
        self.calculate_gs(self.pattern_var.get())

    def calculate_gs_callback(self, choice):
        self.calculate_gs(choice)
        self.update_topo_plot()

    def on_tab_change(self):
        current_tab = self.tabview.get()
        if self.ani_micro is not None:
            if current_tab == "Virtual Microscope":
                self.ani_micro.event_source.start()
            else:
                self.ani_micro.event_source.stop()
                
        if self.ani_mc is not None:
            if current_tab == "Photothermal Langevin Dynamics":
                self.ani_mc.event_source.start()
            else:
                self.ani_mc.event_source.stop()

    # ==========================================
    # 3. ANALYSIS & ANIMATION ENGINE
    # ==========================================
    def update_topo_plot(self):
        power = self.power_slider.get() * 1e-3  
        radius = self.radius_slider.get() * 1e-9 
        mu_s = self.scatter_slider.get() * 1e3  
        mode = self.beam_var.get()
        wl, _ = self.get_laser_properties()
        lens_na = self.na_slider.get()
        waist = wl / (2 * lens_na) 
        
        grid = 50
        x = y = np.linspace(-2e-6, 2e-6, grid)
        X, Y = np.meshgrid(x, y)
        
        pattern = self.pattern_var.get()
        centers = []
        r_dist = 0.8e-6 
        
        if pattern == "1 Trap (Center)": centers.append((0, 0))
        elif pattern == "2 Traps (Line)": centers.extend([(-r_dist, 0), (r_dist, 0)])
        elif pattern == "4 Traps (Square)": centers.extend([(-r_dist, -r_dist), (r_dist, -r_dist), (-r_dist, r_dist), (r_dist, r_dist)])
        elif pattern == "8 Traps (Ring)":
            for angle in np.linspace(0, 2*np.pi, 8, endpoint=False):
                centers.append((r_dist * np.cos(angle), r_dist * np.sin(angle)))

        Total_Intensity = np.zeros_like(X)
        for cx, cy in centers:
            sim = OpticalTweezersSimulation(wl, power / len(centers), waist, 1.33, 1.50, radius, mode, mu_s)
            Int, _ = sim.calculate_intensity(X - cx, Y - cy, 1e-6)
            Total_Intensity += Int

        grad_coeff = sim.alpha / (2 * sim.c * sim.nm * sim.epsilon0)
        k_B_T = 1.38e-23 * 300
        Potential_Well = (-grad_coeff * Total_Intensity) / k_B_T
        
        true_min = np.min(Potential_Well)
        if true_min >= -0.1:
            z_min_bound = -50.0
        else:
            z_min_bound = true_min * 1.15 if true_min > -300 else true_min - (np.abs(true_min) ** 0.45) * 5.0
            
        z_max_bound = max(20.0, np.max(Potential_Well))
        
        dU_dy, dU_dx = np.gradient(Potential_Well)
        Fx, Fy = -dU_dx, -dU_dy
        Force_Mag_pN = np.hypot(Fx, Fy) * 1e12

        self.ax_cross.clear(); self.ax_quiver.clear(); self.ax_3d.clear()

        if wl == 532e-9:
            cmap_topo = 'viridis'
            line_color = '#00ffcc'
        elif wl == 700e-9:
            cmap_topo = 'magma'
            line_color = '#ff6666'
        else:
            cmap_topo = 'plasma'
            line_color = '#ff00ff'

        mid_idx = grid // 2
        u_1d = Potential_Well[mid_idx, :]
        self.ax_cross.plot(x * 1e6, u_1d, color=line_color, linewidth=2)
        self.ax_cross.set_title(f"Cross-Section: $U(r) = -\\sum \\frac{{\\alpha}}{{2cn_m\\epsilon_0}}I_i(r)$", color='white', fontsize=10)
        self.ax_cross.set_xlabel(r"Lateral Position $x$ ($\mu$m)", color='white', fontsize=9)
        self.ax_cross.set_ylabel(r"Potential Energy $U/k_B T$", color='white', fontsize=9)
        self.ax_cross.tick_params(colors='white')
        self.ax_cross.grid(True, alpha=0.1)
        self.ax_cross.set_ylim(z_min_bound, z_max_bound)
        
        skip = (slice(None, None, 4), slice(None, None, 4))
        q = self.ax_quiver.quiver(X[skip]*1e6, Y[skip]*1e6, Fx[skip], Fy[skip], Force_Mag_pN[skip], cmap=cmap_topo, scale=150, pivot='mid') 
        
        if not hasattr(self, 'cbar_force') or self.cbar_force is None:
            self.cbar_force = self.fig_topo.colorbar(q, ax=self.ax_quiver, fraction=0.046, pad=0.04)
            self.cbar_force.set_label('Force Magnitude (pN)', color='white', fontsize=8)
            self.cbar_force.ax.tick_params(colors='white', labelsize=8)
        else:
            self.cbar_force.update_normal(q)
            
        self.ax_quiver.set_title("Interference Force Field", color='white', fontsize=11)
        self.ax_quiver.set_xlabel(r"Lateral $x$ ($\mu$m)", color='white', fontsize=9)
        self.ax_quiver.set_ylabel(r"Lateral $y$ ($\mu$m)", color='white', fontsize=9)
        self.ax_quiver.tick_params(colors='white')

        self.ax_3d.set_box_aspect(aspect=(1, 1, 0.65)) 
        self.ax_3d.plot_surface(X * 1e6, Y * 1e6, Potential_Well, cmap=cmap_topo, edgecolor='none', alpha=0.9)
        self.ax_3d.set_title(f"3D Multi-Trap Cross-Talk Surface", color='white', fontsize=11)
        self.ax_3d.set_xlabel(r"$x$ ($\mu$m)", color='white', fontsize=9)
        self.ax_3d.set_ylabel(r"$y$ ($\mu$m)", color='white', fontsize=9)
        self.ax_3d.set_zlabel(r"Potential $U/k_B T$", color='white', fontsize=9)
        self.ax_3d.set_zlim(z_min_bound, z_max_bound)
        for axis in [self.ax_3d.xaxis, self.ax_3d.yaxis, self.ax_3d.zaxis]:
            axis.set_pane_color((0.12, 0.12, 0.12, 1.0))
        self.ax_3d.tick_params(axis='both', colors='white')
        
        self.fig_topo.subplots_adjust(top=0.84, bottom=0.14, left=0.12, right=0.96, wspace=0.38)
        self.ax_3d.set_position([0.50, 0.12, 0.44, 0.70])
        
        self.canvas_topo.draw()

    def run_microscope(self):
        if self.ani_micro is not None:
            self.ani_micro.event_source.stop()
        self.ax_micro.clear()
        self.ax_micro.set_xlim(-5, 5)
        self.ax_micro.set_ylim(-5, 5)
        self.ax_micro.set_title("Virtual Microscope UI", color='white', fontsize=14)
        self.ax_micro.axis('off')
        
        n_particles = 15
        particles_x = np.random.uniform(-4, 4, n_particles)
        particles_y = np.random.uniform(-4, 4, n_particles)
        
        x_mesh = np.linspace(-5, 5, 100)
        X_beam, Y_beam = np.meshgrid(x_mesh, x_mesh)
        R_sq_beam = X_beam**2 + Y_beam**2
        
        def get_laser_cmap():
            choice = self.laser_var.get()
            if "532" in choice: return CMAP_GREEN
            elif "700" in choice: return CMAP_RED
            return 'hot'

        self.laser_imshow = self.ax_micro.imshow(np.zeros((100, 100)), extent=[-5, 5, -5, 5], origin='lower', cmap=get_laser_cmap(), vmin=0, vmax=1, alpha=0.0, zorder=1)
        scatter = self.ax_micro.scatter(particles_x, particles_y, color='#00ffcc', edgecolors='white', zorder=5)

        def update_micro(frame):
            live_power = self.power_slider.get()
            base_radius = self.radius_slider.get()
            live_fluid_v = self.fluid_slider.get() * 0.01 
            mode = self.beam_var.get()
            is_mixed = self.mix_var.get() == "Mixed (Rayleigh + Mie)"
            wl, _ = self.get_laser_properties()
            
            self.laser_imshow.set_cmap(get_laser_cmap())
            if mode == "Gaussian":
                I_beam = np.exp(-2 * R_sq_beam / (1.5**2))
            else:
                I_beam = (R_sq_beam / 1.5**2) * np.exp(-2 * R_sq_beam / (1.5**2)) * 2.7
            self.laser_imshow.set_data(I_beam)
            self.laser_imshow.set_alpha(min(0.8, live_power / 1000 + 0.1))
            
            sizes = [base_radius * 10 if (is_mixed and i < 3) else base_radius for i in range(n_particles)]
            colors = ['#facc15' if (is_mixed and i < 3) else '#00ffcc' for i in range(n_particles)]
            scatter.set_sizes(sizes)
            scatter.set_color(colors)
            scatter.set_edgecolor('white')
            
            for i in range(n_particles):
                is_mie = (is_mixed and i < 3)
                noise_scale = 0.15 / np.sqrt(10.0 if is_mie else 1.0)
                dx = np.random.randn() * noise_scale
                dy = np.random.randn() * noise_scale
                dx += live_fluid_v 
                
                r = np.sqrt(particles_x[i]**2 + particles_y[i]**2)
                
                if live_power > 10:
                    pull_strength = (live_power / 1000) * 0.2 * (1064e-9 / wl) 
                    if is_mie: pull_strength *= 0.1 

                    if mode == "Gaussian" and r < (1.5 + live_power/200):
                        dx -= (particles_x[i] / r) * pull_strength if r > 0 else 0
                        dy -= (particles_y[i] / r) * pull_strength if r > 0 else 0
                    elif mode == "Vortex (OAM)" and r < 3:
                        dr = r - 1.0 
                        dx -= (particles_x[i] / r) * dr * pull_strength if r > 0 else 0
                        dy -= (particles_y[i] / r) * dr * pull_strength if r > 0 else 0
                        dx -= (particles_y[i] / r) * pull_strength * 0.8
                        dy += (particles_x[i] / r) * pull_strength * 0.8
                
                particles_x[i] = np.clip(particles_x[i] + dx, -4.8, 4.8)
                particles_y[i] = np.clip(particles_y[i] + dy, -4.8, 4.8)

                if particles_x[i] > 4.7:
                    particles_x[i] = -4.7
                    particles_y[i] = np.random.uniform(-4, 4)

            scatter.set_offsets(np.c_[particles_x, particles_y])
            return scatter, self.laser_imshow

        self.ani_micro = animation.FuncAnimation(self.fig_micro, update_micro, interval=40, blit=False)
        self.canvas_micro.draw()

    def run_monte_carlo(self):
        if self.ani_mc is not None:
            self.ani_mc.event_source.stop()
        
        dt, steps = 1e-4, 300 
        is_mixed = self.mix_var.get() == "Mixed (Rayleigh + Mie)"
        n_p = 2 
        
        time_data = np.linspace(0, steps*dt, steps)
        pos_data = np.zeros((n_p, steps))
        
        self.ax_mc.clear()
        self.ax_mc.set_facecolor('#1e1e1e')
        self.ax_hist.clear()
        self.ax_hist.set_facecolor('#1e1e1e')
        
        if is_mixed:
            colors = ['#facc15', '#00ffcc'] 
            labels = ['Mie Cell (Pushed)', 'Rayleigh (Stable in Trap)']
            self.ax_mc.set_title("Mie vs Rayleigh Trap Dynamics", color='white', fontsize=13)
        else:
            colors = ['#00ffcc', '#ff00ff']
            labels = ['X-Axis (Lateral)', 'Z-Axis (Axial)']
            self.ax_mc.set_title("3D Trapping Stability (X vs Z)", color='white', fontsize=13)

        lines = [self.ax_mc.plot(time_data, pos_data[i], color=colors[i], linewidth=2.0, alpha=0.9, label=labels[i])[0] for i in range(n_p)]
        self.ax_mc.legend(loc='upper right', facecolor='#000000', edgecolor='#555555', labelcolor='white', fontsize=10)
        
        self.thermal_text = self.ax_mc.text(0.02, 0.95, '', transform=self.ax_mc.transAxes, color='white', 
                                            fontsize=11, fontweight='bold', verticalalignment='top',
                                            bbox=dict(boxstyle='round,pad=0.5', facecolor='#000000', edgecolor='#ff4444', alpha=0.7))

        self.ax_mc.set_ylabel("Displacement (nm)", color='white')
        self.ax_mc.set_xlabel("Time (s)", color='white')
        self.ax_mc.grid(True, alpha=0.1)
        self.ax_mc.tick_params(colors='white')
        self.ax_mc.set_xlim(0, steps * dt)
        
        # Setup Hist Plot
        self.ax_hist.set_title("Boltzmann Distribution\n(Live MC vs Theory)", color='white', fontsize=11)
        self.hist_line, = self.ax_hist.plot([], [], color='#00ffcc', linewidth=2, drawstyle='steps-mid', label='MC Data')
        self.theory_line, = self.ax_hist.plot([], [], color='#ff00ff', linestyle='--', linewidth=2, label='Theory Fit')
        self.ax_hist.legend(loc='upper right', facecolor='#000000', edgecolor='none', labelcolor='white', fontsize=8)
        self.ax_hist.tick_params(colors='white')
        self.ax_hist.set_xlabel("Displacement x (nm)", color='white', fontsize=9)
        self.ax_hist.set_ylabel("Probability Density", color='white', fontsize=9)
        
        def format_disp(val):
            if abs(val) >= 10000: 
                return f"{val:+.2e} nm"
            return f"{val:+.1f} nm"

        def update(frame):
            live_power = self.power_slider.get() * 1e-3  
            base_radius = self.radius_slider.get() * 1e-9 
            live_fluid_v = self.fluid_slider.get() * 1e-6 
            mu_s = self.scatter_slider.get() * 1e3
            lens_na = self.na_slider.get() 
            wl, therm_fact = self.get_laser_properties()
            waist = wl / (2 * lens_na) 
            
            T_local = 300 + (live_power * 1000 * therm_fact) 
            eta = 8.9e-4 * np.exp(-0.02 * (T_local - 300)) 
            
            heat_ratio = min((T_local - 300) / 60, 1.0) 
            self.ax_mc.set_facecolor((0.12 + (0.3 * heat_ratio), 0.12 - (0.12 * heat_ratio), 0.12 - (0.12 * heat_ratio)))
            self.ax_hist.set_facecolor((0.12 + (0.3 * heat_ratio), 0.12 - (0.12 * heat_ratio), 0.12 - (0.12 * heat_ratio)))
            
            if T_local >= 373.15:
                self.thermal_text.set_text(f"💥 CAVITATION ERROR: Temp {T_local:.1f} K\nWater boiling! Micro-bubbles destroyed the trap.")
                self.thermal_text.set_color('#ff0000')
                live_power = 0
            elif T_local > 325:
                self.thermal_text.set_text(f"🔥 HIGH THERMAL AGITATION (Opticution Risk)\nTemp: {T_local:.1f} K | Visc: {eta*1e4:.2f} cP")
                self.thermal_text.set_color('#ff4d4d')
            else:
                self.thermal_text.set_text(f"🌡️ Lab State\nTemp: {T_local:.1f} K | Visc: {eta*1e4:.2f} cP")
                self.thermal_text.set_color('white')

            x_old = pos_data[:, -1]
            x_new = np.zeros(n_p)
            
            gamma_val, d_val = 0, 0
            k_x_pn_nm, k_z_pn_nm = 0, 0
            current_f_pn, snr_val = 0, 0
            ktrap_val_stable = 0
            
            for i in range(n_p):
                if is_mixed:
                    r_particle = base_radius * 10.0 if i == 0 else base_radius
                    gamma = 6 * np.pi * eta * r_particle 
                    D = (1.38e-23 * T_local) / gamma 
                    sim = OpticalTweezersSimulation(wl, live_power, waist, 1.33, 1.50, r_particle, "Gaussian", mu_s)
                    grad_coeff = sim.alpha / (2 * sim.c * sim.nm * sim.epsilon0)
                    attenuation = np.exp(-mu_s * 1e-6)
                    k_trap = (4 * grad_coeff * sim.I0 * attenuation) / (waist**2) if live_power > 0 else 0
                    
                    radiation_push = 0
                    if i == 0: 
                        k_trap *= (lens_na / 1.2)**4 * 0.1 
                        rad_press_scale = (1064e-9 / wl)**4
                        if lens_na < 1.0:
                            radiation_push = (live_power * 1e-4) * (1.1 - lens_na) * rad_press_scale
                else:
                    r_particle = base_radius
                    gamma = 6 * np.pi * eta * r_particle 
                    D = (1.38e-23 * T_local) / gamma 
                    sim = OpticalTweezersSimulation(wl, live_power, waist, 1.33, 1.50, r_particle, "Gaussian", mu_s)
                    grad_coeff = sim.alpha / (2 * sim.c * sim.nm * sim.epsilon0)
                    attenuation = np.exp(-mu_s * 1e-6)
                    k_trap = (4 * grad_coeff * sim.I0 * attenuation) / (waist**2) if live_power > 0 else 0
                    radiation_push = 0
                    if i == 1: k_trap *= 0.2 

                F_optical = -k_trap * x_old[i]
                F_drag = gamma * live_fluid_v if i == 0 else 0 
                
                if i == 1: 
                    gamma_val, d_val = gamma, D
                    ktrap_val_stable = k_trap
                    current_f_pn = abs(F_optical) * 1e12
                    
                    k_x_pn_nm = k_trap * 1e3 
                    k_z_pn_nm = (k_trap * 0.2) * 1e3
                    
                    trap_depth_J = k_trap * (waist**2) / 4 if live_power > 0 else 0
                    snr_val = trap_depth_J / (1.38e-23 * T_local)

                deterministic_dx = ((F_optical + F_drag) / gamma) * dt + radiation_push
                stochastic_dx = np.sqrt(2 * D * dt) * np.random.randn()
                
                new_val = x_old[i] + deterministic_dx + stochastic_dx
                x_new[i] = np.clip(new_val, -100e-6, 100e-6)

            if np.max(np.abs(x_new)) > 100e-9: 
                self.beep_geiger()
            
            pos_data[:, :-1] = pos_data[:, 1:]
            pos_data[:, -1] = x_new
            
            # --- Dynamic Y-Axis limits to solve the "Flat Line" issue ---
            max_disp = np.max(np.abs(pos_data * 1e9))
            y_bound = max(10.0, max_disp * 1.5)
            self.ax_mc.set_ylim(-y_bound, y_bound)
            
            # --- Update Histogram & Theory Overlay ---
            data_to_hist = pos_data[1, :] * 1e9
            hist, bin_edges = np.histogram(data_to_hist, bins=20, density=True)
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            self.hist_line.set_data(bin_centers, hist)
            
            if ktrap_val_stable > 1e-9:
                sigma = np.sqrt(1.38e-23 * T_local / ktrap_val_stable) * 1e9
                theory_x = np.linspace(-4*sigma, 4*sigma, 100)
                theory_y = 1/(sigma * np.sqrt(2 * np.pi)) * np.exp( - (theory_x)**2 / (2 * sigma**2) )
                self.theory_line.set_data(theory_x, theory_y)
                
                max_y = max(np.max(hist) if len(hist)>0 else 0.02, np.max(theory_y)) * 1.2
                self.ax_hist.set_ylim(0, max_y if max_y > 0 else 0.05)
                
                dynamic_x = max(10.0, 3.5 * sigma)
                self.ax_hist.set_xlim(-dynamic_x, dynamic_x)
            else:
                self.theory_line.set_data([], [])
            
            val1 = format_disp(x_new[0]*1e9)
            val2 = format_disp(x_new[1]*1e9)
            
            status = "STABLE \u2714" if snr_val > 10 else ("WEAK \u26A0" if snr_val > 1 else "UNSTABLE \u2716")
            metrics_string = (
                f"LANGEVIN DYNAMICS DASHBOARD:\n"
                f"▶ Displacement | {labels[0]}: {val1}  |  {labels[1]}: {val2}\n"
                f"▶ Optic Forces | Force: {current_f_pn:.2f} pN  |  Stiffness: \u03BA_x={k_x_pn_nm:.4f}, \u03BA_z={k_z_pn_nm:.4f} pN/nm\n"
                f"▶ Stability    | Potential/Thermal (SNR): {snr_val:.1f}  [{status}]\n"
                f"▶ Environment  | Drag (\u03b3): {gamma_val:.2e} N\u00B7s/m  |  Diffusion (D): {d_val:.2e} m\u00B2/s"
            )
            self.ctk_metrics_label.configure(text=metrics_string)

            for i in range(n_p):
                lines[i].set_ydata(pos_data[i] * 1e9)
            
            return tuple(lines) + (self.thermal_text, self.hist_line, self.theory_line)

        self.ani_mc = animation.FuncAnimation(self.fig_mc, update, interval=20, blit=False)
        self.canvas_mc.draw()

    def calculate_gs(self, *args):
        N = 128 
        target_amp = np.zeros((N, N))
        c, r, trap_size = N // 2, 20, 2
        pattern = self.pattern_var.get()
        
        if pattern == "1 Trap (Center)":
            target_amp[c-trap_size:c+trap_size, c-trap_size:c+trap_size] = 1
        elif pattern == "2 Traps (Line)":
            target_amp[c-trap_size:c+trap_size, c-r-trap_size:c-r+trap_size] = 1
            target_amp[c-trap_size:c+trap_size, c+r-trap_size:c+r+trap_size] = 1
        elif pattern == "4 Traps (Square)":
            target_amp[c-r-trap_size:c-r+trap_size, c-r-trap_size:c-r+trap_size] = 1
            target_amp[c-r-trap_size:c-r+trap_size, c+r-trap_size:c+r+trap_size] = 1
            target_amp[c+r-trap_size:c+r+trap_size, c-r-trap_size:c-r+trap_size] = 1
            target_amp[c+r-trap_size:c+r+trap_size, c+r-trap_size:c+r+trap_size] = 1
        elif pattern == "8 Traps (Ring)":
            for angle in np.linspace(0, 2*np.pi, 8, endpoint=False):
                x = int(c + r * np.cos(angle))
                y = int(c + r * np.sin(angle))
                target_amp[y-trap_size:y+trap_size, x-trap_size:x+trap_size] = 1

        depth = self.depth_slider.get() 
        x_slm = np.linspace(-1, 1, N)
        X_slm, Y_slm = np.meshgrid(x_slm, x_slm)
        rho = np.sqrt(X_slm**2 + Y_slm**2)
        rho[rho > 1] = 0 
        theta = np.arctan2(Y_slm, X_slm)
        
        self.aberration_coeff_val = (depth / 50.0) * 15.0 
        
        z_type = self.zernike_type_var.get()
        if "Spherical" in z_type:
            self.aberration_phase = self.aberration_coeff_val * np.sqrt(5) * (6*rho**4 - 6*rho**2 + 1)
        elif "Astigmatism" in z_type:
            self.aberration_phase = self.aberration_coeff_val * np.sqrt(6) * (rho**2) * np.cos(2*theta)
        else: 
            self.aberration_phase = self.aberration_coeff_val * np.sqrt(8) * (3*rho**3 - 2*rho) * np.cos(theta)

        phase = np.random.rand(N, N) * 2 * np.pi
        A_field = target_amp * np.exp(1j * phase)

        for _ in range(15): 
            slm_field = np.fft.ifft2(np.fft.ifftshift(A_field))
            slm_phase = np.angle(slm_field)
            focal_field = np.fft.fftshift(np.fft.fft2(1.0 * np.exp(1j * slm_phase)))
            A_field = target_amp * np.exp(1j * np.angle(focal_field)) 

        self.gs_cache_field = focal_field
        self.gs_cache_phase = slm_phase
        self.update_holo_plot_realtime()

    def update_holo_plot_realtime(self):
        if self.gs_cache_field is None: return
        
        live_power_ratio = max(self.power_slider.get() / 1000.0, 0.05)
        pattern = self.pattern_var.get()
        N = self.gs_cache_field.shape[0]
        
        is_corrected = self.zernike_var.get() == "On"
        depth_val = self.depth_slider.get()
        z_type = self.zernike_type_var.get()
        
        if is_corrected:
            final_slm_phase = self.gs_cache_phase - self.aberration_phase
            actual_focal_field = np.fft.fftshift(np.fft.fft2(1.0 * np.exp(1j * (final_slm_phase + self.aberration_phase))))
        else:
            final_slm_phase = self.gs_cache_phase
            actual_focal_field = np.fft.fftshift(np.fft.fft2(1.0 * np.exp(1j * (final_slm_phase + self.aberration_phase))))

        self.ax_target.clear()
        self.ax_phase.clear()
        self.ax_holo_3d.clear()
        
        simulated_intensity = (np.abs(actual_focal_field)**2) * live_power_ratio
        
        ideal_max = np.max(np.abs(self.gs_cache_field)**2)
        actual_max = np.max(np.abs(actual_focal_field)**2)
        
        if depth_val == 0:
            strehl = 100.0
        else:
            strehl = (actual_max / ideal_max) * 100 if ideal_max > 0 else 0
        
        self.ax_target.imshow(simulated_intensity, cmap='inferno', vmin=0, vmax=np.max(np.abs(self.gs_cache_field)**2))
        title_1 = f"Actual Focus (Corrected)\nStrehl Ratio: {strehl:.1f}%" if is_corrected else f"Actual Focus (Distorted)\nStrehl Ratio: {strehl:.1f}%"
        self.ax_target.set_title(f"1. {title_1}", color='white', fontsize=11)
        self.ax_target.axis('off')
        
        im_phase = self.ax_phase.imshow(final_slm_phase, cmap='twilight', vmin=-np.pi, vmax=np.pi)
        
        if self.cb_phase is None:
            self.cb_phase = self.fig_holo.colorbar(im_phase, ax=self.ax_phase, fraction=0.046, pad=0.04, ticks=[-np.pi, -np.pi/2, 0, np.pi/2, np.pi])
            self.cb_phase.ax.set_yticklabels([r'$-\pi$', r'$-\pi/2$', r'$0$', r'$\pi/2$', r'$\pi$'])
            self.cb_phase.ax.tick_params(labelsize=10, colors='white')
        else:
            self.cb_phase.update_normal(im_phase)
            
        if is_corrected and depth_val > 0:
            if "Spherical" in z_type:
                math_eq = r"$\Phi = -C \cdot \sqrt{5}(6\rho^4 - 6\rho^2 + 1)$"
            elif "Astigmatism" in z_type:
                math_eq = r"$\Phi = -C \cdot \sqrt{6}\rho^2 \cos(2\theta)$"
            else:
                math_eq = r"$\Phi = -C \cdot \sqrt{8}(3\rho^3 - 2\rho)\cos(\theta)$"
                
            mode_name = z_type.split(" ")[0]
            math_title = f"2. SLM Mask ({mode_name} Correction)\n{math_eq}\n$C = {self.aberration_coeff_val:.1f}$ rad"
            self.ax_phase.set_title(math_title, color='#10b981', fontsize=11)
        elif depth_val == 0:
            self.ax_phase.set_title("2. SLM Phase Mask\n(No Distortion Active)", color='white', fontsize=11)
        else:
            self.ax_phase.set_title("2. SLM Phase Mask\n(Uncorrected)", color='white', fontsize=11)
            
        self.ax_phase.axis('off')

        u_holo = -simulated_intensity / np.max(np.abs(self.gs_cache_field)**2) 
        x_mesh = np.linspace(-5, 5, N)
        X_m, Y_m = np.meshgrid(x_mesh, x_mesh)
        self.ax_holo_3d.set_box_aspect(aspect=(1, 1, 0.4))
        self.ax_holo_3d.plot_surface(X_m, Y_m, u_holo, cmap=cm.plasma, edgecolor='none', alpha=0.9)
        self.ax_holo_3d.set_title("3. 3D Output\n(Live Wavefront Distortion)", color='white', fontsize=11)
        self.ax_holo_3d.set_xlabel(r"$x$ ($\mu$m)", color='white', fontsize=8)
        self.ax_holo_3d.set_ylabel(r"$y$ ($\mu$m)", color='white', fontsize=8)
        self.ax_holo_3d.set_zlabel(r"Normalized Intensity", color='white', fontsize=8)
        self.ax_holo_3d.set_zlim(-1.2, 0.2)
        
        for axis in [self.ax_holo_3d.xaxis, self.ax_holo_3d.yaxis, self.ax_holo_3d.zaxis]:
            axis.set_pane_color((0.12, 0.12, 0.12, 1.0))
        self.ax_holo_3d.tick_params(axis='both', colors='white', labelsize=8)
        
        self.canvas_holo.draw()

    def on_slider_change(self):
        self.lbl_power.configure(text=f"Laser Power: {int(self.power_slider.get())} mW")
        self.lbl_radius.configure(text=f"Base Radius (Rayleigh): {int(self.radius_slider.get())} nm")
        self.lbl_fluid.configure(text=f"Fluid Drag: {int(self.fluid_slider.get())} μm/s")
        self.lbl_scattering.configure(text=f"Tissue Turbidity (\u03BC_s): {int(self.scatter_slider.get())} mm^-1")
        self.lbl_depth.configure(text=f"Aberration Intensity: {int(self.depth_slider.get())}")
        
        na_val = self.na_slider.get()
        if na_val > 1.33:
            self.lbl_na.configure(text=f"Objective NA: {na_val:.2f} \u26A0 (Requires Immersion Lens)", text_color="#ffaa00")
        else:
            self.lbl_na.configure(text=f"Objective NA: {na_val:.2f}", text_color="white")
        
        active_tab = self.tabview.get() if hasattr(self, 'tabview') else ""
        if active_tab == "Topology (Tissue Interaction)":
            self.update_topo_plot()
        elif active_tab == "Holographic Array (SLM)":
            self.calculate_gs(self.pattern_var.get())

if __name__ == "__main__":
    app = AdvancedTweezersApp()
    app.mainloop()