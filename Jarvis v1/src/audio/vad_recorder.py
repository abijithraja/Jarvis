import sounddevice as sd
import numpy as np
import webrtcvad
from scipy.io.wavfile import write

SAMPLE_RATE = 16000
FRAME_DURATION = 30
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION / 1000)

vad = webrtcvad.Vad(1)


def record_speech(filename="audio.wav"):
    audio_frames = []
    speech_started = False
    silence_counter = 0
    MAX_SILENCE_FRAMES = 18

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16') as stream:
        while True:
            frame, _ = stream.read(FRAME_SIZE)
            frame_bytes = frame.tobytes()

            is_speech = vad.is_speech(frame_bytes, SAMPLE_RATE)

            if is_speech:
                speech_started = True
                silence_counter = 0
                audio_frames.append(frame)

            elif speech_started:
                audio_frames.append(frame)
                silence_counter += 1

                if silence_counter > MAX_SILENCE_FRAMES:
                    break

    if audio_frames:
        audio_np = np.concatenate(audio_frames, axis=0)
        write(filename, SAMPLE_RATE, audio_np)
        return filename

    return None
