#!/usr/bin/env python
# tests/regression/simple_button_app.py
"""
A very simple Tkinter application with a single button.
Used as a target for pyautogui regression tests.
"""
import tkinter as tk


def on_click():
    """Prints a success message and closes the application."""
    print("SUCCESS: Button was clicked by agent.")
    root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("AEGIS Test App")
    root.geometry("200x100")

    button = tk.Button(root, text="Click Me!", command=on_click, font=("Arial", 16))
    button.pack(pady=20, padx=20, expand=True, fill=tk.BOTH)

    root.mainloop()
