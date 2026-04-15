import os
from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
import os
import uuid
from .videomaker.main import create_video
import threading
from .models import VideoJob

video_jobs = {}

def check_status(request, job_id):
    # job = video_jobs.get(job_id)
    try:
        job = VideoJob.objects.get(id=job_id)
    except VideoJob.DoesNotExist:
        return JsonResponse({"error": "Invalid Job ID"})

    return JsonResponse({
    "status": job.status,
    "video": job.video.url if job.video else None,
    "error": job.error,
    "message": job.status_message,
    "progress": job.progress
})

    if not job:
        return JsonResponse({"error": "Invalid Job ID"})

    return JsonResponse(job)

def process_video(job_id, audio_path, keyword_list, mode, media_paths):
    try:
        # 🔥 Generate video
        if mode == "manual":
            video_path = create_video(audio_path, media_files=media_paths,job_id=job_id)
        else:
            video_path = create_video(audio_path, keywords=keyword_list,job_id=job_id)

        # 🔥 Get job from DB
        job = VideoJob.objects.get(id=job_id)

        # 🔥 Save video path (temporary string)
        job.status = "completed"
        job.video = video_path   # we improve this in next step
        job.save()

    except Exception as e:
        job = VideoJob.objects.get(id=job_id)

        job.status = "error"
        job.error = str(e)
        job.save()

def home(request):
    if request.method == "POST":
        audio_file = request.FILES.get('audio')
        keywords = request.POST.get('keywords')
        mode = request.POST.get("mode")

        # if not audio_file or not keywords:
        #     return HttpResponse("Please provide audio and keywords")
        if not audio_file:
            return JsonResponse({"error": "Audio file required"})

        if mode == "auto" and not keywords:
            return JsonResponse({"error": "Keywords required for auto mode"})

        if mode == "manual":
            files = request.FILES.getlist("media_files")
            if not files:
                return JsonResponse({"error": "Please upload images"})

        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]

        # if len(keyword_list) < 3:
        #     return HttpResponse("Enter at least 3 keywords")
        if mode == "auto" and len(keyword_list) < 3:
            return JsonResponse({"error": "Enter at least 3 keywords"})
        
        media_paths = []

        if mode == "manual":
            files = request.FILES.getlist("media_files")

            if not files:
                return HttpResponse("Please upload images")

            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            upload_folder = os.path.join(BASE_DIR, "videomaker", "uploads")

            os.makedirs(upload_folder, exist_ok=True)

            for f in files:
                file_path = os.path.join(upload_folder, f"{uuid.uuid4()}_{f.name}")

                with open(file_path, 'wb+') as dest:
                    for chunk in f.chunks():
                        dest.write(chunk)

                media_paths.append(file_path)

        # 🔥 SAVE AUDIO FILE
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        # Go to videomaker/voice_over
        voice_folder = os.path.join(BASE_DIR, "videomaker", "voice_over")

        # Create folder if not exists
        os.makedirs(voice_folder, exist_ok=True)

        # Create unique filename (VERY IMPORTANT)
        filename = f"{uuid.uuid4()}_{audio_file.name}"

        # Full path
        audio_path = os.path.join(voice_folder, filename)

        # Save file
        with open(audio_path, 'wb+') as f:
            for chunk in audio_file.chunks():
                f.write(chunk)

        with open(audio_path, 'wb+') as f:
            for chunk in audio_file.chunks():
                f.write(chunk)


        # job_id = str(uuid.uuid4())

        # video_jobs[job_id] = {
        #     "status": "processing",
        #     "video": "path"
        # }

        job = VideoJob.objects.create(
            status="processing"
        )

        job_id = str(job.id)

        thread = threading.Thread(
            target=process_video,
            args=(job_id, audio_path, keyword_list, mode, media_paths)
        )
        thread.start()

        return JsonResponse({
            "job_id": job_id,
            "status": "processing"
        })

    return render(request, "index.html")