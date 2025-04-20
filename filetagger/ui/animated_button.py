# ui/animated_button.py
import tkinter as tk
from tkinter import font as tkFont
from PIL import Image, ImageTk, ImageFilter, ImageOps, ImageDraw
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

class AnimatedImageButton(tk.Button):
    """En knapp med en animerad bakgrundsbild och text ovanpå."""
    def __init__(self, master, text, base_pil_image, command=None, **kwargs):
        # Hämta fonten från ttkbootstrap-temat för sektionstitlar
        style = ttk.Style()
        font_name = style.lookup("TLabelFrame.Label", "font", default=("Helvetica", 10, "bold"))
        self.font = tkFont.nametofont(font_name) if isinstance(font_name, str) else tkFont.Font(family="Helvetica", size=10, weight="bold")

        # Mät textens storlek
        text_width = self.font.measure(text)
        text_height = self.font.metrics("linespace")

        # Lägg till marginaler runt texten
        padding_x = 10  # Horisontell padding
        padding_y = 5   # Vertikal padding
        button_width = text_width + 2 * padding_x
        button_height = text_height + 2 * padding_y

        # Skapa en kopia av basbilden och skala om den till knappens storlek
        self.base_pil_image = base_pil_image.resize((button_width, button_height), Image.Resampling.LANCZOS)

        super().__init__(
            master,
            text=text,
            font=self.font,
            compound=tk.CENTER,  # Placera texten ovanpå bilden
            borderwidth=0,
            highlightthickness=0,
            width=button_width,
            height=button_height,
            command=command,
            **kwargs
        )

        # Skapa PhotoImage för olika tillstånd
        self.passive_image = ImageTk.PhotoImage(self.base_pil_image)
        self.hover_image = self.create_hover_image(self.base_pil_image)
        self.active_image = self.create_active_image(self.base_pil_image)

        # Sätt initial bild (passiv)
        self.config(image=self.passive_image)

        # Bind händelser för hover och klick
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)

    def create_hover_image(self, pil_image):
        """Skapar en hover-bild med Emboss-effekt och en ram."""
        # Tillämpa Emboss-effekt
        emboss_image = pil_image.filter(ImageFilter.EMBOSS)

        # Lägg till en ram
        draw = ImageDraw.Draw(emboss_image)
        width, height = emboss_image.size
        draw.rectangle([0, 0, width-1, height-1], outline="yellow", width=2)

        # Konvertera till PhotoImage
        return ImageTk.PhotoImage(emboss_image)

    def create_active_image(self, pil_image):
        """Skapar en aktiv-bild med Negative-effekt."""
        # Konvertera till RGB om bilden har en alfakanal
        if pil_image.mode == "RGBA":
            pil_image = pil_image.convert("RGB")

        # Tillämpa Negative-effekt (invertera färger)
        negative_image = ImageOps.invert(pil_image)

        # Konvertera till PhotoImage
        return ImageTk.PhotoImage(negative_image)

    def on_enter(self, event):
        self.config(image=self.hover_image)

    def on_leave(self, event):
        self.config(image=self.passive_image)

    def on_press(self, event):
        self.config(image=self.active_image)

    def on_release(self, event):
        if self.winfo_containing(event.x_root, event.y_root) == self:
            self.config(image=self.hover_image)
        else:
            self.config(image=self.passive_image)
