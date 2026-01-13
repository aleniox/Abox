import re
import torch
from tqdm import tqdm
import pickle
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
from scipy.signal import savgol_filter
import soundfile as sf


# Hàm chia đoạn văn thành các câu
def split_into_sentences(text):
    # Tách dựa trên dấu . ! ? và loại bỏ chúng
    sentences = re.split(r'[.!?]+\s+', text.strip())
    # Loại bỏ khoảng trắng thừa và các câu rỗng
    return [sentence.strip() for sentence in sentences if sentence.strip()]

def clone_tts(para, speaker_emb, model, processor, vocoder):
    spectrogram_audio = None
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    for text in tqdm(split_into_sentences(para)):
        text = text.replace("\n"," ").strip()
        if len(text) == 0:
            continue
        inputs = processor(text=text.lower(), return_tensors="pt")
        model.to(device)
        # speaker_embeddings.device
        spectrogram = model.generate_speech(inputs["input_ids"].to(model.device), speaker_emb.to(model.device))
        if spectrogram_audio is None:
            spectrogram_audio = spectrogram
        else:
            spectrogram_audio = torch.cat((spectrogram_audio, spectrogram), dim=0)

    # print(spectrogram_audio.shape, spectrogram_audio.device)
    vocoder.to(device)
    print(vocoder.device)
    with torch.no_grad():
        speech = vocoder(spectrogram_audio)
    return speech.to("cpu").numpy()

def init_model(processor_id="dolphinnlp/voice_vi", model_id="dolphinnlp/voice_vi", vocoder_id="vocoder"):
    processor = SpeechT5Processor.from_pretrained(processor_id)
    model = SpeechT5ForTextToSpeech.from_pretrained(model_id)
    vocoder = SpeechT5HifiGan.from_pretrained(vocoder_id)
    return processor, model, vocoder

def run(output_filename, text, window_length=5, polyorder=1, sample_rate=24000):
    with open('data/voice_speaker_vy.pkl', 'rb') as f:
        speaker_embeddings_loaded = pickle.load(f)
    # Sử dụng dữ liệu đã tải
    # print(speaker_embeddings_loaded)
    print("Nội dung text:", text)
    speaker_embeddings = speaker_embeddings_loaded[83].unsqueeze(0)
    
    # Use relative path for Docker compatibility
    model_id = "weights/voice_vi"
    processor, model, vocoder = init_model(processor_id=model_id, model_id=model_id, vocoder_id="microsoft/speecht5_hifigan")

    speech = clone_tts(text, speaker_embeddings, model, processor, vocoder)
    smoothed_audio = savgol_filter(speech, window_length, polyorder)
    sf.write(output_filename, smoothed_audio, sample_rate)
    # sd.play(smoothed_audio, sample_rate)
    # sd.wait()
    return output_filename
