from faster_whisper import WhisperModel

model = WhisperModel("base")


def transcribe_audio():
    segments, _ = model.transcribe("audio.wav")

    text = ""
    for segment in segments:
        text += segment.text

    return text.strip()