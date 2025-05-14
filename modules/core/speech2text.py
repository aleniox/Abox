import os
from pathlib import Path
import speech_recognition as sr
from pydub import AudioSegment
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def convert_audio_to_wav(input_path: str, output_dir: str) -> Optional[str]:
    """Chuyển đổi audio sang định dạng WAV 16kHz (yêu cầu của SpeechRecognition)"""
    try:
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(output_dir, exist_ok=True)
        
        # Đường dẫn output
        output_path = os.path.join(output_dir, f"converted_{Path(input_path).stem}.wav")
        
        # Chuyển đổi bằng pydub
        audio = AudioSegment.from_file(input_path)
        audio = audio.set_frame_rate(16000).set_channels(1)
        audio.export(output_path, format="wav")
        
        return output_path
    except Exception as e:
        logger.error(f"Audio conversion failed: {e}")
        return None

def transcribe_audio(audio_path: str, language: str = "vi-VN") -> Optional[str]:
    """Chuyển đổi audio thành văn bản bằng Google Speech Recognition"""
    recognizer = sr.Recognizer()
    
    try:
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
            
            # Sử dụng Google Web API (miễn phí nhưng cần Internet)
            text = recognizer.recognize_google(audio_data, language=language)
            return text
    except sr.UnknownValueError:
        logger.warning("Google Speech Recognition could not understand audio")
    except sr.RequestError as e:
        logger.error(f"Could not request results from Google: {e}")
    except Exception as e:
        logger.error(f"Transcription error: {e}")
    
    return None

def transcribe_audio_with_whisperx(audio_path: str, language: str = "vi") -> Optional[str]:
    """Chuyển đổi audio thành văn bản bằng Faster Whisper"""
    import whisperx
    model = whisperx.load_model("weights/speech2text", "cuda", compute_type="int8")

    try:
        audio = whisperx.load_audio(audio_path)
        segments = model.transcribe(audio, batch_size=8, language=language)
        text = " ".join([segment["text"] for segment in segments["segments"]])
        return text
    except Exception as e:
        logger.error(f"Faster Whisper transcription error: {e}")
    
    return None

def process_voice_message(audio_paths: str, temp_dir: str = "temp_audio") -> Optional[str]:
    """Xử lý tin nhắn thoại: chuyển đổi -> nhận dạng"""
    # Bước 1: Chuyển đổi sang WAV
    output_text = ""
    for audio_path in audio_paths:
        wav_path = convert_audio_to_wav(audio_path, temp_dir)
        if not wav_path:
            return None
        
        # Bước 2: Chuyển thành text
        text = transcribe_audio_with_whisperx(wav_path)
        # text = transcribe_audio(wav_path, language="vi-VN")
        output_text += text + "\n" if text else ""
        # Xóa file tạm (tuỳ chọn)
        os.remove(wav_path)
    
    return output_text

