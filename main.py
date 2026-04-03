from src.stt.whisper_stt import transcribe_audio
from src.tts.speaker import speak


def main():
	print("Jarvis started...")

	while True:
		text = transcribe_audio()

		if not text:
			continue

		print("You:", text)

		response = f"You said: {text}"

		speak(response)


if __name__ == "__main__":
	main()
