import sounddevice as sd
import numpy as np
import queue
import whisperx
import scipy.io.wavfile as wavfile
import os

# Load model WhisperX
model = whisperx.load_model("weights/speech2text", device="cpu", compute_type="int8")

samplerate = 16000
q = queue.Queue()
all_audio = []
all_text = []

# Thời lượng mỗi đoạn phân tích (giây)
chunk_duration = 5
chunk_samples = samplerate * chunk_duration
buffer = []

def callback(indata, frames, time_, status):
    if status:
        print("⚠️", status)
    q.put(indata.copy())

def record_and_transcribe():
    with sd.InputStream(samplerate=samplerate, channels=1, callback=callback):
        print("🎤 Đang nghe... Nói đi! (Nhấn Ctrl+C để kết thúc và lưu file)")

        try:
            while True:
                audio = q.get()
                buffer.append(audio)
                all_audio.append(audio)

                # Nếu đã đủ 5 giây âm thanh thì xử lý
                total_samples = sum(len(chunk) for chunk in buffer)
                if total_samples >= chunk_samples:
                    print("🔍 Đang xử lý 5 giây âm thanh...")

                    audio_chunk = np.concatenate(buffer)[:chunk_samples]
                    buffer.clear()

                    # Ghi file tạm để WhisperX xử lý
                    temp_path = "temp_segment.wav"
                    wavfile.write(temp_path, samplerate, audio_chunk.astype(np.float32))

                    # Transcribe bằng WhisperX
                    result = model.transcribe(temp_path, language="vi")
                    text = result

                    if text:
                        print("📝 Bạn nói:", text)
                        all_text.append(text)
                    else:
                        print("🤔 Không nghe rõ...")

                    os.remove(temp_path)

        except KeyboardInterrupt:
            print("\n🛑 Kết thúc ghi âm. Đang lưu file...")

            # Gộp toàn bộ âm thanh và lưu
            full_audio = np.concatenate(all_audio, axis=0)
            wavfile.write("output_recording.wav", samplerate, full_audio.astype(np.float32))
            print("✅ Đã lưu âm thanh: output_recording.wav")

            # Lưu văn bản
            with open("output_transcript.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(all_text))
            print("✅ Đã lưu nội dung nói: output_transcript.txt")

# Chạy chương trình
record_and_transcribe()
