# import tkinter as tk


def get_video_resolution():
    return 1280, 720  # default

# def get_video_resolution():
#     width, height = 1280, 720  # default

#     def select_long():
#         nonlocal width, height
#         width, height = 1280, 720
#         root.destroy()

#     def select_short():
#         nonlocal width, height
#         width, height = 1080, 1920
#         root.destroy()

#     root = tk.Tk()
#     root.title("Select Video Type")
#     root.geometry("350x200")
#     root.configure(bg="#1e1e1e")

#     frame = tk.Frame(root, bg="#1e1e1e")
#     frame.pack(expand=True)

#     tk.Label(
#         frame,
#         text="Choose Video Format",
#         font=("Arial", 14, "bold"),
#         fg="white",
#         bg="#1e1e1e"
#     ).pack(pady=15)

#     tk.Button(
#         frame,
#         text="📺 Long Video (1280 x 720)",
#         bg="#4CAF50",
#         fg="white",
#         width=25,
#         height=2,
#         bd=0,
#         command=select_long
#     ).pack(pady=5)

#     tk.Button(
#         frame,
#         text="📱 Short Video (1080 x 1920)",
#         bg="#2196F3",
#         fg="white",
#         width=25,
#         height=2,
#         bd=0,
#         command=select_short
#     ).pack(pady=5)

#     root.mainloop()

#     return width, height