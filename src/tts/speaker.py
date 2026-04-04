"""
Premium TTS: edge-tts (Microsoft neural voices) with pyttsx3 fallback.
Install: pip install edge-tts
"""

import asyncio
import os
import tempfile
import threading
import subprocess
import shutil
import platform
import pyttsx3

_lock = threading.Lock()
_current_player = None
_current_engine = None

VOICE = os.environ.get("JARVIS_VOICE", "en-US-GuyNeural")
RATE  = os.environ.get("JARVIS_RATE",  "+10%")
USE_EDGE_TTS = os.environ.get("JARVIS_USE_EDGE_TTS", "0" if os.name == "nt" else "1").strip().lower() in {
    "1", "true", "yes", "on"
}

AVAILABLE_VOICES = {
    "guy":   "en-US-GuyNeural",
    "davis": "en-US-DavisNeural",
    "tony":  "en-US-TonyNeural",
    "aria":  "en-US-AriaNeural",
    "ryan":  "en-GB-RyanNeural",
    "sonia": "en-GB-SoniaNeural",
}

def set_voice(name: str):
    global VOICE
    VOICE = AVAILABLE_VOICES.get(name.lower(), name)
    print(f"Voice set to: {VOICE}")

def speak(text: str, rate: str = None, pitch: str = "+0Hz"):
    if not text or not text.strip():
        return
    text = _clean(text)
    with _lock:
        if _try_edge_tts(text, rate or RATE, pitch):
            return
        _pyttsx3_speak(text)


def stop_speaking():
    """Best-effort stop for active TTS playback during shutdown."""
    global _current_player, _current_engine

    try:
        if _current_engine is not None:
            _current_engine.stop()
    except Exception:
        pass
    finally:
        _current_engine = None

    player = _current_player
    if player is not None:
        try:
            if player.poll() is None:
                player.terminate()
                try:
                    player.wait(timeout=1.0)
                except Exception:
                    player.kill()
        except Exception:
            pass
        finally:
            _current_player = None

def _try_edge_tts(text: str, rate: str, pitch: str) -> bool:
    if not USE_EDGE_TTS:
        return False
    try:
        import edge_tts
        asyncio.run(_edge_speak(text, rate, pitch))
        return True
    except ImportError:
        return False
    except Exception as e:
        print(f"edge-tts failed: {e} - falling back to pyttsx3")
        return False

async def _edge_speak(text: str, rate: str, pitch: str):
    import edge_tts
    communicate = edge_tts.Communicate(text, VOICE, rate=rate, pitch=pitch)
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    await communicate.save(tmp.name)
    _play_audio(tmp.name)
    try:
        os.remove(tmp.name)
    except Exception:
        pass

def _play_audio(path: str):
    global _current_player

    system = platform.system()
    if system == "Windows":
        # edge-tts saves MP3; play it with Windows Media Player when available.
        player = subprocess.Popen(
            ["cmd", "/c", "start", "/min", "/wait", "", "wmplayer", "/play", "/close", path],
            capture_output=True,
            text=True,
        )
        _current_player = player
        player.wait()
        _current_player = None
        if player.returncode not in (0, None):
            raise subprocess.CalledProcessError(player.returncode, player.args, output=player.stdout, stderr=player.stderr)
        return

    if system == "Darwin":
        player = subprocess.Popen(["afplay", path])
        _current_player = player
        player.wait()
        _current_player = None
        if player.returncode not in (0, None):
            raise subprocess.CalledProcessError(player.returncode, player.args)
        return

    for player in ["mpg123", "ffplay", "aplay"]:
        if shutil.which(player):
            proc = None
            if player == "ffplay":
                proc = subprocess.Popen([player, "-nodisp", "-autoexit", "-loglevel", "quiet", path])
            elif player == "mpg123":
                proc = subprocess.Popen([player, "-q", path])
            else:
                proc = subprocess.Popen([player, path])

            _current_player = proc
            proc.wait()
            _current_player = None
            if proc.returncode not in (0, None):
                raise subprocess.CalledProcessError(proc.returncode, proc.args)
            return

    raise RuntimeError("No compatible audio player found for edge-tts output")

def _get_pyttsx_engine():
    engine = pyttsx3.init()
    engine.setProperty("rate", 185)
    engine.setProperty("volume", 1.0)
    voices = engine.getProperty("voices")
    for v in voices:
        if "david" in v.name.lower():
            engine.setProperty("voice", v.id)
            break
    return engine

def _pyttsx3_speak(text: str):
    global _current_engine

    last_error = None
    for _ in range(2):
        engine = None
        try:
            engine = _get_pyttsx_engine()
            _current_engine = engine
            engine.say(text)
            engine.runAndWait()
            return
        except Exception as e:
            last_error = e
        finally:
            if engine is not None:
                try:
                    engine.stop()
                except Exception:
                    pass
            _current_engine = None
    if last_error:
        print(f"TTS error: {last_error}")

def _clean(text: str) -> str:
    import re
    text = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'\n+', ' ', text).strip()
    return text
