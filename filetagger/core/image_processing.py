# core/image_processing.py
import os
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from datetime import datetime
import piexif
import webbrowser

def update_preview(app, event=None):
    app.preview_canvas.delete("all")
    selected_indices = app.file_listbox.curselection()
    if len(selected_indices) == 1:
        try:
            selected_rel_path = app.file_listbox.get(selected_indices[0])
            filename = os.path.basename(selected_rel_path)
            name_part, _ = os.path.splitext(filename)
            app.single_entry.delete(0, tk.END)
            app.single_entry.insert(0, name_part)
            file_path = os.path.join(app.folder, selected_rel_path)
            update_metadata(app, file_path)
        except:
            app.single_entry.delete(0, tk.END)
            update_metadata(app, None)
    else:
        app.single_entry.delete(0, tk.END)
        update_metadata(app, None)

    if selected_indices:
        try:
            first_selected_rel_path = app.file_listbox.get(selected_indices[0])
            file_path = os.path.join(app.folder, first_selected_rel_path)
            if os.path.exists(file_path):
                image = Image.open(file_path)
                canvas_width = app.preview_canvas.winfo_width()
                canvas_height = app.preview_canvas.winfo_height()
                if canvas_width > 1 and canvas_height > 1:
                    image.thumbnail((canvas_width - 10, canvas_height - 10))
                    app.current_photo = ImageTk.PhotoImage(image)
                    x = (canvas_width - app.current_photo.width()) // 2
                    y = (canvas_height - app.current_photo.height()) // 2
                    app.preview_canvas.create_image(x, y, anchor=tk.NW, image=app.current_photo)
        except Exception as e:
            print(f"Error loading preview: {e}")

def update_metadata(app, file_path):
    app.current_file_path = file_path
    for field in app.metadata_entries:
        app.metadata_entries[field].delete(0, tk.END)
        app.metadata_entries[field].insert(0, "N/A")
    for field in app.metadata_labels:
        app.metadata_labels[field].config(text="N/A")

    if file_path is None or not os.path.exists(file_path):
        return

    try:
        with Image.open(file_path) as img:
            width, height = img.size
            app.metadata_labels["Bildstorlek"].config(text=f"{width}×{height} pixlar")

            exif_raw = img.info.get("exif")
            if exif_raw and isinstance(exif_raw, bytes) and len(exif_raw) > 0:
                try:
                    exif_dict = piexif.load(exif_raw)
                    exif_data = exif_dict.get("Exif", {})
                    zeroth_ifd = exif_dict.get("0th", {})
                    gps_data = exif_dict.get("GPS", {})

                    date_taken = exif_data.get(piexif.ExifIFD.DateTimeOriginal)
                    if date_taken:
                        date_taken = date_taken.decode('utf-8')
                        app.metadata_entries["Fotodatum"].delete(0, tk.END)
                        app.metadata_entries["Fotodatum"].insert(0, date_taken)
                    else:
                        date_digitized = exif_data.get(piexif.ExifIFD.DateTimeDigitized)
                        if date_digitized:
                            date_digitized = date_digitized.decode('utf-8')
                            app.metadata_entries["Fotodatum"].delete(0, tk.END)
                            app.metadata_entries["Fotodatum"].insert(0, date_digitized)

                    make = zeroth_ifd.get(piexif.ImageIFD.Make)
                    if make:
                        app.metadata_labels["Kameratillverkare"].config(text=make.decode('utf-8'))
                    model = zeroth_ifd.get(piexif.ImageIFD.Model)
                    if model:
                        app.metadata_labels["Kameramodell"].config(text=model.decode('utf-8'))

                    lat = get_gps_coord(gps_data, piexif.GPSIFD.GPSLatitude, piexif.GPSIFD.GPSLatitudeRef)
                    lon = get_gps_coord(gps_data, piexif.GPSIFD.GPSLongitude, piexif.GPSIFD.GPSLongitudeRef)
                    if lat:
                        app.metadata_labels["GPS Latitud"].config(text=f"{lat:.6f}")
                    if lon:
                        app.metadata_labels["GPS Longitud"].config(text=f"{lon:.6f}")
                except Exception as e:
                    print(f"Fel vid läsning av EXIF-data: {e}")
            else:
                print("Ingen EXIF-data tillgänglig för denna fil.")

        mtime = os.path.getmtime(file_path)
        last_modified = datetime.fromtimestamp(mtime).strftime('%Y:%m:%d %H:%M:%S')
        app.metadata_labels["Senast ändrad"].config(text=last_modified)

        file_size = os.path.getsize(file_path) / 1024  # KB
        if file_size >= 1024:
            file_size = file_size / 1024  # MB
            size_str = f"{file_size:.2f} MB"
        else:
            size_str = f"{file_size:.2f} KB"
        current_text = app.metadata_labels["Bildstorlek"].cget("text")
        app.metadata_labels["Bildstorlek"].config(text=f"{current_text}, {size_str}")

    except Exception as e:
        print(f"Fel vid läsning av metadata: {e}")

