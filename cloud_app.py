# cloud_app.py - نسخة خفيفة للبيئة المجانية على Streamlit

import streamlit as st
import yt_dlp
import os
import tempfile
import time
import whisper
from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip
from google import genai

# ==================== إعدادات ====================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # ضع المفتاح في Secrets
CAPTION_COLOR = 'yellow'
CAPTION_FONT = 'Arial'
CAPTION_SIZE = 50
MAX_CLIPS = 3  # الحد الأقصى لعدد المقاطع

# ==================== دوال مساعدة ====================

def log_message(message, status_placeholder=None):
    if status_placeholder:
        status_placeholder.info(message, icon="⏳")
        time.sleep(0.3)

def download_video(url, status_placeholder=None):
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, 'temp_original_video.mp4')
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        'outtmpl': output_path,
        'quiet': True,
        'cachedir': False
    }
    log_message("📥 تحميل الفيديو...", status_placeholder)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        log_message("✅ تم تحميل الفيديو.", status_placeholder)
        return output_path
    except Exception as e:
        st.error(f"❌ خطأ في تحميل الفيديو: {e}")
        return None

def transcribe_video(video_path, status_placeholder=None):
    log_message("🎤 تحويل الصوت إلى نص (Whisper tiny)...", status_placeholder)
    try:
        model = whisper.load_model("tiny")  # نسخة خفيفة
        result = model.transcribe(video_path, verbose=False)
        log_message("✅ انتهى التحويل إلى نص.", status_placeholder)
        return {
            'text': result["text"],
            'segments': result.get("segments", [])
        }
    except Exception as e:
        st.error(f"❌ خطأ في الترجمة الصوتية: {e}")
        return None

def analyze_script_for_clips(transcript, status_placeholder=None):
    log_message("✂️ تحديد مقاطع القص...", status_placeholder)
    segments = transcript.get('segments', [])
    clip_times = []
    for i, seg in enumerate(segments):
        if i >= MAX_CLIPS:
            break
        clip_times.append((seg['start'], seg['end']))
    log_message(f"✅ تم تحديد {len(clip_times)} مقاطع.", status_placeholder)
    return clip_times

def call_gemini_for_analysis(text, status_placeholder=None):
    log_message("🤖 طلب تحليل من Gemini API...", status_placeholder)
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=text
        )
        log_message("✅ استجابة Gemini تم استلامها.", status_placeholder)
        return []  # نترك النتيجة فارغة للنسخة الخفيفة
    except Exception as e:
        st.warning(f"⚠️ خطأ من Gemini API: {e}")
        return []

def add_caption_to_clip(input_file, start_time, end_time, segments, status_placeholder=None, clip_index=1):
    temp_dir = tempfile.gettempdir()
    output_file = os.path.join(temp_dir, f"clip_{clip_index}_captioned.mp4")
    log_message(f"✂️ معالجة المقطع {clip_index}...", status_placeholder)
    try:
        full_clip = VideoFileClip(input_file)
        clipped_clip = full_clip.subclip(start_time, end_time)
        captions_text = " ".join([seg['text'] for seg in segments if seg['start'] >= start_time and seg['end'] <= end_time])
        caption_clip = TextClip(
            captions_text if captions_text else "",
            fontsize=CAPTION_SIZE,
            color=CAPTION_COLOR,
            font=CAPTION_FONT
        ).set_position(('center', 'bottom')).set_duration(clipped_clip.duration)
        final_clip = CompositeVideoClip([clipped_clip, caption_clip])
        final_clip.write_videofile(
            output_file,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile=os.path.join(temp_dir, 'temp-audio.m4a'),
            remove_temp=True,
            fps=clipped_clip.fps,
            verbose=False,
            logger=None
        )
        final_clip.close()
        clipped_clip.close()
        full_clip.close()
        log_message(f"✅ انتهى المقطع {clip_index}.", status_placeholder)
        return output_file
    except Exception as e:
        st.error(f"❌ خطأ في المونتاج: {e}")
        return None

# ==================== الدالة الرئيسية ====================

def run_clipper_tool_streamlit(video_url, status_placeholder):
    original_video_path = download_video(video_url, status_placeholder)
    if not original_video_path:
        return

    transcript = transcribe_video(original_video_path, status_placeholder)
    if not transcript:
        return

    gemini_segments = call_gemini_for_analysis(transcript['text'], status_placeholder)
    if gemini_segments:
        clip_timestamps = gemini_segments
    else:
        clip_timestamps = analyze_script_for_clips(transcript, status_placeholder)

    for i, (start, end) in enumerate(clip_timestamps):
        clipped_path = add_caption_to_clip(original_video_path, start, end, transcript['segments'], status_placeholder, clip_index=i+1)
        if clipped_path:
            output_file_name = f"clip_{i+1}_captioned.mp4"
            with open(clipped_path, "rb") as file:
                st.download_button(
                    label=f"تحميل {output_file_name}",
                    data=file,
                    file_name=output_file_name,
                    mime='video/mp4',
                    key=f'download_{i}'
                )

    try:
        os.remove(original_video_path)
        status_placeholder.success("✅ حذف الملف الأصلي المؤقت.")
    except:
        status_placeholder.warning("⚠️ لم يتم حذف الملف المؤقت.")

    status_placeholder.success("🎉 انتهت العملية بنجاح!")

# ==================== واجهة Streamlit ====================

st.title("✂️ Gemini Clipper Lite")

video_url = st.text_input("ادخل رابط فيديو من YouTube:")

status_placeholder = st.empty()

if st.button("ابدأ العملية"):
    if video_url:
        run_clipper_tool_streamlit(video_url, status_placeholder)
    else:
        st.warning("❗ من فضلك أدخل رابط فيديو.")
