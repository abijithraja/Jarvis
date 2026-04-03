import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import tempfile

SAMPLE_RATE = 16000
DURATION = 7


def record_audio(filename=None):
    try:
        if filename is None:
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            filename = temp_file.name
            temp_file.close()

        print("🎤 Listening...")

        recording = sd.rec(
            int(DURATION * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocking=True,
        )

        write(filename, SAMPLE_RATE, recording)

        print("✅ Recording complete")
        return filename
    except KeyboardInterrupt:
        sd.stop()
        print("🛑 Recording interrupted")
        return None
    except sd.PortAudioError as err:
        print(f"❌ Microphone error: {err}")
        return None