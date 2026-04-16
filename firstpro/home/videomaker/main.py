import cv2
import os
import numpy as np
import random
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip
from .video_selector import get_video_resolution
from moviepy.video.fx import Loop
import uuid
import subprocess
from home.models import VideoJob
import shutil


# ---------------- FFMPEG SETUP ----------------

def setup_ffmpeg():
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")

    if not ffmpeg_path:
        raise RuntimeError("ffmpeg not found on system")

    os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_path
    os.environ["FFMPEG_BINARY"] = ffmpeg_path

    if ffprobe_path:
        os.environ["FFPROBE_BINARY"] = ffprobe_path

    print("Using system FFmpeg:", ffmpeg_path)



setup_ffmpeg()


# ---------------- SETTINGS ----------------

# export_folder = "exports"
# sfx_folder = "sfx"
# BG_MUSIC_FOLDER = "bg_music"
# OVERLAY_FOLDER = "overlay"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# export_folder = os.path.join(BASE_DIR, "exports")
export_folder = os.path.join(BASE_DIR, "..", "..", "media")
sfx_folder = os.path.join(BASE_DIR, "sfx")
BG_MUSIC_FOLDER = os.path.join(BASE_DIR, "bg_music")
OVERLAY_FOLDER = os.path.join(BASE_DIR, "overlay")

fps = 30
seconds_per_image = 3
frames_per_image = fps * seconds_per_image
transition_frames = 20
BG_MUSIC_VOLUME = 0.10
OVERLAY_OPACITY = 0.5

#for long video 16:9
# width = 1280
# height = 720

#for short video 9:16
# width = 1080
# height = 1920

width, height = get_video_resolution()

print(f"Selected: {width}x{height}")


# Load sfx
def load_sfx():

    if not os.path.exists(sfx_folder):
        return []

    return [
        os.path.join(sfx_folder, f)
        for f in os.listdir(sfx_folder)
        if f.lower().endswith((".wav", ".mp3"))
    ]

sfx_files = load_sfx()




# pick first mp4 file
overlay_files = [f for f in os.listdir(OVERLAY_FOLDER) if f.endswith(".mp4")]

if not overlay_files:
    print("No overlay file found!")
    overlay_clip = None
else:
    overlay_path = os.path.join(OVERLAY_FOLDER, overlay_files[0])
    overlay_clip = VideoFileClip(overlay_path)


# ---------------- SAFE FUNCTIONS ----------------

def safe_write(video, frame):

    if frame is None:
        return False

    if not isinstance(frame, np.ndarray):
        return False

    try:

        if frame.shape[0] != height or frame.shape[1] != width:
            frame = cv2.resize(frame, (width, height))

        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)

        video.write(frame)

        return True

    except Exception:
        return False




def validate_images(image_paths):

    valid = []

    for p in image_paths:

        try:

            img = cv2.imread(p)

            if img is None:
                print("Skipping invalid image:", p)
                continue

            valid.append(p)

        except Exception as e:
            print("Error reading image:", p, e)

    if not valid:
        raise RuntimeError("No valid images found")

    return valid


def load_audio_safe(path):

    try:

        clip = AudioFileClip(path)

        if clip.duration <= 0:
            raise RuntimeError("Audio duration invalid")

        return clip

    except Exception as e:
        raise RuntimeError(f"Audio failed to load: {e}")



def get_random_bg_music():

    if not os.path.exists(BG_MUSIC_FOLDER):
        return None

    files = [
        f for f in os.listdir(BG_MUSIC_FOLDER)
        if f.lower().endswith((".mp3", ".wav"))
    ]

    if not files:
        return None

    return os.path.join(BG_MUSIC_FOLDER, random.choice(files))



from moviepy import CompositeVideoClip

def apply_overlay(base_clip, overlay_clip):
    if overlay_clip is None:
        return base_clip

    # Resize + opacity (NEW syntax)
    overlay = (
        overlay_clip
        .resized(base_clip.size)
        .with_opacity(OVERLAY_OPACITY)
    )

    # Match duration
    if overlay.duration < base_clip.duration:
        overlay = overlay.with_effects([Loop(duration=base_clip.duration)])
    else:
        overlay = overlay.subclipped(0, base_clip.duration)

    # Combine clips (this is still correct in v2)
    final = CompositeVideoClip([base_clip, overlay])

    return final


