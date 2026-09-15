"""Uygulama ayarları: modeller, yollar ve transkripsiyon parametreleri."""

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_DIR / "models"

# Arayüzde görünen ad -> faster-whisper kısa adı veya Hugging Face repo id.
# Kısa adlar faster-whisper tarafından şu repolara eşlenir:
#   large-v3-turbo -> mobiuslabsgmbh/faster-whisper-large-v3-turbo (~1.6 GB)
#   medium         -> Systran/faster-whisper-medium               (~1.5 GB)
#   small          -> Systran/faster-whisper-small                (~480 MB)
MODELS: dict[str, str] = {
    "large-v3-turbo (önerilen)": "large-v3-turbo",
    "kotoba-whisper-v2.0 (Japonca özel, noktalamasız)": "kotoba-tech/kotoba-whisper-v2.0-faster",
    "medium": "medium",
    "small (hızlı, düşük kalite)": "small",
}
DEFAULT_MODEL = "large-v3-turbo (önerilen)"
# Zayıf bilgisayarlar için hızlı seçenek; taşınabilir pakete varsayılan olarak DEFAULT ile birlikte eklenir.
FAST_MODEL = "small (hızlı, düşük kalite)"

AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma", ".opus"}
VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}
SUPPORTED_EXTS = AUDIO_EXTS | VIDEO_EXTS

# Donanım
DEVICE = "cpu"
COMPUTE_TYPE = "int8"  # CPU'da en hızlı ve en az RAM tüketen seçenek
CPU_THREADS = 0  # 0 = CTranslate2 varsayılanı

# Transkripsiyon
LANGUAGE = "ja"
BEAM_SIZE = 5
VAD_FILTER = True  # Silero VAD ile sessiz bölümleri atla (hız + daha az halüsinasyon)
VAD_MIN_SILENCE_MS = 500
# Tekrar döngüsü (aynı cümlenin defalarca yazılması) görülürse False yapın.
CONDITION_ON_PREVIOUS_TEXT = True
# Japonca çıktıda noktalama zayıf kalırsa aşağıdaki gibi bir prompt noktalamayı teşvik eder:
# INITIAL_PROMPT = "こんにちは。今日はいい天気ですね。"
INITIAL_PROMPT: str | None = None
