import tempfile
import unittest
from pathlib import Path

from pria.voice.speech_to_text import SpeechToText, default_model_dir
from pria.voice.text_to_speech import TextToSpeech, voice_path


VOICE_READY = default_model_dir().joinpath("final.mdl").is_file() and voice_path().is_file()


@unittest.skipUnless(VOICE_READY, "modelos opcionais de voz ainda não instalados")
class LocalVoiceTests(unittest.TestCase):
    def test_local_tts_and_ptbr_stt_round_trip_without_microphone_or_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "fala-de-teste.wav"
            TextToSpeech().synthesize_to_file("Olá, esta é uma frase de teste da PRIA.", wav)
            self.assertTrue(wav.is_file())
            transcript = SpeechToText().transcribe_wav(wav).casefold()
            self.assertIn("teste", transcript)


if __name__ == "__main__":
    unittest.main()
