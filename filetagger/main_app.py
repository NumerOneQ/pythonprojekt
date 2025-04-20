# filetagger/main_app.py
import tkinter as tk
import os
import threading
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk

from filetagger.ui.animated_button import AnimatedImageButton
from filetagger.core import config, file_operations, image_processing, api_integration

class FileRenamerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Filnamnsändrare med Taggning")
        self.style = ttk.Style("darkly")

        self.root.minsize(800, 600)

        self.folder = ""
        self.allowed_extensions = list(config.DEFAULT_ALLOWED_EXTENSIONS)
        self.shortcut_keys = list(config.DEFAULT_SHORTCUT_KEYS)
        self.tags = [""] * len(self.shortcut_keys)
        self.is_assigning_shortcut = False
        self.shortcut_assign_index = None
        self.current_photo = None
        self.text_entries = []
        self.saved_horizontal_sash_pos = 300
        self.saved_vertical_sash_pos = 400
        self.saved_metadata_sash_pos = 300
        self.sash_positions_set = False
        self.archived_files = []
        self.external_viewer_path = ""
        self.google_maps_api_key = ""

        self.imgbb_api_key = ""
        self.serpapi_api_key = ""

        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        self.progressbar = None
        self.progress_label = None
        self.last_archived_label = None
        self.metadata_labels = {}
        self.metadata_entries = {}
        self.current_file_path = None

        self.create_top_toolbar()
        self.create_path_display()
        self.create_main_content()

        self.load_settings()

        if not self.imgbb_api_key:
            messagebox.showerror("Fel", "ImgBB API-nyckel saknas i settings.json. Ange en giltig nyckel.")
            self.root.destroy()
            return
        if not self.serpapi_api_key:
            messagebox.showerror("Fel", "SerpApi API-nyckel saknas i settings.json. Ange en giltig nyckel.")
            self.root.destroy()
            return
        if not self.google_maps_api_key:
            messagebox.showerror("Fel", "Google Maps API-nyckel saknas i settings.json. Ange en giltig nyckel.")
            self.root.destroy()
            return
        if not self.external_viewer_path:
            messagebox.showwarning("Varning", "Sökväg till extern bildvisare saknas i settings.json. Ange sökvägen för att använda dubbelklick-funktionen.")

        if self.folder and os.path.isdir(self.folder):
            self.list_files()
        else:
            self.file_count_label.config(text="Filer: 0")
            self.file_listbox.insert(tk.END, "Välj en katalog för att visa filer.")

        self.setup_keyboard_shortcuts()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Configure>", self.on_window_resize)
        self.paned_window.bind("<Configure>", self.set_sash_positions_once)

    def show_progress(self):
        self.progressbar.pack(side=tk.LEFT, padx=5)
        self.progress_label.pack(side=tk.LEFT, padx=5)
        self.progressbar.start()
        self.root.update_idletasks()

    def hide_progress(self):
        self.progressbar.stop()
        self.progressbar.pack_forget()
        self.progress_label.pack_forget()
        self.root.update_idletasks()

    def upload_image_to_imgbb(self, file_path):
        return api_integration.upload_image_to_imgbb(file_path, self.imgbb_api_key)

    def analyze_image_with_google_lens(self):
        api_integration.analyze_image_with_google_lens(self)

    def _analyze_image_thread(self, selected_indices):
        api_integration._analyze_image_thread(self, selected_indices)

    def _update_tags(self, tags):
        api_integration._update_tags(self, tags)

    def archive_file(self):
        file_operations.archive_file(self)

    def undo_archive(self):
        file_operations.undo_archive(self)

    def open_in_external_viewer(self, event):
        file_operations.open_in_external_viewer(self, event)

    def create_top_toolbar(self):
        toolbar = ttk.Frame(self.main_frame, bootstyle="dark")
        toolbar.pack(fill=tk.X, pady=(0, 10))

        folder_image = self.load_icon("folder", size=(24, 24))
        self.select_folder_btn = AnimatedImageButton(
            toolbar,
            text="Välj mapp",
            base_pil_image=folder_image,
            command=self.select_folder
        )
        self.select_folder_btn.pack(side=tk.LEFT, padx=5)

        self.path_label = ttk.Label(toolbar, text="Sökväg: Ingen katalog vald", bootstyle="light")
        self.path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        analyze_image = self.load_icon("analyze", size=(24, 24))
        self.analyze_btn = AnimatedImageButton(
            toolbar,
            text="Analysera",
            base_pil_image=analyze_image,
            command=self.analyze_image_with_google_lens
        )
        self.analyze_btn.pack(side=tk.LEFT, padx=5)

        self.progressbar = ttk.Progressbar(toolbar, mode="indeterminate", bootstyle="info")
        self.progress_label = ttk.Label(toolbar, text="Analyserar bild...", bootstyle="info")
        self.progressbar.pack_forget()
        self.progress_label.pack_forget()

        self.file_count_label = ttk.Label(toolbar, text="Filer: 0", bootstyle="light")
        self.file_count_label.pack(side=tk.RIGHT, padx=5)

    def create_path_display(self):
        path_frame = ttk.Frame(self.main_frame, bootstyle="dark")
        path_frame.pack(fill=tk.X, pady=(0, 10))

        extension_frame = ttk.LabelFrame(path_frame, text="Filändelser", bootstyle="info")
        extension_frame.pack(side=tk.RIGHT, padx=5)
        self.extension_entry = ttk.Entry(extension_frame, width=20)
        self.extension_entry.pack(side=tk.LEFT, padx=5, pady=5)
        self.extension_entry.bind("<Return>", lambda event: self.update_extensions())

        refresh_image = self.load_icon("refresh", size=(24, 24))
        self.extension_update_btn = AnimatedImageButton(
            extension_frame,
            text="Uppdatera",
            base_pil_image=refresh_image,
            command=self.update_extensions
        )
        self.extension_update_btn.pack(side=tk.LEFT, padx=5, pady=5)

        name_change_frame = ttk.LabelFrame(path_frame, text="Manuell namnändring", bootstyle="info")
        name_change_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.single_entry = ttk.Entry(name_change_frame)
        self.single_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        self.single_entry.bind("<Return>", lambda event: self.rename_single_file())

        rename_image = self.load_icon("rename", size=(24, 24))
        self.rename_single_btn = AnimatedImageButton(
            name_change_frame,
            text="Byt namn",
            base_pil_image=rename_image,
            command=self.rename_single_file
        )
        self.rename_single_btn.pack(side=tk.LEFT, padx=5, pady=5)

    def load_icon(self, base_name, size=(24, 24)):
        """Laddar en basbild och returnerar den som en PIL Image."""
        try:
            # Använd resource_path för att hitta bilderna
            img_path = config.resource_path(f"{base_name}.png")
            img = Image.open(img_path)
            img = img.resize(size, Image.Resampling.LANCZOS)
            return img
        except FileNotFoundError as e:
            print(f"Varning: Bildfil för {base_name} hittades inte: {e}. Använder platshållare.")
            placeholder = Image.new("RGBA", size, (255, 255, 255, 0))
            return placeholder
        except Exception as e:
            print(f"Fel vid laddning av bild för {base_name}: {e}")
            placeholder = Image.new("RGBA", size, (255, 255, 255, 0))
            return placeholder

    def set_sash_positions_once(self, event):
        if not self.sash_positions_set:
            self.paned_window.sashpos(0, self.saved_horizontal_sash_pos)
            self.right_paned_window.sashpos(0, self.saved_vertical_sash_pos)
            self.bottom_paned_window.sashpos(0, self.saved_metadata_sash_pos)
            self.sash_positions_set = True
            self.restrict_pane_sizes(None)

    def on_window_resize(self, event):
        self.restrict_pane_sizes(None)

    def restrict_pane_sizes(self, event):
        sash_pos = self.paned_window.sashpos(0)
        window_width = self.paned_window.winfo_width()
        min_left = 200
        min_right = 300
        if sash_pos < min_left:
            self.paned_window.sashpos(0, min_left)
        elif sash_pos > window_width - min_right and window_width > min_right:
            self.paned_window.sashpos(0, window_width - min_right)

        sash_pos_vertical = self.right_paned_window.sashpos(0)
        window_height = self.right_paned_window.winfo_height()
        min_top = 200
        min_bottom = 200
        if sash_pos_vertical < min_top:
            self.right_paned_window.sashpos(0, min_top)
        elif sash_pos_vertical > window_height - min_bottom and window_height > min_bottom:
            self.right_paned_window.sashpos(0, window_height - min_bottom)

        sash_pos_metadata = self.bottom_paned_window.sashpos(0)
        bottom_width = self.bottom_paned_window.winfo_width()
        min_metadata = 200
        min_tags = 200
        if sash_pos_metadata < min_metadata:
            self.bottom_paned_window.sashpos(0, min_metadata)
        elif sash_pos_metadata > bottom_width - min_tags and bottom_width > min_tags:
            self.bottom_paned_window.sashpos(0, bottom_width - min_tags)

    def create_main_content(self):
        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        self.paned_window = ttk.PanedWindow(content_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(left_frame)

        list_frame = ttk.LabelFrame(left_frame, text="Filer", bootstyle="info")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        self.file_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            bg="#2c2c2c",
            fg="white",
            selectbackground="#4a4a4a",
            highlightthickness=0,
            borderwidth=0
        )
        self.file_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.file_listbox.bind("<<ListboxSelect>>", self.update_preview)
        self.file_listbox.bind("<Double-Button-1>", self.open_in_external_viewer)

        archived_frame = ttk.LabelFrame(left_frame, text="Arkiverat", bootstyle="info")
        archived_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.last_archived_label = ttk.Label(archived_frame, text="Senast arkiverad: Ingen", bootstyle="light")
        self.last_archived_label.pack(fill=tk.X, padx=5, pady=5)

        self.right_paned_window = ttk.PanedWindow(self.paned_window, orient=tk.VERTICAL)
        self.paned_window.add(self.right_paned_window)

        preview_container = ttk.LabelFrame(self.right_paned_window, text="Förhandsgranskning", bootstyle="info")
        self.preview_canvas = tk.Canvas(preview_container, bg="#2c2c2c", highlightthickness=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.preview_canvas.bind("<Configure>", self.update_preview)
        self.right_paned_window.add(preview_container)

        self.bottom_paned_window = ttk.PanedWindow(self.right_paned_window, orient=tk.HORIZONTAL)
        self.right_paned_window.add(self.bottom_paned_window)

        metadata_frame = ttk.LabelFrame(self.bottom_paned_window, text="Metadata", bootstyle="info")
        self.bottom_paned_window.add(metadata_frame)

        metadata_fields = [
            "Fotodatum", "Senast ändrad", "GPS Latitud", "GPS Longitud",
            "Kameratillverkare", "Kameramodell", "Bildstorlek"
        ]
        for field in metadata_fields:
            row_frame = ttk.Frame(metadata_frame)
            row_frame.pack(fill=tk.X, pady=2, padx=5)
            label = ttk.Label(row_frame, text=f"{field}:", width=15, bootstyle="light")
            label.pack(side=tk.LEFT)

            if field in ["Fotodatum"]:
                entry = ttk.Entry(row_frame)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self.metadata_entries[field] = entry
            else:
                value_label = ttk.Label(row_frame, text="N/A", bootstyle="light", wraplength=200)
                value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self.metadata_labels[field] = value_label
                if field in ["GPS Latitud", "GPS Longitud"]:
                    value_label.bind("<Double-Button-1>", lambda event, f=field: image_processing.open_google_maps(self, f))

        save_metadata_image = self.load_icon("save_metadata", size=(24, 24))
        save_metadata_btn = AnimatedImageButton(
            metadata_frame,
            text="Spara metadata",
            base_pil_image=save_metadata_image,
            command=self.save_metadata
        )
        save_metadata_btn.pack(pady=2)

        gps_frame = ttk.Frame(metadata_frame)
        gps_frame.pack(fill=tk.X, pady=2, padx=5)
        ttk.Label(gps_frame, text="Plats för GPS:", bootstyle="light").pack(side=tk.LEFT)
        self.gps_location_entry = ttk.Entry(gps_frame)
        self.gps_location_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        fetch_gps_image = self.load_icon("fetch_gps", size=(24, 24))
        fetch_gps_btn = AnimatedImageButton(
            gps_frame,
            text="Hämta GPS",
            base_pil_image=fetch_gps_image,
            command=self.fetch_and_save_gps
        )
        fetch_gps_btn.pack(side=tk.LEFT, padx=2)

        fetch_place_image = self.load_icon("fetch_place", size=(24, 24))
        fetch_place_btn = AnimatedImageButton(
            gps_frame,
            text="Hämta plats",
            base_pil_image=fetch_place_image,
            command=self.fetch_place_from_gps
        )
        fetch_place_btn.pack(side=tk.LEFT, padx=2)

        text_buttons_frame = ttk.LabelFrame(self.bottom_paned_window, text="Taggar och kortkommandon", bootstyle="info")
        self.bottom_paned_window.add(text_buttons_frame)

        self.rename_buttons = []
        self.shortcut_buttons = []
        for i in range(10):
            row_frame = ttk.Frame(text_buttons_frame)
            row_frame.pack(fill=tk.X, pady=2, padx=5)

            shortcut_image = self.load_icon("shortcut", size=(24, 24))
            shortcut_btn = AnimatedImageButton(
                row_frame,
                text="N/A",
                base_pil_image=shortcut_image,
                command=lambda index=i: self.start_shortcut_assignment(index)
            )
            shortcut_btn.pack(side=tk.LEFT, padx=5)
            self.shortcut_buttons.append(shortcut_btn)

            entry = ttk.Entry(row_frame)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            entry.bind("<Return>", lambda event, index=i: self.handle_shortcut_and_save_tag(index, event))
            entry.bind("<KeyRelease>", lambda event, index=i: self.update_tag(index))
            self.text_entries.append(entry)

            tag_image = self.load_icon("tag", size=(24, 24))
            btn = AnimatedImageButton(
                row_frame,
                text=f"Tagg {i+1}",
                base_pil_image=tag_image,
                command=lambda i=i: self.handle_shortcut(i, None)
            )
            btn.pack(side=tk.LEFT, padx=5)
            self.rename_buttons.append(btn)

        for i in range(10, 12):
            row_frame = ttk.Frame(text_buttons_frame)
            row_frame.pack(fill=tk.X, pady=2, padx=5)

            shortcut_image = self.load_icon("shortcut", size=(24, 24))
            shortcut_btn = AnimatedImageButton(
                row_frame,
                text="N/A",
                base_pil_image=shortcut_image,
                command=lambda index=i: self.start_shortcut_assignment(index)
            )
            shortcut_btn.pack(side=tk.LEFT, padx=5)
            self.shortcut_buttons.append(shortcut_btn)

            button_name = "archive" if i == 10 else "undo"
            button_text = "Arkivera" if i == 10 else "Ångra"
            button_image = self.load_icon(button_name, size=(24, 24))
            btn = AnimatedImageButton(
                row_frame,
                text=button_text,
                base_pil_image=button_image,
                command=self.archive_file if i == 10 else self.undo_archive
            )
            btn.pack(side=tk.LEFT, padx=5)
            self.rename_buttons.append(btn)

        self.paned_window.bind("<B1-Motion>", self.restrict_pane_sizes)
        self.right_paned_window.bind("<B1-Motion>", self.restrict_pane_sizes)
        self.bottom_paned_window.bind("<B1-Motion>", self.restrict_pane_sizes)

    def update_metadata(self, file_path):
        image_processing.update_metadata(self, file_path)

    def get_gps_coord(self, gps_data, coord_tag, ref_tag):
        return image_processing.get_gps_coord(gps_data, coord_tag, ref_tag)

    def save_metadata(self):
        image_processing.save_metadata(self)

    def fetch_and_save_gps(self):
        image_processing.fetch_and_save_gps(self)

    def fetch_place_from_gps(self):
        image_processing.fetch_place_from_gps(self)

    def open_google_maps(self, field):
        image_processing.open_google_maps(self, field)

    def save_gps_to_image(self, lat, lon):
        image_processing.save_gps_to_image(self, lat, lon)

    def update_tag(self, index):
        if index < len(self.text_entries):
            self.tags[index] = self.text_entries[index].get()
            self.save_settings()

    def handle_shortcut_and_save_tag(self, index, event):
        self.handle_shortcut(index, event)
        self.update_tag(index)

    def select_folder(self):
        file_operations.select_folder(self)

    def list_files(self):
        file_operations.list_files(self)

    def update_extensions(self):
        file_operations.update_extensions(self)

    def update_preview(self, event=None):
        image_processing.update_preview(self, event)

    def rename_single_file(self):
        file_operations.rename_single_file(self)

    def start_shortcut_assignment(self, index):
        if self.is_assigning_shortcut:
            return
        self.is_assigning_shortcut = True
        self.shortcut_assign_index = index
        self.shortcut_buttons[index].config(text="Tryck tangent...")
        self.root.bind("<Key>", self.capture_new_shortcut)

    def capture_new_shortcut(self, event):
        if not self.is_assigning_shortcut:
            return
        self.root.unbind("<Key>")
        self.is_assigning_shortcut = False
        assign_index = self.shortcut_assign_index
        self.shortcut_assign_index = None
        new_key = event.keysym.upper()
        if new_key in config.DISALLOWED_KEYS:
            messagebox.showwarning("Ogiltig tangent", f"Tangent {new_key} kan inte användas.")
            self.shortcut_buttons[assign_index].config(text="N/A")
            return
        if new_key in self.shortcut_keys and self.shortcut_keys.index(new_key) != assign_index:
            messagebox.showwarning("Tangent upptagen", f"Tangent '{new_key}' används redan.")
            self.shortcut_buttons[assign_index].config(text="N/A")
            return
        self.shortcut_keys[assign_index] = new_key
        self.shortcut_buttons[assign_index].config(text=new_key)
        self.save_settings()
        self.setup_keyboard_shortcuts()

    def setup_keyboard_shortcuts(self):
        for key in config.ALLOWED_SHORTCUT_KEYS:
            try:
                self.root.unbind(f"<{key}>")
            except tk.TclError:
                pass
        for i, key in enumerate(self.shortcut_keys):
            if key and key in config.ALLOWED_SHORTCUT_KEYS:
                if i < 10:
                    self.root.bind(f"<{key}>", lambda event, index=i: self.handle_shortcut(index, event))
                elif i == 10:
                    self.root.bind(f"<{key}>", lambda event: self.archive_file())
                elif i == 11:
                    self.root.bind(f"<{key}>", lambda event: self.undo_archive())

    def handle_shortcut(self, index, event):
        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Varning", "Ingen fil är vald.")
            return
        if index >= len(self.text_entries):
            return
        tag = self.text_entries[index].get()
        if not tag:
            messagebox.showwarning("Varning", f"Text {index+1} är tom. Ange en tagg först.")
            return

        for idx in selected_indices:
            old_rel_path = self.file_listbox.get(idx)
            old_full_path = os.path.join(self.folder, old_rel_path)
            dir_name = os.path.dirname(old_full_path)
            filename, ext = os.path.splitext(os.path.basename(old_rel_path))
            new_filename = f"{filename}{tag}{ext}"
            new_full_path = os.path.join(dir_name, new_filename)
            try:
                if old_full_path != new_full_path:
                    os.rename(old_full_path, new_full_path)
                    new_rel_path = os.path.relpath(new_full_path, self.folder)
                    self.file_listbox.delete(idx)
                    self.file_listbox.insert(idx, new_rel_path)
                    self.file_listbox.selection_set(idx)
            except Exception as e:
                messagebox.showerror("Fel vid namnbyte", f"Kunde inte byta namn:\n{str(e)}")
        self.update_preview(None)

    def on_close(self):
        self.save_settings()
        self.root.destroy()

    def save_settings(self):
        config.save_settings(self)

    def load_settings(self):
        settings = config.load_settings()
        self.folder = settings.get("last_folder", "")
        loaded_shortcut_keys = settings.get("shortcut_keys", list(config.DEFAULT_SHORTCUT_KEYS))
        self.shortcut_keys = loaded_shortcut_keys + [""] * (len(config.DEFAULT_SHORTCUT_KEYS) - len(loaded_shortcut_keys))
        loaded_tags = settings.get("tags", [""] * len(self.shortcut_keys))
        self.tags = loaded_tags + [""] * (len(self.shortcut_keys) - len(loaded_tags))
        self.allowed_extensions = settings.get("allowed_extensions", list(config.DEFAULT_ALLOWED_EXTENSIONS))
        if not self.allowed_extensions:
            self.allowed_extensions = list(config.DEFAULT_ALLOWED_EXTENSIONS)
            print("Loaded extensions were empty, reverting to default.")
        self.path_label.config(text=f"Sökväg: {self.folder}" if self.folder else "Sökväg: Ingen katalog vald")
        self.extension_entry.delete(0, tk.END)
        self.extension_entry.insert(0, ";".join(self.allowed_extensions))
        for i, key in enumerate(self.shortcut_keys):
            self.shortcut_buttons[i].config(text=key if key else "N/A")
        for i, tag in enumerate(self.tags):
            if i < len(self.text_entries):
                self.text_entries[i].delete(0, tk.END)
                self.text_entries[i].insert(0, tag)
        window_geometry = settings.get("window_geometry", "800x600+100+100")
        self.root.geometry(window_geometry)
        self.saved_horizontal_sash_pos = settings.get("horizontal_sash_pos", 300)
        self.saved_vertical_sash_pos = settings.get("vertical_sash_pos", 400)
        self.saved_metadata_sash_pos = settings.get("metadata_sash_pos", 300)
        self.imgbb_api_key = settings.get("imgbb_api_key", "")
        self.serpapi_api_key = settings.get("serpapi_api_key", "")
        self.google_maps_api_key = settings.get("google_maps_api_key", "")
        self.archived_files = settings.get("archived_files", [])
        self.external_viewer_path = settings.get("external_viewer_path", "")