def get_gps_coord(gps_data, coord_tag, ref_tag):
    coord = gps_data.get(coord_tag)
    ref = gps_data.get(ref_tag)
    if not coord or not ref:
        return None
    ref = ref.decode('utf-8')
    degrees = coord[0][0] / coord[0][1]
    minutes = coord[1][0] / coord[1][1]
    seconds = coord[2][0] / coord[2][1]
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if ref in ["S", "W"]:
        decimal = -decimal
    return decimal

def save_metadata(app):
    if not app.current_file_path:
        messagebox.showwarning("Varning", "Ingen fil är vald.")
        return

    try:
        img = Image.open(app.current_file_path)
        exif_raw = img.info.get("exif")
        if exif_raw and isinstance(exif_raw, bytes) and len(exif_raw) > 0:
            try:
                exif_dict = piexif.load(exif_raw)
            except Exception as e:
                messagebox.showerror("Fel", f"Kunde inte läsa befintlig EXIF-data: {e}")
                img.close()
                return
        else:
            exif_dict = {
                "0th": {},
                "Exif": {},
                "GPS": {},
                "1st": {},
                "thumbnail": None
            }

        fotodatum = app.metadata_entries["Fotodatum"].get()
        if fotodatum and fotodatum != "N/A":
            try:
                datetime.strptime(fotodatum, '%Y:%m:%d %H:%M:%S')
                exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = fotodatum.encode('utf-8')
            except ValueError:
                messagebox.showerror("Fel", "Fotodatum måste vara i formatet YYYY:MM:DD HH:MM:SS (t.ex. 2025:04:14 12:00:00)")
                img.close()
                return

        exif_bytes = piexif.dump(exif_dict)
        img.save(app.current_file_path, exif=exif_bytes)
        img.close()

        messagebox.showinfo("Klart", "Metadata har sparats!")
        update_metadata(app, app.current_file_path)

    except Exception as e:
        messagebox.showerror("Fel", f"Kunde inte spara metadata: {e}")

def fetch_and_save_gps(app):
    if not app.current_file_path:
        messagebox.showwarning("Varning", "Ingen fil är vald.")
        return

    location = app.gps_location_entry.get().strip()
    if not location:
        messagebox.showwarning("Varning", "Ange en plats för att hämta GPS-koordinater.")
        return

    img = Image.open(app.current_file_path)
    exif_raw = img.info.get("exif")
    lat = None
    lon = None
    if exif_raw and isinstance(exif_raw, bytes) and len(exif_raw) > 0:
        try:
            exif_dict = piexif.load(exif_raw)
            gps_data = exif_dict.get("GPS", {})
            lat = get_gps_coord(gps_data, piexif.GPSIFD.GPSLatitude, piexif.GPSIFD.GPSLatitudeRef)
            lon = get_gps_coord(gps_data, piexif.GPSIFD.GPSLongitude, piexif.GPSIFD.GPSLongitudeRef)
        except Exception as e:
            messagebox.showerror("Fel", f"Kunde inte läsa befintlig EXIF-data: {e}")
            img.close()
            return
    img.close()

    if lat is not None and lon is not None:
        result = messagebox.askyesno(
            "Varning",
            "Befintliga GPS-koordinater finns redan i bilden.\nVill du verkligen skriva över dem?"
        )
        if not result:
            return

    from filetagger.core.api_integration import get_gps_coordinates_from_location
    try:
        lat, lon = get_gps_coordinates_from_location(location, app.google_maps_api_key)

        save_gps_to_image(app, lat, lon)

        app.metadata_labels["GPS Latitud"].config(text=f"{lat:.6f}")
        app.metadata_labels["GPS Longitud"].config(text=f"{lon:.6f}")
        messagebox.showinfo("Klart", f"GPS-koordinater för {location} har sparats: Latitud {lat:.6f}, Longitud {lon:.6f}")

    except Exception as e:
        messagebox.showerror("Fel", f"Kunde inte hämta eller spara GPS-koordinater: {e}")

