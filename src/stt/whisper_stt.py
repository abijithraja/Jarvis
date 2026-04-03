from faster_whisper import WhisperModel
from src.audio.recorder import record_audio
import os

model = None


def get_model():
    global model

    if model is None:
        model = WhisperModel("base", device="cpu", compute_type="int8")

    return model


def transcribe_audio():
    audio_path = record_audio()

    if not audio_path:
        return ""

    try:
        segments, _ = get_model().transcribe(
            audio_path,
            condition_on_previous_text=False,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
    except Exception as err:
        print(f"❌ Transcription error: {err}")
        return ""
    finally:
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except OSError:
            pass

    text = ""
    for segment in segments:
        text += segment.text

    return text.strip()