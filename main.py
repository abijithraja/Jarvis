from src.stt.whisper_stt import transcribe_audio
from src.tts.speaker import speak


def main():
	print("🚀 Jarvis is running... (Press Ctrl+C to stop)")

	try:
		while True:
			text = transcribe_audio()

			if not text:
				print("⚠️ No speech detected")
				continue

			print("🧑 You:", text)

			response = f"You said: {text}"

			print("🤖 Jarvis:", response)
			speak(response)
	except KeyboardInterrupt:
		print("\n👋 Jarvis stopped.")


if __name__ == "__main__":
    main()
