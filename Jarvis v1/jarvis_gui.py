import tkinter as tk
from threading import Thread
from main import run_jarvis


def start():
    Thread(target=run_jarvis, daemon=True).start()


app = tk.Tk()
app.title("Jarvis AI")
app.geometry("500x300")
app.configure(bg="black")

label = tk.Label(app, text="JARVIS ACTIVE", fg="lime", bg="black", font=("Arial", 20))
label.pack(pady=50)

button = tk.Button(app, text="Start Jarvis", command=start)
button.pack()

app.mainloop()
