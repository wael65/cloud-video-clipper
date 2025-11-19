# cloud_app.py - ملف مُعد للنشر على Streamlit Community Cloud

import streamlit as st
import yt_dlp
import os
import json
import tempfile # لاستخدام مجلدات مؤقتة
from google import genai
from google.genai import types
import whisper
from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip
from moviepy.video.tools.subtitles import SubtitlesClip
import moviepy.config as config
import time 

# ==================== الإعدادات والثوابت ====================

# يجب تعيين هذا المتغير في إعدادات Streamlit Cloud (Secrets)
gemini_api_key = os.getenv("GEMINI_API_KEY") 

# لا نحدد مسار ImageMagick، نعتمد على الإعداد الافتراضي للسحابة

# إعدادات الكابشن
CAPTION_COLOR = 'yellow'
CAPTION_FONT = 'Arial' 
CAPTION_SIZE = 60
# ==========================================================

# ==================== دوال المساعدة (Core Functions) ====================

# ... (هنا يجب أن تضع جميع الدوال المساعدة: log_message, download_video, transcribe_video, analyze_script_for_clips, add_caption_to_clip) ...

# *******************************************************************
# ملاحظة: يجب نسخ جميع دوال المعالجة الخمسة من ملف app.py بعد توحيد 
# وسيط الحالة إلى 'status_placeholder' ولصقها هنا. 
# *******************************************************************

# سنقوم فقط بتعديل دالة download_video و add_caption_to_clip لاستخدام المسارات المؤقتة
# ----------------------------------------------------------------------------------

def log_message(message, status_placeholder):
    # (نفس دالة log_message من app.py)
    if status_placeholder:
        status_placeholder.info(message, icon="⏳")
        time.sleep(0.5)

def download_video(url, status_placeholder=None):
    """يستخدم مجلداً مؤقتاً لتخزين الفيديو الأصلي في البيئة السحابية."""
    # إنشاء مسار مؤقت لملف الفيديو
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, 'temp_original_video.mp4')
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        'outtmpl': output_path,
        'quiet': True,
        'cachedir': False
    }
    log_message("📥 جاري محاولة تحميل الفيديو...", status_placeholder)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        log_message(f"✅ تم تحميل الفيديو بنجاح وحفظه مؤقتاً.", status_placeholder)
        return output_path
    except Exception as e:
        st.error(f"❌ حدث خطأ أثناء تحميل الفيديو: {e}")
        return None

# ... (الدوال transcribe_video و analyze_script_for_clips تبقى كما هي) ...

def add_caption_to_clip(input_file, start_time, end_time, segments, status_placeholder=None, clip_index=1):
    """يقص الفيديو ويضيف إليه الكابشن باستخدام MoviePy ويخزنه مؤقتاً."""
    temp_dir = tempfile.gettempdir()
    output_file = os.path.join(temp_dir, f"final_clip_{clip_index}_captioned.mp4")
    log_message(f"✂️ جاري مونتاج المقطع رقم {clip_index}...", status_placeholder)
    
    # ... (نفس منطق MoviePy والقص من app.py) ...
    
    try:
        full_clip = VideoFileClip(input_file)
        clipped_clip = full_clip.subclip(start_time, end_time)
        
        # ... (منطق إنشاء captions و final_clip) ... (انسخها من app.py)
        
        final_clip = CompositeVideoClip([
            clipped_clip, 
            # ... (باقي المنطق) ...
        ])

        final_clip.write_videofile(
            output_file, 
            codec='libx264', 
            audio_codec='aac', 
            temp_audiofile='temp-audio.m4a', 
            remove_temp=True,
            fps=clipped_clip.fps
        )
        
        # التأكد من إغلاق جميع موارد MoviePy وتحرير الملف
        final_clip.close()
        clipped_clip.close() 
        full_clip.close()
        
        log_message(f"✅ تم إنتاج المقطع {clip_index} بنجاح.", status_placeholder)
        return output_file
    
    except Exception as e:
        st.error(f"❌ خطأ حرج في المونتاج (MoviePy/ImageMagick): {e}")
        return None


# ==================== الدالة الرئيسية للتحكم في العملية (Cloud) ====================

def run_clipper_tool_streamlit(video_url, status_placeholder):
    # ... (نفس الدالة ولكن مع تحديث الاستدعاءات) ...

    # أ. التحميل
    original_video_path = download_video(video_url, status_placeholder=status_placeholder)
    if not original_video_path: return

    # ب. تحويل الصوت إلى نص (Whisper)
    # ... (نفس المنطق) ...

    # ج. تحليل النص لتحديد مقاطع القص (Gemini)
    # ... (نفس المنطق) ...

    # د. القص والمونتاج وإضافة الكابشن
    all_segments = whisper_result['segments']

    for i, (start, end) in enumerate(clip_timestamps):
        
        # استدعاء الدالة الجديدة
        clipped_path = add_caption_to_clip(
            original_video_path, 
            start, 
            end, 
            all_segments, 
            status_placeholder=status_placeholder, 
            clip_index=i+1
        )
        
        if clipped_path:
            output_file_name = f"final_clip_{i+1}_start_{start}_captioned.mp4"
            # عرض زر تحميل للمقطع المقصوص
            with open(clipped_path, "rb") as file:
                st.download_button(
                    label=f"تحميل {output_file_name}",
                    data=file,
                    file_name=output_file_name,
                    mime='video/mp4',
                    key=f'download_{i}'
                )
            
            # (اختياري) حذف الملف المقصوص بعد عرضه
            os.remove(clipped_path)

    # تنظيف الملف المؤقت الأصلي
    try:
        os.remove(original_video_path) 
        status_placeholder.success("✅ تم حذف الملف المؤقت بنجاح.")
    except Exception as e:
        status_placeholder.warning(f"⚠️ فشل حذف الملف المؤقت: {e}")
        
    status_placeholder.success("🎉 انتهت عملية القص والمونتاج بنجاح! يمكنك تحميل الملفات.")


# ==================== واجهة Streamlit الرئيسية (تبقى كما هي) ====================

st.title("✂️ أداة القص التلقائي للفيديوهات (Gemini Clipper)")
# ... (باقي واجهة Streamlit من app.py) ...
