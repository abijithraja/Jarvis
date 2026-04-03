from faster_whisper import WhisperModel
from src.audio.vad_recorder import record_speech

model = WhisperModel("base", device="cpu", compute_type="float32")


def transcribe_audio():
    audio_path = record_speech()

    if not audio_path:
        return None

    segments, _ = model.transcribe(
        audio_path,
        language="en",
        beam_size=1,
        condition_on_previous_text=False,
    )

    text = ""
    for segment in segments:
        text += segment.text

    return text.strip()