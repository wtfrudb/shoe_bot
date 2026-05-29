import speech_recognition as sr
from gtts import gTTS
import os
from pydub import AudioSegment
import subprocess

FFMPEG_PATH = r"C:\Users\Tania\Desktop\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
AudioSegment.converter = FFMPEG_PATH
AudioSegment.ffmpeg = FFMPEG_PATH

def transcribe_voice(file_path):
    try:
        wav_path = file_path.replace(".ogg", ".wav")
        
        cmd = [FFMPEG_PATH, "-i", file_path, "-acodec", "pcm_s16le", "-ar", "16000", wav_path, "-y"]
        subprocess.run(cmd, capture_output=True, check=True)
        
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data, language="ru-RU")
                return text
            except sr.UnknownValueError:
                return "Не удалось распознать речь. Попробуйте сказать чётче."
            except sr.RequestError as e:
                return f"Ошибка сервиса распознавания: {e}"
            finally:
                for f in [wav_path, file_path]:
                    if os.path.exists(f):
                        try:
                            os.remove(f)
                        except:
                            pass
    except Exception as e:
        return f"Ошибка обработки голоса: {str(e)}"

def text_to_voice(text, output_path="response.ogg"):
    try:
        mp3_path = output_path.replace(".ogg", ".mp3")
        tts = gTTS(text=text, lang="ru")
        tts.save(mp3_path)
        
        cmd = [FFMPEG_PATH, "-i", mp3_path, "-c:a", "libopus", output_path, "-y"]
        subprocess.run(cmd, capture_output=True, check=True)
        
        if os.path.exists(mp3_path):
            os.remove(mp3_path)
        
        return output_path
    except Exception as e:
        print(f"TTS error: {e}")
        return None