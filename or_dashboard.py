import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests
import re
import json
import os
from datetime import datetime, timedelta, timezone

# ==========================================
# --- CONFIGURATION & CONSTANTS ---
# ==========================================
# The file where the user's API key will be securely saved locally
CONFIG_FILE = "or_config.json"
# How often the dashboard automatically fetches new data (300s = 5 minutes)
REFRESH_INTERVAL_SECONDS = 300  

# Custom color mapping to match OpenRouter's web UI.
# Add new models and their preferred hex colors here.
CUSTOM_MODEL_COLORS = {
    "GLM 5.2": "#d4a373",           
    "Gemini 3.7 Flash": "#f4cc5d",  
    "Claude Sonnet 5": "#457b9d",   
    "GPT-5.6 Luna Pro": "#558b2f",  
    "DeepSeek v4 Pro": "#8338ec",   
    "Kimi K3": "#e63946",           
    "Claude 4.6 Sonnet": "#d88c9a"  
}

# Fallback colors used if a model is not found in CUSTOM_MODEL_COLORS
DEFAULT_PALETTE = [
    "#2a9d8f", "#e76f51", "#264653", "#e9c46a", "#f4a261", 
    "#118ab2", "#06d6a0", "#ef476f", "#073b4c"
]
# ==========================================

class OpenRouterDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # --- Window Configuration ---
        self.title("OR Usage & Balance")
        self.geometry("280x510")
        self.attributes("-topmost", True) # Keeps the window floating above others
        self.configure(bg="#ffffff")
        
        # --- State Variables ---
        self.hours = list(range(-12, 1)) # X-axis data representing hours past (-12 to 0)
        self.models_data = {}            # Stores hourly cost arrays per model
        self.model_colors = {}           # Stores assigned colors per model
        self.countdown_job = None        # Tracks the Tkinter 'after' job for auto-refresh
        self.time_until_refresh = REFRESH_INTERVAL_SECONDS
        
        # --- Initialization ---
        self.setup_ui()
        
        # Check if the user has saved an API key. If not, open settings immediately.
        if not self.get_api_key():
            self.status_label.config(text="Missing API Key", fg="#e63946")
            self.open_settings()
        else:
            self.refresh_data() # Initial data fetch

    # ==========================================
    # --- FILE I/O (SETTINGS MANAGER) ---
    # ==========================================
    def get_api_key(self):
        """Attempts to load the API key from the local JSON config file."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    return data.get("api_key", "").strip()
            except Exception:
                return ""
        return ""

    def save_api_key(self, key):
        """Saves the API key to the local JSON config file."""
        with open(CONFIG_FILE, "w") as f:
            json.dump({"api_key": key}, f)

    # ==========================================
    # --- UTILITIES ---
    # ==========================================
    def format_model_name(self, slug):
        """
        Parses raw OpenRouter model slugs (e.g., 'anthropic/claude-5-sonnet') 
        into cleaner display names for the UI.
        """
        slug_lower = slug.lower()
        if "glm-5.2" in slug_lower: return "GLM 5.2"
        elif "gemini-3.7-flash" in slug_lower: return "Gemini 3.7 Flash"
        elif "claude-sonnet-5" in slug_lower or "claude-5-sonnet" in slug_lower: return "Claude Sonnet 5"
        elif "claude-4.6-sonnet" in slug_lower: return "Claude 4.6 Sonnet"
        elif "gpt-5.6-luna" in slug_lower: return "GPT-5.6 Luna Pro"
        elif "deepseek-v4-pro" in slug_lower: return "DeepSeek v4 Pro"
        elif "kimi-k3" in slug_lower: return "Kimi K3"
        
        # Fallback: Strip vendor name and trailing date tags
        name = slug.split('/')[-1]
        name = re.sub(r'-\d{8}$', '', name)
        return name.replace('-', ' ').title()

    # ==========================================
    # --- UI SETUP ---
    # ==========================================
    def setup_ui(self):
        """Builds all the static frames, labels, and the Matplotlib canvas."""
        
        # 1. Header Area (Live Spend & Balance)
        self.header_frame = tk.Frame(self, bg="#ffffff")
        self.header_frame.pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(self.header_frame, text="Live Spend", bg="#ffffff", font=("Segoe UI", 10, "bold"), fg="#333333").pack(side="left")
        
        self.balance_label = tk.Label(self.header_frame, text="Balance: $--.--", bg="#ffffff", font=("Segoe UI", 9, "bold"), fg="#2a9d8f")
        self.balance_label.pack(side="right")
        
        # 2. Graph Area (Matplotlib)
        self.fig = Figure(figsize=(2.6, 1.8), dpi=100)
        self.fig.patch.set_facecolor('#ffffff')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#ffffff')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="x", pady=(5, 0), padx=8)
        
        # 3. Table Area (To be populated dynamically later)
        self.table_frame = tk.Frame(self, bg="#ffffff")
        self.table_frame.pack(fill="both", expand=True, padx=16, pady=5)
        
        # 4. Bottom Controls Area (Buttons & Status)
        self.controls_frame = tk.Frame(self, bg="#ffffff")
        self.controls_frame.pack(fill="x", side="bottom", pady=10, padx=16)
        
        self.refresh_btn = tk.Button(
            self.controls_frame, text="Refresh Now", command=self.manual_refresh,
            bg="#f4f4f5", fg="#333333", font=("Segoe UI", 8), relief="groove", cursor="hand2"
        )
        self.refresh_btn.pack(side="left")
        
        self.settings_btn = tk.Button(
            self.controls_frame, text="⚙", command=self.open_settings,
            bg="#f4f4f5", fg="#333333", font=("Segoe UI", 8), relief="groove", cursor="hand2"
        )
        self.settings_btn.pack(side="left", padx=(5, 0))
        
        self.status_label = tk.Label(
            self.controls_frame, text="Starting...", bg="#ffffff", fg="#888888", font=("Segoe UI", 8)
        )
        self.status_label.pack(side="right")

    def open_settings(self):
        """Opens a modal popup to enter and save the OpenRouter API Key."""
        settings_win = tk.Toplevel(self)
        settings_win.title("Settings")
        settings_win.geometry("300x120")
        settings_win.attributes("-topmost", True)
        settings_win.configure(bg="#f4f4f5")
        settings_win.grab_set() # Forces all user interaction to this window until closed
        
        tk.Label(settings_win, text="Management API Key:", bg="#f4f4f5", font=("Segoe UI", 9)).pack(pady=(15, 5))
        
        key_var = tk.StringVar(value=self.get_api_key())
        key_entry = tk.Entry(settings_win, textvariable=key_var, width=35, show="*")
        key_entry.pack(pady=5)
        
        def save_and_close():
            new_key = key_var.get().strip()
            if new_key:
                self.save_api_key(new_key)
                settings_win.destroy()
                self.manual_refresh() # Force a data update with the new key
            else:
                messagebox.showwarning("Warning", "API Key cannot be empty.", parent=settings_win)

        tk.Button(settings_win, text="Save & Refresh", command=save_and_close, bg="#3b82f6", fg="white", font=("Segoe UI", 8, "bold"), relief="flat").pack(pady=5)

    # ==========================================
    # --- API DATA FETCHING ---
    # ==========================================
    def fetch_balance(self, api_key):
        """Fetches the total credits and usage to calculate remaining balance."""
        url = "https://openrouter.ai/api/v1/credits"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        try:
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json().get('data', {})
            
            total_credits = data.get('total_credits')
            total_usage = data.get('total_usage')
            
            # Detects if user is on Pay-As-You-Go (PAYG) instead of prepaid credits
            if total_credits is None or total_usage is None:
                return "PAYG"
                
            balance = float(total_credits) - float(total_usage)
            return balance
        except Exception as e:
            print(f"Balance fetch error: {e}")
            return None

    def fetch_live_data(self):
        """Fetches hourly cost analytics from OpenRouter for the past 12 hours."""
        api_key = self.get_api_key()
        if not api_key:
            return {}, None

        # Fetch balance concurrently
        balance = self.fetch_balance(api_key)

        url = "https://openrouter.ai/api/v1/analytics/query"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Calculate time range bounds (UTC)
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=12)
        
        payload = {
            "metrics": ["total_usage"], 
            "dimensions": ["model"], 
            "granularity": "hour", 
            "time_range": {
                "start": start_time.strftime("%Y-%m-%dT%H:00:00Z"),
                "end": now.strftime("%Y-%m-%dT%H:59:59Z")
            }
        }
        
        parsed_data = {}
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=8)
            # Handle invalid API key specifically
            if response.status_code == 401:
                self.status_label.config(text="Invalid API Key", fg="#e63946")
                return {}, balance
            
            response.raise_for_status()
            raw = response.json()
            
            # OpenRouter wraps the payload in an extra 'data' dictionary
            records = raw.get('data', {}).get('data', [])
            current_hour_utc = now.replace(minute=0, second=0, microsecond=0)
            
            # Sort the records into hourly buckets mapping to -12 to 0 on the graph
            for entry in records:
                raw_model = entry.get('model', 'Unknown')
                display_model = self.format_model_name(raw_model)
                
                # Initialize an array of 13 zeros (for hours -12 through 0)
                if display_model not in parsed_data:
                    parsed_data[display_model] = [0.0] * 13
                
                cost = float(entry.get('total_usage', 0.0))
                date_str = entry.get('date__hour')
                
                if date_str:
                    try:
                        # Find the time difference between the log and right now
                        entry_dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                        hour_diff = int((entry_dt - current_hour_utc).total_seconds() // 3600)
                        
                        # Apply to the correct array index (index 12 is hour 0)
                        index = 12 + hour_diff
                        if 0 <= index <= 12:
                            parsed_data[display_model][index] += cost
                    except Exception:
                        parsed_data[display_model][-1] += cost
                else:
                    parsed_data[display_model][-1] += cost
                    
            return parsed_data, balance
        except Exception as e:
            print(f"Fetch error: {e}")
            return {}, balance

    # ==========================================
    # --- REFRESH & TICK LOGIC ---
    # ==========================================
    def manual_refresh(self):
        """Triggered by the Refresh button. Resets the timer and updates."""
        if not self.get_api_key():
            self.open_settings()
            return
        self.time_until_refresh = REFRESH_INTERVAL_SECONDS
        self.refresh_data()

    def refresh_data(self):
        """The main execution loop for fetching and drawing new data."""
        # Cancel any pending loop so we don't end up with multiple timers firing
        if self.countdown_job is not None:
            self.after_cancel(self.countdown_job)
            
        self.status_label.config(text="Fetching...", fg="#888888")
        self.update_idletasks() # Force UI update before the blocking network call
        
        data, balance = self.fetch_live_data()
        
        # 1. Update Balance UI
        if balance == "PAYG":
            self.balance_label.config(text="Balance: PAYG", fg="#e63946")
        elif isinstance(balance, float):
            self.balance_label.config(text=f"Balance: ${balance:.2f}", fg="#2a9d8f")
        else:
            self.balance_label.config(text="Balance: Error", fg="#888888")
        
        # 2. Process Graph Data and Assign Colors
        if data:
            self.models_data = data
            self.model_colors = {}
            fallback_index = 0
            
            # Map known models to custom colors, assign default colors to unknowns
            for model in self.models_data.keys():
                if model in CUSTOM_MODEL_COLORS:
                    self.model_colors[model] = CUSTOM_MODEL_COLORS[model]
                else:
                    self.model_colors[model] = DEFAULT_PALETTE[fallback_index % len(DEFAULT_PALETTE)]
                    fallback_index += 1
        
        # 3. Redraw the GUI components
        self.draw_graph()
        self.update_table()
        
        # 4. Restart the countdown
        self.time_until_refresh = REFRESH_INTERVAL_SECONDS
        self.tick_countdown()

    def tick_countdown(self):
        """Updates the countdown text every second."""
        if self.time_until_refresh <= 0:
            self.refresh_data()
            return
            
        mins, secs = divmod(self.time_until_refresh, 60)
        self.status_label.config(text=f"Update in {mins:02d}:{secs:02d}", fg="#888888")
        
        self.time_until_refresh -= 1
        # Schedule this function to run again in 1000 milliseconds
        self.countdown_job = self.after(1000, self.tick_countdown)

    # ==========================================
    # --- DRAWING / RENDERING ---
    # ==========================================
    def update_table(self):
        """Clears and rebuilds the bottom list of models and their costs."""
        # Clear existing rows
        for widget in self.table_frame.winfo_children():
            widget.destroy()
            
        # Calculate total cost per model and filter out $0.00 entries
        model_totals = [
            (model, sum(vals)) 
            for model, vals in self.models_data.items() 
            if sum(vals) > 0.0001
        ]
        # Sort highest spend to lowest
        model_totals.sort(key=lambda x: x[1], reverse=True)
        grand_total = sum(t[1] for t in model_totals)
        
        # Build Table Rows
        for i, (model, total) in enumerate(model_totals):
            color = self.model_colors.get(model, "#888888")
            
            # Vertical color strip
            tk.Label(self.table_frame, bg=color, width=1, font=("Arial", 6)).grid(row=i, column=0, pady=3, sticky="nsw")
            # Model Name
            tk.Label(self.table_frame, text=model, bg="#ffffff", font=("Segoe UI", 9)).grid(row=i, column=1, sticky="w", padx=(6, 0))
            # Cost (Dynamically formats 3 decimal places for micro-transactions)
            cost_str = f"${total:.3f}" if total < 1.0 else f"${total:.2f}"
            tk.Label(self.table_frame, text=cost_str, bg="#ffffff", font=("Segoe UI", 9)).grid(row=i, column=2, sticky="e")
            
            # Ensure the middle column stretches so numbers align to the right
            self.table_frame.grid_columnconfigure(1, weight=1)

        row_offset = len(model_totals)
        
        # Bottom Divider and Grand Total
        ttk.Separator(self.table_frame, orient="horizontal").grid(
            row=row_offset, column=0, columnspan=3, sticky="ew", pady=8
        )
        tk.Label(self.table_frame, text="Total", bg="#ffffff", font=("Segoe UI", 9, "bold")).grid(
            row=row_offset + 1, column=1, sticky="w", padx=(6, 0)
        )
        tk.Label(self.table_frame, text=f"${grand_total:.2f}", bg="#ffffff", font=("Segoe UI", 10, "bold")).grid(
            row=row_offset + 1, column=2, sticky="e"
        )

    def draw_graph(self):
        """Clears and rebuilds the Matplotlib stacked bar chart."""
        self.ax.clear()
        
        # Keeps track of the cumulative height of each bar segment for stacking
        bottoms = [0.0] * len(self.hours)
        
        for model, values in self.models_data.items():
            color = self.model_colors.get(model, "#888888")
            self.ax.bar(
                self.hours, values, bottom=bottoms, 
                color=color, width=0.35, edgecolor='none'
            )
            # Add current model's values to bottoms to push the next model up
            bottoms = [b + v for b, v in zip(bottoms, values)]
            
        # Clean up X-axis to only show relevant hour milestones
        self.ax.set_xticks([-12, -9, -6, -3, 0])
        self.ax.set_xlim(-12.5, 0.5)
        self.ax.tick_params(colors='#777777', labelsize=8, length=0)
        
        # Format Y-axis as currency
        self.ax.yaxis.set_major_formatter('${x:1.1f}')
        self.ax.tick_params(axis='y', colors='#777777', labelsize=8, length=0)
        
        # Draw background dashed gridlines
        self.ax.grid(True, axis='both', linestyle='--', alpha=0.35, color='#dddddd')
        self.ax.set_axisbelow(True) # Force gridlines behind the bars
        
        # Remove the black box outline from the chart
        for spine in self.ax.spines.values():
            spine.set_visible(False)
            
        # Apply layout and render to canvas
        self.fig.tight_layout(pad=0.8)
        self.canvas.draw()

# --- ENTRY POINT ---
if __name__ == "__main__":
    app = OpenRouterDashboard()
    app.mainloop()