"""Model yükleme ve transkripsiyon motoru (faster-whisper / CTranslate2)."""

from __future__ import annotations

import gc
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

# Windows'ta Hugging Face önbelleği symlink kullanamayınca uyarı basar; sustur.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from faster_whisper import WhisperModel, download_model  # noqa: E402

from . import config  # noqa: E402

# Aynı anda tek model bellekte tutulur (8 GB RAM'de iki büyük model sığmaz).
_cache: dict[str, WhisperModel] = {}


@dataclass
class Update:
    """Transkripsiyon sırasında arayüze gönderilen ara durum."""

    text: str  # şimdiye kadar biriken metin
    progress: float  # 0.0 - 1.0
    duration: float  # dosyanın toplam süresi (saniye)


def is_supported(path: str | os.PathLike[str]) -> bool:
    return Path(path).suffix.lower() in config.SUPPORTED_EXTS


def is_audio(path: str | os.PathLike[str]) -> bool:
    return Path(path).suffix.lower() in config.AUDIO_EXTS


def model_name(model_key: str) -> str:
    try:
        return config.MODELS[model_key]
    except KeyError:
        raise ValueError(f"Bilinmeyen model: {model_key}") from None


def is_downloaded(model_key: str) -> bool:
    """Model daha önce models/ altına indirilmiş mi? (ağa çıkmaz)"""
    try:
        download_model(
            model_name(model_key),
            cache_dir=str(config.MODELS_DIR),
            local_files_only=True,
        )
        return True
    except Exception:
        return False


def get_model(model_key: str) -> WhisperModel:
    """Modeli yükler (gerekirse indirir). Farklı bir model istenirse eskisi bırakılır."""
    name = model_name(model_key)
    if name in _cache:
        return _cache[name]

    _cache.clear()
    gc.collect()

    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    # Model models/ altında tamsa ağa hiç çıkma: proxy'li/kapalı ağlarda beklemeyi ve hatayı önler.
    local_only = is_downloaded(model_key)
    try:
        model = WhisperModel(
            name,
            device=config.DEVICE,
            compute_type=config.COMPUTE_TYPE,
            download_root=str(config.MODELS_DIR),
            cpu_threads=config.CPU_THREADS,
            local_files_only=local_only,
        )
    except Exception as exc:  # ağ hatası, bozuk indirme vb.
        if local_only:
            raise RuntimeError(f"Model models/ klasöründe var ama yüklenemedi ({name}). Ayrıntı: {exc}") from exc
        raise RuntimeError(
            f"Model bulunamadı ve indirilemedi ({name}). İnternet/proxy engelliyorsa çevrimdışı paketi "
            "kullanın: hazır bir kurulumdan models/ klasörünü kopyalayın veya "
            f"tools\\build_offline_package.py çalıştırın. Ayrıntı: {exc}"
        ) from exc

    _cache[name] = model
    return model


def transcribe_file(path: str | os.PathLike[str], model_key: str) -> Iterator[Update]:
    """Dosyayı Japonca olarak transkript eder; her segmentte ara durum üretir.

    Generator terk edilirse (iptal) çözümleme de durur, çünkü faster-whisper
    segmentleri tembel (lazy) üretir.
    """
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"Dosya bulunamadı: {path.name}")
    if not is_supported(path):
        exts = ", ".join(sorted(config.SUPPORTED_EXTS))
        raise ValueError(f"Desteklenmeyen dosya türü: {path.suffix or '(uzantısız)'}. Desteklenenler: {exts}")

    model = get_model(model_key)

    try:
        segments, info = model.transcribe(
            str(path),
            language=config.LANGUAGE,
            task="transcribe",
            beam_size=config.BEAM_SIZE,
            vad_filter=config.VAD_FILTER,
            vad_parameters={"min_silence_duration_ms": config.VAD_MIN_SILENCE_MS},
            condition_on_previous_text=config.CONDITION_ON_PREVIOUS_TEXT,
            initial_prompt=config.INITIAL_PROMPT,
        )
    except Exception as exc:  # PyAV çözemedi, bozuk dosya vb.
        raise RuntimeError(f"Dosya çözümlenemedi ({path.name}). Ses akışı bulunamadı veya dosya bozuk. Ayrıntı: {exc}") from exc

    duration = float(info.duration or 0.0)
    lines: list[str] = []
    yield Update(text="", progress=0.0, duration=duration)

    for seg in segments:
        text = seg.text.strip()
        if text:
            lines.append(text)
        progress = min(seg.end / duration, 1.0) if duration > 0 else 0.0
        yield Update(text="\n".join(lines), progress=progress, duration=duration)

    yield Update(text="\n".join(lines), progress=1.0, duration=duration)