def fix_audio_if_needed(input_path):
    fixed_path = input_path.replace(".wav", "_fixed.wav")

    command = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-ar", "44100",
        "-ac", "2",
        "-vn",  # ✅ ignore video if any
        fixed_path
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    # ❌ if ffmpeg failed → don't use broken file
    if result.returncode != 0:
        print("FFmpeg error:\n", result.stderr)
        return input_path

    # ✅ validate file size
    if not os.path.exists(fixed_path) or os.path.getsize(fixed_path) < 5000:
        print("Fixed audio invalid, using original")
        return input_path

    return fixed_path


def update_status(job_id, message, progress=None):
    if job_id:
        update_data = {"status_message": message}

        if progress is not None:
            update_data["progress"] = progress

        VideoJob.objects.filter(id=job_id).update(**update_data)

        print(f"{message} ({progress if progress else 0}%)")



# ---------------- IMAGE FIT WITH BLUR BACKGROUND ----------------

def load_and_resize(path):

    try:

        img = cv2.imread(path)

        if img is None:
            raise RuntimeError("Image read failed")

        h, w = img.shape[:2]

        background = cv2.resize(img, (width, height))
        background = cv2.GaussianBlur(background, (51, 51), 0)

        scale = min(width / w, height / h)

        new_w = int(w * scale)
        new_h = int(h * scale)

        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

        x_offset = (width - new_w) // 2
        y_offset = (height - new_h) // 2

        background[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

        return background

    except Exception as e:

        print("Skipping bad image:", path)
        print("Reason:", e)

        return None


# ---------------- ANIMATIONS ----------------

def zoom_animation(img):

    frames = []

    zoom_factor = 1.2

    large = cv2.resize(
        img,
        (int(width * zoom_factor), int(height * zoom_factor)),
        interpolation=cv2.INTER_LANCZOS4
    )

    large_h, large_w = large.shape[:2]

    for i in range(frames_per_image):

        progress = i / frames_per_image

        crop_w = int(width + (large_w - width) * progress)
        crop_h = int(height + (large_h - height) * progress)

        x = (large_w - crop_w) // 2
        y = (large_h - crop_h) // 2

        crop = large[y:y+crop_h, x:x+crop_w]

        frame = cv2.resize(crop, (width, height), interpolation=cv2.INTER_LANCZOS4)

        frames.append(frame)

    return frames


def zoom_out(img):

    frames = []

    for i in range(frames_per_image):

        scale = 1.15 - (i / frames_per_image) * 0.15

        resized = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)

        h, w = resized.shape[:2]

        x = (w - width) // 2
        y = (h - height) // 2

        frame = resized[y:y+height, x:x+width]

        frames.append(frame)

    return frames


def pan_left_to_right(img):

    frames = []

    large = cv2.resize(img, (width + 300, height), interpolation=cv2.INTER_LANCZOS4)

    for i in range(frames_per_image):

        x = int((large.shape[1] - width) * (i / frames_per_image))

        frame = large[:, x:x+width]

        frames.append(frame)

    return frames


def pan_right_to_left(img):

    frames = []

    large = cv2.resize(img, (width + 300, height), interpolation=cv2.INTER_LANCZOS4)

    for i in range(frames_per_image):

        x = int((large.shape[1] - width) * (1 - i / frames_per_image))

        frame = large[:, x:x+width]

        frames.append(frame)

    return frames

def cinematic_pan(img):

    frames = []

    large = cv2.resize(img, (width + 400, height))

    for i in range(frames_per_image):

        progress = i / frames_per_image
        x = int((large.shape[1] - width) * progress)

        frame = large[:, x:x+width]

        frames.append(frame)

    return frames

def diagonal_drift(img):

    frames = []

    large = cv2.resize(img, (width + 300, height + 300))

    for i in range(frames_per_image):

        progress = i / frames_per_image

        x = int((large.shape[1] - width) * progress * 0.6)
        y = int((large.shape[0] - height) * progress * 0.6)

        frame = large[y:y+height, x:x+width]

        frames.append(frame)

    return frames

