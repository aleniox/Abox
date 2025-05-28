import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import scipy.signal as signal
import requests
import queue
import threading
import time, os
from pyannote.audio import Model
from pyannote.audio.pipelines import VoiceActivityDetection
from pydub import AudioSegment
from dotenv import load_dotenv
load_dotenv()

# ⚙️ Config
url = os.getenv("URL")  # Dùng HTTP
fs = 16000
chunk_duration = 3      # Thời lượng mỗi đoạn
max_chunk_duration = 10
overlap_duration = 0.0    # Phần chồng lặp giữa các đoạn
chunk_samples = int(fs * chunk_duration)
overlap_samples = int(fs * overlap_duration)
firts_audio_chunk = []

audio_queue = queue.Queue()
stop_flag = False

model = Model.from_pretrained(
  "pyannote/segmentation-3.0", 
  use_auth_token=os.getenv("HUGGINGFACE_TOKEN"))
pipeline = VoiceActivityDetection(segmentation=model)
HYPER_PARAMETERS = {
  # remove speech regions shorter than that many seconds.
  "min_duration_on": 0.0,
  # fill non-speech regions shorter than that many seconds.
  "min_duration_off": 0.0
}
pipeline.instantiate(HYPER_PARAMETERS)


def butter_bandpass(lowcut=250.0, highcut=3400.0, fs=16000, order=4):
    nyq = 0.5 * fs  # Nyquist freq
    low = lowcut / nyq
    high = highcut / nyq
    b, a = signal.butter(order, [low, high], btype='band')
    return b, a

b, a = butter_bandpass()
all_recordings = []
# 🎙 Ghi âm liên tục và đưa vào queue
def record_loop():
    buffer = np.zeros(chunk_samples, dtype='int16')
    stream = sd.InputStream(samplerate=fs, channels=1, dtype='int16')
    stream.start()
    print("🎧 Bắt đầu ghi âm liên tục... (nhấn Ctrl+C để dừng)")

    try:
        while not stop_flag:
            # Đọc dữ liệu
            data, _ = stream.read(chunk_samples - overlap_samples)
            buffer = np.roll(buffer, -len(data))
            buffer[-len(data):] = data[:, 0]
            # Đưa đoạn ghi vào queue
            audio_queue.put(buffer.copy())
            all_recordings.append(data[:, 0].copy())
    except KeyboardInterrupt:
        print("🛑 Dừng ghi âm")
    finally:
        stream.stop()
        stream.close()

def clean_audio(chunk):
    chunk = signal.filtfilt(b, a, chunk)
    rms = np.sqrt(np.mean(chunk**2))
    target_rms = 3000  # Bạn có thể điều chỉnh từ 2000–6000 tùy chất lượng mic
    if rms > 0:
        gain = min(target_rms / rms, 5.0)
        chunk = chunk * gain

    # Giới hạn để không vượt quá int16
    chunk = np.clip(chunk, -32768, 32767).astype(np.int16)
    return chunk
# 🚀 Gửi từng đoạn trong queue đến API

import scipy.signal

def apply_wiener(audio_np):
    return scipy.signal.wiener(audio_np)

def merge_segments_except_last(segments, fs, audio_chunk):
    # Bỏ đoạn cuối
    if len(segments) <= 1:
        return None  # Không có gì để ghép

    merged_audio = []
    for seg in segments[:-1]:
        start_sample = max(0, int((seg['start'] - 0.2) * fs))
        end_sample = min(len(audio_chunk), int((seg['end'] + 0.2) * fs))
        merged_audio.append(audio_chunk[start_sample:end_sample])

    # Ghép tất cả lại
    final_merged = np.concatenate(merged_audio).astype(np.int16)
    return final_merged

# def sender_loop():
#     count = 1
#     audio_concat = AudioSegment.empty()
    
#     chunk_30s = []
#     while not stop_flag:
#         if not audio_queue.empty():
#             chunk = audio_queue.get()
#             chunk = clean_audio(chunk)
#             temp_audio = "temp_chunk.wav"
            
#             with open(temp_audio, "wb") as f:
#                 wav.write(f, fs, chunk)
#             temp_audio, audio_concat = split_and_concat(temp_audio, audio_concat)

#             files = {'file': open(temp_audio, "rb")}
#             try:
#                 response = requests.post(url, files=files)
#                 if response.ok:
#                     print("📝 Transcribed:", response.json()["transcription"])
#                 else:
#                     print(f"⚠️ API Error: {response.status_code}")
#             except Exception as e:
#                 print(f"❌ Gửi lỗi: {e}")
#             count+=1
#         else:
#             time.sleep(0.1)
import os
def numpy_to_audio_segment(np_array, sample_rate, sample_width_bytes=2, channels=1):
    """Chuyển đổi numpy array (raw audio) sang pydub.AudioSegment."""
    # pydub mong đợi dữ liệu byte
    # Đảm bảo numpy array có kiểu dữ liệu phù hợp (e.g., int16 cho sample_width_bytes=2)
    return AudioSegment(
        np_array.tobytes(),
        frame_rate=sample_rate,
        sample_width=sample_width_bytes,
        channels=channels
    )

