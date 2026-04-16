import os
import subprocess
import math
import shutil
from icrawler.builtin import BingImageCrawler
import os
# from tkinter import Tk, filedialog, messagebox
import signal
import sys
from home.models import VideoJob


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

IMAGE_FOLDER = os.path.join(BASE_DIR, "images")
VOICE_FOLDER = os.path.join(BASE_DIR, "voice_over")
KEYWORD_FOLDER = os.path.join(BASE_DIR, "keywords")

FFMPEG_FOLDER = os.path.join(BASE_DIR, "ffmpeg")

# FFMPEG_PATH = os.path.join(FFMPEG_FOLDER, "ffmpeg.exe")
# FFPROBE_PATH = os.path.join(FFMPEG_FOLDER, "ffprobe.exe")
FFMPEG_PATH = "ffmpeg"
FFPROBE_PATH = "ffprobe"
FFPLAY_PATH = os.path.join(FFMPEG_FOLDER, "ffplay.exe")

IMAGE_DURATION = 3  # seconds per image
MAX_IMAGES = 70

os.makedirs(IMAGE_FOLDER, exist_ok=True)


# -----------------------------
# Check if folders exist
# -----------------------------
def check_folders():

    os.makedirs(IMAGE_FOLDER, exist_ok=True)
    os.makedirs(VOICE_FOLDER, exist_ok=True)


# -----------------------------
# Pick Voice over
# -----------------------------
# def select_voice_file():
#     root = Tk()
#     root.withdraw()

#     file_path = filedialog.askopenfilename(
#         initialdir=VOICE_FOLDER,
#         title="Select Voice Over",
#         filetypes=[("Audio Files", "*.mp3 *.wav")]
#     )

#     if not file_path:
#         print("No voice file selected. Exiting.")
#         exit()

#     return file_path

from home.models import VideoJob

def update_status(job_id, message, progress=None):
    if job_id:
        data = {"status_message": message}
        if progress is not None:
            data["progress"] = progress
        VideoJob.objects.filter(id=job_id).update(**data)
        print(message)


# voice_file = select_voice_file()
# print("Selected Voice:", voice_file)


# -----------------------------
# Check ffmpeg
# -----------------------------
def check_ffmpeg():

    # if not os.path.exists(FFPROBE_PATH):
    #     print("ERROR: ffprobe.exe not found in ffmpeg folder")
    #     exit()
    print("Using system ffmpeg")


# -----------------------------
# Clear old images
# -----------------------------
def clear_images():

    if not os.path.exists(IMAGE_FOLDER):
        os.makedirs(IMAGE_FOLDER)

    for file in os.listdir(IMAGE_FOLDER):

        path = os.path.join(IMAGE_FOLDER, file)

        if os.path.isfile(path):
            os.remove(path)

    print("Old images deleted.")


# -----------------------------
# Find voice file
# -----------------------------
# def get_voice_file():

#     for file in os.listdir(VOICE_FOLDER):

#         if file.lower().endswith((".mp3", ".wav")):
#             return os.path.join(VOICE_FOLDER, file)

#     return None


# -----------------------------
# Get audio duration
# -----------------------------
def get_audio_duration(audio_path):

    cmd = [
        FFPROBE_PATH,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE)

    duration = float(result.stdout)

    return math.ceil(duration)


# -----------------------------
# Get keywords
# -----------------------------
# def get_keywords():

#     while True:

#         user_input = input("Enter at least 3 keywords separated by comma: ")

#         keywords = [k.strip() for k in user_input.split(",") if k.strip()]

#         if len(keywords) >= 3:
#             return keywords

#         else:
#             print("Please enter minimum 3 keywords.")


# -----------------------------
# Download images
# -----------------------------
import cv2

def download_images(keyword, amount, start_index, job_id=None):

    print(f"\nDownloading images for: {keyword}")

    temp_folder = os.path.join(IMAGE_FOLDER, "temp")

    crawler = BingImageCrawler(
        downloader_threads=4,
        parser_threads=2,
        storage={'root_dir': temp_folder}
    )

    for attempt in range(3):

        try:
            crawler.crawl(
                keyword=keyword,
                max_num=amount
            )
            break

        except Exception:
            print("Download failed. Retrying...", attempt + 1)

            if attempt == 2:
                print("Skipping keyword:", keyword)


    files = os.listdir(temp_folder)

    count = 0

    allowed_ext = (".jpg", ".jpeg", ".png", ".webp")

    total_files = len(files)
    for i, file in enumerate(files):

        old_path = os.path.join(temp_folder, file)

        ext = os.path.splitext(file)[1].lower()

        if ext not in allowed_ext:
            print("Skipping unsupported file:", file)
            continue

        # verify image is valid
        img = cv2.imread(old_path)

        if img is None:
            print("Skipping corrupted image:", file)
            continue

        new_name = f"img_{start_index + count}{ext}"

        new_path = os.path.join(IMAGE_FOLDER, new_name)

        try:
            shutil.move(old_path, new_path)
        except Exception:
            continue

        print("Saved:", new_path)

        count += 1
        progress = int(((i + 1) / total_files) * 100)

        update_status(job_id, f"Downloading images for: {keyword}", progress)

        if count >= amount:
            break

    shutil.rmtree(temp_folder)


# -----------------------------
# Main
# -----------------------------
def generate_images_from_audio(voice_file,keywords, job_id=None):
    check_folders()
    check_ffmpeg()
    clear_images()

#old method of choosing voice from folder----------------
    # voice_file = get_voice_file()

    # if not voice_file:
    #     print("No voice over found.")
    #     return

    # print("Voice file:", voice_file)
#old method of choosing voice from folder----------------

    duration = get_audio_duration(voice_file)
    print("Voice file:", voice_file)

    duration = get_audio_duration(voice_file)

    print("Audio duration:", duration, "seconds")

    images_needed = math.ceil(duration / IMAGE_DURATION)

    if images_needed > MAX_IMAGES:
        images_needed = MAX_IMAGES

    print("Total images needed:", images_needed)

    # keywords = get_keywords()

    # keywords = ["doremon", "nobita", "pokemon"]

    if not keywords:
        print("No keywords found.")
        return

    print("Keywords:", keywords)

    images_per_keyword = images_needed // len(keywords)

    extra = images_needed % len(keywords)

    index = 0

    update_status(job_id, "Starting image download...")
    for i, keyword in enumerate(keywords):

        amount = images_per_keyword

        if i < extra:
            amount += 1

        download_images(keyword, amount, index,job_id)

        index += amount
        update_status(job_id, f"Downloading images for: {keyword}")

    print("[DEBUG] Collecting images...")

    image_paths = [
        os.path.join(IMAGE_FOLDER, f)
        for f in os.listdir(IMAGE_FOLDER)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]

    print("[DEBUG] Total images found:", len(image_paths))

    print("[DEBUG] Returning to main.py...")

    print("[CLEANUP] Killing leftover threads...")

    update_status(job_id, "All images downloaded",100)
    return image_paths


# if __name__ == "__main__":
#     main()


