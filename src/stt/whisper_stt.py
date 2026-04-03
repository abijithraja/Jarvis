import os
from faster_whisper import WhisperModel

# Load once at module level - not on every call
model = WhisperModel("base", device="cpu", compute_type="float32")


def transcribe_audio():
    """
    Records speech via VAD, transcribes with Whisper.
    Returns transcribed string or None.
    """
    from src.audio.vad_recorder import record_speech

    audio_path = record_speech()

    if not audio_path:
        return None

    try:
        segments, _ = model.transcribe(
            audio_path,
            language="en",
            beam_size=1,
            condition_on_previous_text=False,
        )

        text = "".join(segment.text for segment in segments).strip()
        return text if text else None

    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return None

    finally:
        # Always clean up the temp wav file
        try:
            os.remove(audio_path)
        except Exception:
            pass
