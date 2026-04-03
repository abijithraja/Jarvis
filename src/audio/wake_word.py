import pvporcupine
import sounddevice as sd
import numpy as np
import os
import re

WAKE_PHRASE = "hey jarvis"


def contains_wake_phrase(text):
    normalized = " ".join(text.lower().split())
    return WAKE_PHRASE in normalized or normalized == "jarvis"


def strip_wake_phrase(text):
    lowered = text.lower()
    start_index = lowered.find(WAKE_PHRASE)

    if start_index >= 0:
        stripped = text[:start_index] + text[start_index + len(WAKE_PHRASE):]
        return re.sub(r"\s+", " ", stripped).strip(" ,.!?\t\n")

    if lowered.strip() == "jarvis":
        return ""

    return text.strip()


def listen_for_wake_word():
    access_key = os.getenv("PICOVOICE_ACCESS_KEY")
    if not access_key:
        raise RuntimeError("PICOVOICE_ACCESS_KEY is not set.")

    porcupine = pvporcupine.create(access_key=access_key, keywords=["jarvis"])

    print("👂 Listening for wake word: Hey Jarvis...")

    try:
        with sd.InputStream(
            samplerate=porcupine.sample_rate,
            channels=1,
            dtype="int16",
        ) as stream:
            while True:
                pcm, _ = stream.read(porcupine.frame_length)
                pcm = np.squeeze(pcm)

                result = porcupine.process(pcm)

                if result >= 0:
                    print("🎯 Wake word detected!")
                    return True
    finally:
        porcupine.delete()