def fetch_place_from_gps(app):
    if not app.current_file_path:
        messagebox.showwarning("Varning", "Ingen fil är vald.")
        return

    lat_str = app.metadata_labels["GPS Latitud"].cget("text")
    lon_str = app.metadata_labels["GPS Longitud"].cget("text")

    if lat_str == "N/A" or lon_str == "N/A":
        messagebox.showwarning("Varning", "Inga GPS-koordinater finns för den valda bilden. Hämta GPS först.")
        return

    try:
        lat = float(lat_str)
        lon = float(lon_str)
    except ValueError:
        messagebox.showerror("Fel", "Ogiltiga GPS-koordinater i metadata.")
        return

    from filetagger.core.api_integration import get_place_from_gps_coordinates
    try:
        place_tags = get_place_from_gps_coordinates(lat, lon, app.google_maps_api_key, app.text_entries)

        if place_tags:
            for i, tag in enumerate(place_tags):
                if i < len(app.text_entries):
                    app.text_entries[i].delete(0, tk.END)
                    app.text_entries[i].insert(0, tag)
                    app.tags[i] = tag
            app.save_settings()
            messagebox.showinfo("Klart", f"Platsinformation har hämtats och sparats i taggfälten:\n{', '.join(place_tags)}")
        else:
            messagebox.showwarning("Varning", "Ingen användbar platsinformation kunde hämtas.")

    except Exception as e:
        messagebox.showerror("Fel", f"Kunde inte hämta plats från GPS-koordinater: {e}")

def open_google_maps(app, field):
    lat_str = app.metadata_labels["GPS Latitud"].cget("text")
    lon_str = app.metadata_labels["GPS Longitud"].cget("text")

    if lat_str == "N/A" or lon_str == "N/A":
        messagebox.showwarning("Varning", "Inga GPS-koordinater finns för att visa på Google Maps.")
        return

    try:
        lat = float(lat_str)
        lon = float(lon_str)
    except ValueError:
        messagebox.showerror("Fel", "Ogiltiga GPS-koordinater i metadata.")
        return

    maps_url = f"https://www.google.com/maps?q={lat},{lon}"
    try:
        webbrowser.open(maps_url)
    except Exception as e:
        messagebox.showerror("Fel", f"Kunde inte öppna Google Maps: {e}")

def save_gps_to_image(app, lat, lon):
    img = Image.open(app.current_file_path)
    exif_raw = img.info.get("exif")
    if exif_raw and isinstance(exif_raw, bytes) and len(exif_raw) > 0:
        try:
            exif_dict = piexif.load(exif_raw)
        except Exception as e:
            messagebox.showerror("Fel", f"Kunde inte läsa befintlig EXIF-data: {e}")
            img.close()
            return
    else:
        exif_dict = {
            "0th": {},
            "Exif": {},
            "GPS": {},
            "1st": {},
            "thumbnail": None
        }

    lat_ref = "N" if lat >= 0 else "S"
    lon_ref = "E" if lon >= 0 else "W"
    lat = abs(lat)
    lon = abs(lon)

    lat_deg = int(lat)
    lat_min = int((lat - lat_deg) * 60)
    lat_sec = int((lat - lat_deg - lat_min / 60) * 3600 * 10000)
    lon_deg = int(lon)
    lon_min = int((lon - lon_deg) * 60)
    lon_sec = int((lon - lon_deg - lon_min / 60) * 3600 * 10000)

    exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = [(lat_deg, 1), (lat_min, 1), (lat_sec, 10000)]
    exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = lat_ref.encode('utf-8')
    exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = [(lon_deg, 1), (lon_min, 1), (lon_sec, 10000)]
    exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = lon_ref.encode('utf-8')

    try:
        exif_bytes = piexif.dump(exif_dict)
        img.save(app.current_file_path, exif=exif_bytes)
    except Exception as e:
        messagebox.showerror("Fel", f"Kunde inte spara EXIF-data: {e}")
    finally:
        img.close()
