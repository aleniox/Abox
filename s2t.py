import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import scipy.signal as signal
import queue
import threading
import time
import os
import tempfile
from pathlib import Path
from pyannote.audio import Model
from pyannote.audio.pipelines import VoiceActivityDetection
from pydub import AudioSegment
import modules.core.speech2text as speech2text
from dotenv import load_dotenv

load_dotenv()

# ⚙️ Config
FS = 16000
CHUNK_DURATION = 3
CHUNK_SAMPLES = int(FS * CHUNK_DURATION)
BUFFER_CYCLES = 6  # 6 cycles * 3s = 18s buffer

# Global state
audio_queue = queue.Queue()
stop_flag = False
all_recordings = []

# Initialize models
model = Model.from_pretrained(
    "pyannote/segmentation-3.0",
    use_auth_token=os.getenv("HUGGINGFACE_TOKEN")
)
pipeline = VoiceActivityDetection(segmentation=model)
pipeline.instantiate({
    "min_duration_on": 0.0,
    "min_duration_off": 0.0
})
asr = speech2text.model_init_speech2text(adapter_model="TEST/checkpoint-116160")


# Audio processing utilities
def get_bandpass_filter(lowcut=250.0, highcut=3400.0, fs=FS, order=4):
    """Create bandpass filter coefficients."""
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    return signal.butter(order, [low, high], btype='band')


FILTER_B, FILTER_A = get_bandpass_filter()


def clean_audio(chunk):
    """Apply bandpass filter and normalize audio."""
    chunk = signal.filtfilt(FILTER_B, FILTER_A, chunk)
    rms = np.sqrt(np.mean(chunk**2))
    if rms > 0:
        gain = min(3000 / rms, 5.0)
        chunk = chunk * gain
    return np.clip(chunk, -32768, 32767).astype(np.int16)


def numpy_to_audio_segment(np_array, sample_rate=FS):
    """Convert numpy array to AudioSegment."""
    return AudioSegment(
        np_array.tobytes(),
        frame_rate=sample_rate,
        sample_width=np_array.dtype.itemsize,
        channels=1
    )


def detect_speech_segments(audio_segment):
    """Detect speech segments using VAD pipeline."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_segment.export(tmp.name, format="wav")
        segments = list(pipeline(tmp.name).get_timeline().support())
        Path(tmp.name).unlink(missing_ok=True)
    return segments


def transcribe_audio(audio_segment):
    """Transcribe audio segment using ASR model."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_segment.export(tmp.name, format="wav")
        result = speech2text.infer_s2t(tmp.name, asr)
        Path(tmp.name).unlink(missing_ok=True)
    return result

def record_loop():
    """Continuously record audio and push to queue."""
    with sd.InputStream(samplerate=FS, channels=1, dtype='int16') as stream:
        print("🎧 Bắt đầu ghi âm liên tục... (nhấn Ctrl+C để dừng)")
        try:
            while not stop_flag:
                data, _ = stream.read(CHUNK_SAMPLES)
                audio_queue.put(data[:, 0].copy())
                all_recordings.append(data[:, 0].copy())
        except Exception as e:
            print(f"❌ Lỗi ghi âm: {e}")


def sender_loop():
    """Process audio chunks and transcribe."""
    count = 0
    buffer = AudioSegment.empty()
    
    while not stop_flag:
        if audio_queue.empty():
            time.sleep(0.1)
            continue

        try:
            # Process chunk
            raw_chunk = audio_queue.get()
            cleaned_chunk = clean_audio(raw_chunk)
            audio_segment = numpy_to_audio_segment(cleaned_chunk)
            
            # Transcribe chunk
            print(f"🗣️ Xử lý chunk {count + 1} ({CHUNK_DURATION}s)")
            result = transcribe_audio(audio_segment)
            print(f"📝 Chunk {count + 1}:", result)
            
            # Accumulate buffer
            buffer += audio_segment
            count += 1

            # Process full buffer
            if count >= BUFFER_CYCLES:
                print(f"\n>>> Xử lý buffer đầy ({BUFFER_CYCLES * CHUNK_DURATION}s) <<<")
                
                speech_segments = detect_speech_segments(buffer)
                print(f"Phát hiện {len(speech_segments)} đoạn giọng nói")
                
                if speech_segments:
                    start_ms = int(speech_segments[0].start * 1000)
                    end_ms = int(speech_segments[-1].end * 1000)
                    segment = buffer[start_ms:end_ms]
                    print(f"🗣️ Giọng nói: {speech_segments[0].start:.2f}s - {speech_segments[-1].end:.2f}s")
                else:
                    segment = AudioSegment.silent(duration=100)
                    print("😶 Không phát hiện giọng nói")

                result = transcribe_audio(segment)
                print("📝 Buffer Re-Transcribed:", result)
                
                # Reset
                buffer = AudioSegment.empty()
                count = 0
                print("<<< Reset buffer >>>\n")
                
        except Exception as e:
            print(f"❌ Lỗi xử lý: {e}")


def main():
    """Main entry point."""
    global stop_flag
    
    record_thread = threading.Thread(target=record_loop, daemon=True)
    send_thread = threading.Thread(target=sender_loop, daemon=True)

    record_thread.start()
    send_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Dừng toàn bộ...")
        stop_flag = True
        record_thread.join(timeout=2)
        send_thread.join(timeout=2)
        
        # Save final recording
        if all_recordings:
            final_audio = np.concatenate(all_recordings).astype(np.int16)
            wav.write("final_output.wav", FS, final_audio)
            print("💾 Đã lưu ghi âm: final_output.wav")
        else:
            print("⚠️ Không có dữ liệu để lưu")


if __name__ == "__main__":
    main()