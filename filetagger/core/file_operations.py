# core/file_operations.py
import os
import tkinter as tk
from tkinter import filedialog, messagebox

def select_folder(app):
    initial_dir = app.folder if app.folder and os.path.isdir(app.folder) else os.path.expanduser("~")
    folder_selected = filedialog.askdirectory(initialdir=initial_dir)
    if folder_selected:
        app.folder = folder_selected
        app.path_label.config(text=f"Sökväg: {app.folder}")
        app.archived_files = []
        app.last_archived_label.config(text="Senast arkiverad: Ingen")
        app.save_settings()
        list_files(app)

def list_files(app):
    app.file_listbox.delete(0, tk.END)
    if not app.folder or not os.path.isdir(app.folder):
        app.file_count_label.config(text="Filer: 0")
        app.file_listbox.insert(tk.END, "Katalogen är ogiltig eller tom.")
        print("Folder is invalid or empty.")
        return

    file_count = 0
    for root_dir, _, files in os.walk(app.folder):
        if "Arkiv" in os.path.relpath(root_dir, app.folder).split(os.sep):
            continue
        for filename in files:
            if any(filename.lower().endswith(ext.lower()) for ext in app.allowed_extensions):
                rel_path = os.path.relpath(os.path.join(root_dir, filename), app.folder)
                app.file_listbox.insert(tk.END, rel_path)
                file_count += 1

    app.file_count_label.config(text=f"Filer: {file_count}")
    if file_count == 0:
        app.file_listbox.insert(tk.END, "Inga matchande filer hittades.")
        print("No matching files found.")
    app.update_preview(None)

def update_extensions(app):
    ext_text = app.extension_entry.get()
    extensions = [ext.strip().lower() for ext in ext_text.split(";") if ext.strip()]
    app.allowed_extensions = [ext if ext.startswith('.') else '.' + ext for ext in extensions]
    if not app.allowed_extensions:
        from filetagger.core.config import DEFAULT_ALLOWED_EXTENSIONS
        app.allowed_extensions = list(DEFAULT_ALLOWED_EXTENSIONS)
        print("No extensions provided, reverting to default.")
    app.save_settings()
    list_files(app)

def archive_file(app):
    selected_indices = app.file_listbox.curselection()
    if len(selected_indices) != 1:
        messagebox.showwarning("Varning", "Välj exakt en fil att arkivera.")
        return

    idx = selected_indices[0]
    rel_path = app.file_listbox.get(idx)
    old_full_path = os.path.join(app.folder, rel_path)

    archive_dir = os.path.join(app.folder, "Arkiv")
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)

    filename = os.path.basename(rel_path)
    new_full_path = os.path.join(archive_dir, filename)
    try:
        os.rename(old_full_path, new_full_path)
        app.archived_files.append((old_full_path, new_full_path))
        app.last_archived_label.config(text=f"Senast arkiverad: {filename}")
        app.file_listbox.delete(idx)
        file_count = int(app.file_count_label.cget("text").split(": ")[1]) - 1
        app.file_count_label.config(text=f"Filer: {file_count}")
        app.update_preview(None)
        app.save_settings()
    except Exception as e:
        messagebox.showerror("Fel vid arkivering", f"Kunde inte arkivera filen:\n{str(e)}")

def undo_archive(app):
    if not app.archived_files:
        messagebox.showwarning("Varning", "Ingen arkivering att ångra.")
        return

    old_full_path, new_full_path = app.archived_files.pop()
    try:
        os.rename(new_full_path, old_full_path)
        rel_path = os.path.relpath(old_full_path, app.folder)
        app.file_listbox.insert(tk.END, rel_path)
        file_count = int(app.file_count_label.cget("text").split(": ")[1]) + 1
        app.file_count_label.config(text=f"Filer: {file_count}")
        app.file_listbox.selection_set(tk.END)
        app.last_archived_label.config(text="Senast arkiverad: Ingen")
        app.update_preview(None)
        app.save_settings()
    except Exception as e:
        messagebox.showerror("Fel vid ångring", f"Kunde inte ångra arkiveringen:\n{str(e)}")
        app.archived_files.append((old_full_path, new_full_path))

def rename_single_file(app):
    selected_indices = app.file_listbox.curselection()
    if len(selected_indices) != 1:
        messagebox.showwarning("Varning", "Välj exakt en fil.")
        return
    new_name_part = app.single_entry.get().strip()
    if not new_name_part:
        messagebox.showwarning("Varning", "Ange ett nytt namn.")
        return

    idx = selected_indices[0]
    old_rel_path = app.file_listbox.get(idx)
    old_full_path = os.path.join(app.folder, old_rel_path)
    dir_name = os.path.dirname(old_full_path)
    _, ext = os.path.splitext(old_rel_path)
    new_filename = f"{new_name_part}{ext}"
    new_full_path = os.path.join(dir_name, new_filename)
    try:
        if old_full_path != new_full_path:
            os.rename(old_full_path, new_full_path)
            new_rel_path = os.path.relpath(new_full_path, app.folder)
            app.file_listbox.delete(idx)
            app.file_listbox.insert(idx, new_rel_path)
            app.file_listbox.selection_set(idx)
        app.update_preview(None)
    except Exception as e:
        messagebox.showerror("Fel vid namnbyte", f"Kunde inte byta namn:\n{str(e)}")

def open_in_external_viewer(app, event):
    if not app.external_viewer_path:
        messagebox.showwarning("Varning", "Ingen extern bildvisare är konfigurerad i settings.json.")
        return

    selected_indices = app.file_listbox.curselection()
    if len(selected_indices) != 1:
        messagebox.showwarning("Varning", "Välj exakt en fil för att visa i extern bildvisare.")
        return

    rel_path = app.file_listbox.get(selected_indices[0])
    file_path = os.path.join(app.folder, rel_path)
    if not os.path.exists(file_path):
        messagebox.showerror("Fel", "Filen hittades inte.")
        return

    try:
        os.startfile(file_path)
    except FileNotFoundError:
        messagebox.showerror("Fel", f"Kunde inte hitta bildvisaren på: {app.external_viewer_path}")
    except Exception as e:
        messagebox.showerror("Fel", f"Ett oväntat fel uppstod: {e}")
