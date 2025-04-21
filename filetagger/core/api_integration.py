# core/api_integration.py
import requests
from tkinter import messagebox
from serpapi import GoogleSearch
import threading
import os # <--- DENNA RAD MÅSTE FINNAS!
import tkinter as tk # <-- LÄGG TILL DENNA IMPORT

def upload_image_to_imgbb(file_path, imgbb_api_key):
    try:
        with open(file_path, "rb") as file:
            url = "https://api.imgbb.com/1/upload"
            data = {"key": imgbb_api_key}
            files = {"image": (os.path.basename(file_path), file, "image/jpeg")}
            response = requests.post(url, data=data, files=files)
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                return data["data"]["url"]
            else:
                messagebox.showerror("Fel", f"ImgBB-svar indikerar ett fel: {data.get('error', 'Okänt fel')}")
                return None
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Fel", f"Kunde inte ladda upp bild till ImgBB: {e}")
        return None
    except Exception as e:
        messagebox.showerror("Fel", f"Ett oväntat fel uppstod: {e}")
        return None

def analyze_image_with_google_lens(app):
    selected_indices = app.file_listbox.curselection()
    if len(selected_indices) != 1:
        messagebox.showwarning("Varning", "Välj exakt en fil för analys.")
        return

    app.analyze_btn.config(state="disabled")
    app.show_progress()

    thread = threading.Thread(target=_analyze_image_thread, args=(app, selected_indices))
    thread.start()

def _analyze_image_thread(app, selected_indices):
    try:
        rel_path = app.file_listbox.get(selected_indices[0])
        file_path = os.path.join(app.folder, rel_path)

        image_url = upload_image_to_imgbb(file_path, app.imgbb_api_key)
        if not image_url:
            app.root.after(0, lambda: app.hide_progress())
            app.root.after(0, lambda: app.analyze_btn.config(state="normal"))
            return

        params = {
            "engine": "google_lens",
            "url": image_url,
            "api_key": app.serpapi_api_key,
            "hl": "sv"
        }
        search = GoogleSearch(params)
        results = search.get_dict()

        tags = []
        if "knowledge_graph" in results:
            knowledge = results["knowledge_graph"]
            if isinstance(knowledge, list) and knowledge:
                knowledge = knowledge[0]
            if "title" in knowledge:
                tags.append(knowledge["title"].lower())

        if "visual_matches" in results:
            existing_tags = set(tags)
            for match in results["visual_matches"][:5]:
                if "title" in match:
                    title = match["title"].lower().split(" — ")[0].strip()
                    for generic in ["wikipedia", "image", "photo", "stock", "shutterstock"]:
                        title = title.replace(generic, "").strip()
                    if title and len(title) > 2 and title not in existing_tags:
                        tags.append(title)
                        existing_tags.add(title)

        if "text" in results and results["text"]:
            text = results["text"].lower().strip()
            if len(text) > 3 and text not in tags:
                tags.append(text)

        tags = list(dict.fromkeys(tags))
        tags = [tag for tag in tags if len(tag) > 2][:len(app.text_entries)]

        app.root.after(0, lambda: _update_tags(app, tags))
    except Exception as e:
        app.root.after(0, lambda: messagebox.showerror("Fel", f"Kunde inte analysera bilden med Google Lens: {e}"))
    finally:
        app.root.after(0, lambda: app.hide_progress())
        app.root.after(0, lambda: app.analyze_btn.config(state="normal"))

def _update_tags(app, tags):
    print(f"--- _update_tags called with: {tags} ---") # Debug
    try:
        for i, tag in enumerate(tags):
            if i < len(app.text_entries):
                # Nu kommer tk.END att vara definierad
                app.text_entries[i].delete(0, tk.END)
                app.text_entries[i].insert(0, tag)
                if i < len(app.tags):
                    app.tags[i] = tag
        app.save_settings() # Anropet till save_settings var korrekt här
        messagebox.showinfo("Klart", f"Taggar har genererats och sparats:\n{', '.join(tags)}")
    except Exception as e:
        # ... (felhantering) ...
        messagebox.showerror("Fel vid uppdatering", f"Kunde inte uppdatera taggfälten: {e}")

def get_gps_coordinates_from_location(location, google_maps_api_key):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": location,
        "key": google_maps_api_key
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if data["status"] != "OK":
        raise Exception(f"Kunde inte hämta koordinater: {data['status']}")

    if not data["results"]:
        raise Exception("Inga resultat hittades för platsen.")

    lat = data["results"][0]["geometry"]["location"]["lat"]
    lon = data["results"][0]["geometry"]["location"]["lng"]
    return lat, lon

def get_place_from_gps_coordinates(lat, lon, google_maps_api_key, text_entries):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "latlng": f"{lat},{lon}",
        "key": google_maps_api_key
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if data["status"] != "OK":
        error_message = data.get("error_message", "Okänt fel")
        raise Exception(f"Kunde inte hämta plats: {data['status']}\nFelmeddelande: {error_message}")

    if not data["results"]:
        raise Exception("Inga resultat hittades för koordinaterna.")

    place_tags = []
    existing_tags = set()

    for result in data["results"]:
        for component in result.get("address_components", []):
            name = component.get("long_name", "").strip().lower()
            types = component.get("types", [])
            if "political" in types or "country" in types or "postal_code" in types:
                continue
            if name and len(name) > 2 and name not in existing_tags:
                place_tags.append(name)
                existing_tags.add(name)

        formatted_address = result.get("formatted_address", "").strip().lower()
        address_parts = [part.strip() for part in formatted_address.split(",")]
        for part in address_parts:
            if part in existing_tags or len(part) <= 2 or part.isdigit():
                continue
            for generic in ["sweden", "sverige", "county", "municipality"]:
                part = part.replace(generic, "").strip()
            if part and len(part) > 2 and part not in existing_tags:
                place_tags.append(part)
                existing_tags.add(part)

    place_tags = list(dict.fromkeys(place_tags))
    place_tags = [tag for tag in place_tags if len(tag) > 2][:len(text_entries)]
    return place_tags