def sender_loop():
    count = 0
    buffer_30s = AudioSegment.empty()
    segment_last = AudioSegment.empty()
    while not stop_flag:
        if audio_queue.empty():
            time.sleep(0.1)
            continue

        # Nhận và xử lý đoạn âm thanh 5s
        raw_chunk = audio_queue.get()
        cleaned_chunk_np = clean_audio(raw_chunk)
        audio_seg_5s = numpy_to_audio_segment(cleaned_chunk_np, fs,
                                              sample_width_bytes=cleaned_chunk_np.dtype.itemsize,
                                              channels=1)
        # Phát hiện giọng nói
        temp_5s = "temp_5s.wav"
        audio_seg_5s.export(temp_5s, format="wav")
        # speech_segments = list(pipeline(temp_5s).get_timeline().support())

        # if speech_segments:
        # seg = speech_segments[0]
        segment_to_send = audio_seg_5s[0 * 1000: 3 * 1000]
        print(f"🗣️ Giọng nói trong 5s: {0}s - {3}s")
        # else:
        #     segment_to_send = AudioSegment.silent(duration=100)
        #     print("😶 Không phát hiện giọng nói trong 5s.")

        # Gửi đoạn 5s đến API
        path_5s = "processed_5s.wav"
        segment_to_send.export(path_5s, format="wav")
        try:
            with open(path_5s, "rb") as f:
                response = requests.post(url, files={'file': f})
                if response.ok:
                    print(f"📝 5s Transcribed ({count + 1}):", response.json()["transcription"])
                else:
                    print(f"⚠️ Lỗi API 5s: {response.status_code}")
        except Exception as e:
            print(f"❌ Gửi lỗi 5s: {e}")

        # Tích lũy vào buffer 30s
        buffer_30s += audio_seg_5s
        count += 1

        # Nếu đủ 30s => xử lý lại toàn bộ
        if count == 6:
            print("\n>>> Xử lý lại đoạn 30s <<<")
            temp_30s = "temp_30s.wav"
            buffer_30s.export(temp_30s, format="wav")
            speech_segments_30s = list(pipeline(temp_30s).get_timeline().support())
            print(f"Đã phát hiện {len(speech_segments_30s)} đoạn giọng nói trong 30s.")
            if speech_segments_30s:
                seg_start = speech_segments_30s[0]
                seg_end = speech_segments_30s[-1]
                
                segment_30s = buffer_30s[seg_start.start * 1000: seg_end.end * 1000]
                # segment_last = buffer_30s[seg_end.start * 1000: seg_end.end * 1000]
                print(f"🗣️ Giọng nói trong 30s: {seg_start.start:.2f}s - {seg_end.end:.2f}s")
            else:
                segment_30s = AudioSegment.silent(duration=100)
                print("😶 Không phát hiện giọng nói trong 30s.")

            path_30s = "processed_30s.wav"
            segment_30s.export(path_30s, format="wav")
            try:
                with open(path_30s, "rb") as f:
                    response = requests.post(url, files={'file': f})
                    if response.ok:
                        print("📝 30s Re-Transcribed:", response.json()["transcription"])
                    else:
                        print(f"⚠️ Lỗi API 30s: {response.status_code}")
            except Exception as e:
                print(f"❌ Gửi lỗi 30s: {e}")

            # Reset cho chu kỳ tiếp theo
            buffer_30s = AudioSegment.empty()
            # buffer_30s += segment_last
            count = 0
            # os.remove(temp_30s)
            # os.remove(path_30s)
            print("<<< Reset buffer 30s >>>\n")

        # Xoá file tạm 5s
        # os.remove(temp_5s)
        # os.remove(path_5s)


# def split_and_concat(audio_split, audio_concat):
#     output = pipeline(audio_split)
#     # Extract the timeline of detected speech segments
#     speech_segments = list(output.get_timeline().support())
#     cut_last_audio = AudioSegment.empty()
#     # Check if there are speech segments detected
#     if len(speech_segments) > 0:
#         # 1. Combine the first few segments into one "first" segment
#         first_segment_start = speech_segments[0].start
#         first_segment_end = speech_segments[0].end

#         # 2. Get the last speech segment
#         last_segment = speech_segments[-1]
#         first_segment_end = last_segment.start
#         print(f"First segment: {first_segment_start} - {first_segment_end}")
#         print(f"Last segment: {last_segment.start} - {last_segment.end}")

#         # Load the audio file using pydub
#         audio = AudioSegment.from_wav(audio_split)
        
#         # Convert start and end times to milliseconds for both segments
#         start_ms_first = first_segment_start * 1000
#         end_ms_first = first_segment_end * 1000
#         start_ms_last = last_segment.start * 1000
#         end_ms_last = last_segment.end * 1000

#         # 3. Cut the audio based on the segments
#         cut_first_audio = audio_concat + audio[start_ms_first:end_ms_first]
#         cut_last_audio = audio[start_ms_last:end_ms_last]

#         # Export the cut audio to new files
#         cut_first_audio.export(audio_split, format="wav")
#     return audio_split, cut_last_audio

# ▶️ Khởi động 2 thread song song
record_thread = threading.Thread(target=record_loop)
send_thread = threading.Thread(target=sender_loop)

record_thread.start()
send_thread.start()

# 🕐 Đợi bao lâu tuỳ bạn
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("🛑 Dừng toàn bộ...")
    stop_flag = True
    record_thread.join()
    send_thread.join()
if all_recordings:
    final_audio = np.concatenate(all_recordings).astype(np.int16)
    wav.write("final_output.wav", fs, final_audio)
    print("💾 Đã lưu toàn bộ ghi âm vào file: final_output.wav")
else:
    print("⚠️ Không có dữ liệu để lưu.")