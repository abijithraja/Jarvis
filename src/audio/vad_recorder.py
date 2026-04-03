import sounddevice as sd
import numpy as np
import wave
import tempfile
import os

SAMPLE_RATE = 16000
CHANNELS = 1
SILENCE_THRESHOLD = 0.006     # RMS below this = silence
SILENCE_DURATION = 1.5        # seconds of silence to stop recording
MAX_DURATION = 15             # max seconds to record
CHUNK_SIZE = 512              # frames per chunk


def _rms(data):
    return np.sqrt(np.mean(data.astype(np.float32) ** 2)) / 32768.0


def get_silence_threshold() -> float:
    return float(SILENCE_THRESHOLD)


def set_silence_threshold(value: float) -> float:
    """Clamp and set speech detection threshold."""
    global SILENCE_THRESHOLD
    SILENCE_THRESHOLD = max(0.003, min(float(value), 0.03))
    return SILENCE_THRESHOLD


def _pick_input_device():
    """Prefer an actual microphone device over virtual/sound-mapper inputs."""
    try:
        devices = sd.query_devices()
        default_pair = sd.default.device
        default_input = default_pair[0] if isinstance(default_pair, (list, tuple)) else default_pair

        def _valid_input(idx):
            return isinstance(idx, int) and 0 <= idx < len(devices) and devices[idx]["max_input_channels"] > 0

        if _valid_input(default_input):
            name = devices[default_input]["name"].lower()
            if "sound mapper" not in name and "primary sound capture" not in name:
                return default_input

        for idx, dev in enumerate(devices):
            name = str(dev.get("name", "")).lower()
            if dev.get("max_input_channels", 0) > 0 and (
                "microphone" in name or "mic" in name or "array" in name
            ):
                return idx

        if _valid_input(default_input):
            return default_input

        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) > 0:
                return idx
    except Exception:
        pass
    return None


def calibrate_microphone(seconds: float = 5.0) -> dict:
    """Sample ambient audio and auto-tune the speech threshold."""
    seconds = max(1.0, min(float(seconds), 10.0))
    input_device = _pick_input_device()
    if input_device is None:
        raise RuntimeError("No microphone input device found")

    rms_samples = []
    total_chunks = int((SAMPLE_RATE / CHUNK_SIZE) * seconds)

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        blocksize=CHUNK_SIZE,
        device=input_device,
    ) as stream:
        for _ in range(total_chunks):
            data, _ = stream.read(CHUNK_SIZE)
            chunk = data[:, 0] if data.ndim > 1 else data.flatten()
            rms_samples.append(_rms(chunk))

    if not rms_samples:
        raise RuntimeError("Could not capture calibration audio")

    noise_floor = float(np.percentile(rms_samples, 95))
    tuned_threshold = set_silence_threshold(noise_floor * 1.8)

    return {
        "seconds": seconds,
        "device": input_device,
        "noise_floor": noise_floor,
        "threshold": tuned_threshold,
    }


def record_speech():
    """
    Records audio from the microphone until silence is detected.
    Returns path to a temporary .wav file, or None on failure.
    """
    print("🎙️  Listening...", flush=True)

    chunks = []
    silent_chunks = 0
    speaking_started = False

    silence_chunks_needed = int((SAMPLE_RATE / CHUNK_SIZE) * SILENCE_DURATION)
    max_chunks = int((SAMPLE_RATE / CHUNK_SIZE) * MAX_DURATION)

    input_device = _pick_input_device()

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                            dtype='int16', blocksize=CHUNK_SIZE, device=input_device) as stream:
            for _ in range(max_chunks):
                data, _ = stream.read(CHUNK_SIZE)
                chunk = data[:, 0] if data.ndim > 1 else data.flatten()
                chunks.append(chunk.copy())

                rms = _rms(chunk)

                if rms > SILENCE_THRESHOLD:
                    speaking_started = True
                    silent_chunks = 0
                else:
                    if speaking_started:
                        silent_chunks += 1

                if speaking_started and silent_chunks >= silence_chunks_needed:
                    break

    except Exception as e:
        print(f"❌ Microphone error: {e}")
        return None

    if not speaking_started or len(chunks) < 3:
        print("⚠️  I couldn't hear clear speech. Try speaking a bit louder.")
        return None

    audio = np.concatenate(chunks)

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()

    with wave.open(tmp.name, 'w') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())

    return tmp.name