def tilt_motion(img):

    frames = []

    for i in range(frames_per_image):

        progress = i / frames_per_image
        angle = -4 + progress * 8

        M = cv2.getRotationMatrix2D((width//2, height//2), angle, 1)

        frame = cv2.warpAffine(img, M, (width, height))

        frames.append(frame)

    return frames

def cinematic_zoom(img):

    frames = []

    start_scale = 1.0
    end_scale = 1.3

    for i in range(frames_per_image):

        progress = i / frames_per_image
        scale = start_scale + (end_scale - start_scale) * progress

        resized = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)

        h, w = resized.shape[:2]

        x = (w - width) // 2
        y = (h - height) // 2

        frame = resized[y:y+height, x:x+width]

        frames.append(frame)

    return frames




# ---------------- TRANSITIONS ----------------

def fade_transition(img1, img2):

    frames = []

    for i in range(transition_frames):

        alpha = i / transition_frames

        frame = cv2.addWeighted(img1, 1 - alpha, img2, alpha, 0)

        frames.append(frame)

    return frames


def slide_transition(img1, img2):

    frames = []

    for i in range(transition_frames):

        offset = int(width * (i / transition_frames))

        frame = np.zeros_like(img1)

        frame[:, :width-offset] = img1[:, offset:]
        frame[:, width-offset:] = img2[:, :offset]

        frames.append(frame)

    return frames


def blur_transition(img1, img2):

    frames = []

    for i in range(transition_frames):

        alpha = i / transition_frames

        blur1 = cv2.GaussianBlur(img1, (51, 51), 0)
        blur2 = cv2.GaussianBlur(img2, (51, 51), 0)

        frame = cv2.addWeighted(blur1, 1-alpha, blur2, alpha, 0)

        frames.append(frame)

    return frames

def zoom_blur_transition(img1, img2):

    frames = []

    for i in range(transition_frames):

        progress = i / transition_frames

        scale = 1 + progress * 0.4

        resized = cv2.resize(img2, None, fx=scale, fy=scale)

        h, w = resized.shape[:2]

        # safe crop
        x = max(0, (w - width) // 2)
        y = max(0, (h - height) // 2)

        x2 = min(w, x + width)
        y2 = min(h, y + height)

        frame2 = resized[y:y2, x:x2]

        frame2 = cv2.resize(frame2, (width, height))

        frame = cv2.addWeighted(img1, 1-progress, frame2, progress, 0)

        frame = cv2.GaussianBlur(frame, (31,31), 0)

        frames.append(frame)

    return frames

def whip_pan_transition(img1, img2):

    frames = []

    for i in range(transition_frames):

        progress = i / transition_frames
        offset = int(width * progress)

        frame = np.zeros_like(img1)

        frame[:, :width-offset] = img1[:, offset:]
        frame[:, width-offset:] = img2[:, :offset]

        frame = cv2.GaussianBlur(frame, (21,21), 0)

        frames.append(frame)

    return frames

def circle_reveal_transition(img1, img2):

    frames = []

    center = (width//2, height//2)
    max_radius = int(np.sqrt(width**2 + height**2))

    for i in range(transition_frames):

        radius = int(max_radius * (i/transition_frames))

        mask = np.zeros((height,width), dtype=np.uint8)

        cv2.circle(mask, center, radius, 255, -1)

        mask = mask.astype(bool)

        frame = img1.copy()
        frame[mask] = img2[mask]

        frames.append(frame)

    return frames

def flash_transition(img1, img2):

    frames = []

    for i in range(transition_frames):

        progress = i / transition_frames

        flash = np.full_like(img1, 255)

        if progress < 0.5:
            frame = cv2.addWeighted(img1, 1-progress*2, flash, progress*2, 0)
        else:
            frame = cv2.addWeighted(img2, (progress-0.5)*2, flash, 1-(progress-0.5)*2, 0)

        frames.append(frame)

    return frames

def glitch_transition(img1, img2):

    frames = []

    for i in range(transition_frames):

        frame = img1.copy()

        if i % 3 == 0:
            shift = random.randint(-40,40)
            frame = np.roll(frame, shift, axis=1)

        alpha = i / transition_frames

        frame = cv2.addWeighted(frame, 1-alpha, img2, alpha, 0)

        frames.append(frame)

    return frames


# ---------------- AUDIO MERGE (FINAL EXPORT) ----------------

def add_voice_to_video(temp_video, final_output, audio_file):

    audio_file = fix_audio_if_needed(audio_file)
    voice = AudioFileClip(audio_file)

    if voice.duration is None or voice.duration <= 0:
        raise RuntimeError("❌ Audio is empty or corrupted")

    print("Voice duration:", voice.duration)

    voice = voice.subclipped(0, max(0.1, voice.duration))

    video_clip = VideoFileClip(temp_video)

    audio_tracks = [voice]
    # ---------------- BACKGROUND MUSIC ----------------

    bg_music_path = get_random_bg_music()

    if bg_music_path:

        try:

            bg_music = AudioFileClip(bg_music_path).with_volume_scaled(BG_MUSIC_VOLUME)

            # match duration with voice
            bg_music = AudioFileClip(bg_music_path).with_volume_scaled(BG_MUSIC_VOLUME)

            loops = int(voice.duration // bg_music.duration) + 1

            music_layers = []

            for i in range(loops):
                music_layers.append(bg_music.with_start(i * bg_music.duration))

            bg_music = CompositeAudioClip(music_layers).subclipped(0, voice.duration)

            audio_tracks.append(bg_music)

            print("Background music added:", os.path.basename(bg_music_path))

            # audio_tracks.append(bg_music)

            # print("Background music added:", os.path.basename(bg_music_path))

        except Exception as e:

            print("Background music skipped:", e)

    for t in sfx_times:

        if not sfx_files:
            break

        sfx = AudioFileClip(random.choice(sfx_files)).with_start(t)

        audio_tracks.append(sfx)

    audio_tracks = [t for t in audio_tracks if t.duration and t.duration > 0]

    if not audio_tracks:
        raise RuntimeError("❌ No valid audio tracks found")

    final_audio = CompositeAudioClip(audio_tracks)

    final_video = video_clip.with_audio(final_audio)

    # final_video = apply_overlay(final_video, overlay_clip)

    final_video.write_videofile(
        final_output,
    codec="libx264",
    audio_codec="aac",
    fps=30,
    preset="medium",        # 🔥 change this
    threads=4,
    bitrate="2000k"
    )

    video_clip.close()
    voice.close()

    os.remove(temp_video)

    print("Final video created:", final_output)

    for track in audio_tracks:
        try:
            track.close()
        except:
            pass



def create_video(audio_file, keywords=None, media_files=None,job_id=None):

    update_status(job_id, "Preparing images...")
    print("Starting video creation...")
    # 🔥 Decide source of images
    if media_files:
        print("[MODE] Manual upload detected")
        images = media_files
    else:
        print("[MODE] Auto image download")
        from .image_download import generate_images_from_audio
        update_status(job_id, "Downloading images...")
        images = generate_images_from_audio(audio_file, keywords, job_id=job_id)

    # 🔥 AUTO MODE ONLY (no manual selection)
    from .image_download import generate_images_from_audio

    # images = generate_images_from_audio(audio_file, keywords)

    if not images:
        raise RuntimeError("No images generated")

    images = validate_images(images)

    voice_clip = load_audio_safe(audio_file)
    voice_duration = voice_clip.duration

    total_frames_needed = int(voice_duration * fps)

    os.makedirs(export_folder, exist_ok=True)

    final_output = os.path.join(export_folder, f"video_{uuid.uuid4().hex}.mp4")
    temp_video = os.path.join(export_folder, f"temp_{uuid.uuid4().hex}.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))

    frame_count = 0
    img_index = 0
    prev_img = None

    global sfx_times
    sfx_times = []

    while frame_count < total_frames_needed:
        progress = int((frame_count / total_frames_needed) * 100)
        update_status(job_id, "Creating video frames...", progress)

        img_path = images[img_index % len(images)]
        img = load_and_resize(img_path)

        if img is None:
            img_index += 1
            continue

        sfx_times.append(frame_count / fps)

        if prev_img is not None:
            update_status(job_id, "Applying transitions...")
            transition = random.choice([
                fade_transition,
                slide_transition,
                blur_transition,
                whip_pan_transition,
                zoom_blur_transition,
                circle_reveal_transition,
                flash_transition,
                glitch_transition
            ])

            for f in transition(prev_img, img):
                if safe_write(video, f):
                    frame_count += 1
                if frame_count >= total_frames_needed:
                    break

        update_status(job_id, "Animating images...")
        animation = random.choice([
            cinematic_zoom,
            zoom_out,
            pan_left_to_right,
            pan_right_to_left,
            cinematic_pan,
            diagonal_drift,
            tilt_motion
        ])

        for f in animation(img):
            if safe_write(video, f):
                frame_count += 1
            if frame_count >= total_frames_needed:
                break

        prev_img = img
        img_index += 1

    video.release()

    update_status(job_id, "Adding audio...", 90)
    add_voice_to_video(temp_video, final_output, audio_file)

    update_status(job_id, "Exporting video...", 100)
    print("✅ Video created:", final_output)
    update_status(job_id, "Video completed")

    return final_output