"""MoviTranscriber - Gradio arayüzü.

Çalıştır: python app.py  (veya run.bat)
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import gradio as gr

from transcriber import config, engine

TITLE = "MoviTranscriber"
DESCRIPTION = (
    "Japonca ses veya video dosyanızı yükleyin, tamamen **bilgisayarınızda** çalışan Whisper modeli "
    "Japonca transkript üretsin. İnternet yalnızca seçilen modelin **ilk indirilmesinde** gerekir "
    "(large-v3-turbo ≈ 1.6 GB); sonrasında çevrimdışı çalışır."
)

TXT_DIR = Path(tempfile.gettempdir()) / "movitranscriber"


def _fmt_seconds(seconds: float) -> str:
    seconds = int(round(seconds))
    minutes, sec = divmod(seconds, 60)
    return f"{minutes} dk {sec} sn" if minutes else f"{sec} sn"


def _write_txt(source_name: str, text: str) -> str:
    TXT_DIR.mkdir(parents=True, exist_ok=True)
    out = TXT_DIR / f"{Path(source_name).stem}.txt"
    out.write_text(text + "\n", encoding="utf-8")
    return str(out)


def model_choices() -> list[tuple[str, str]]:
    """Açılır liste: (etiket, model anahtarı). İndirilmiş modeller işaretlenir."""
    return [
        (f"{key}   {'✓ hazır' if engine.is_downloaded(key) else '⬇ ilk kullanımda indirilir'}", key)
        for key in config.MODELS
    ]


def default_model() -> str:
    """İndirilmiş ilk modeli varsayılan yap (config sırasına göre); hiçbiri yoksa config'deki varsayılan."""
    for key in config.MODELS:
        if engine.is_downloaded(key):
            return key
    return config.DEFAULT_MODEL


def refresh_models(current: str):
    return gr.Dropdown(choices=model_choices(), value=current)


def on_file_change(file_path: str | None):
    """Ses dosyası yüklendiyse önizleme oynatıcısını göster; video/boşsa gizle."""
    if file_path and engine.is_audio(file_path):
        return gr.Audio(value=file_path, visible=True)
    return gr.Audio(value=None, visible=False)


def transcribe(file_path: str | None, model_key: str, progress=gr.Progress()):
    """Generator: her segmentte (durum, metin, indirme butonu) üretir."""
    if not file_path:
        raise gr.Error("Önce bir ses veya video dosyası yükleyin.")
    if not engine.is_supported(file_path):
        exts = ", ".join(sorted(config.SUPPORTED_EXTS))
        raise gr.Error(f"Desteklenmeyen dosya türü. Desteklenenler: {exts}")

    name = Path(file_path).name
    hidden_dl = gr.DownloadButton(visible=False)

    if engine.is_downloaded(model_key):
        yield "⏳ Model yükleniyor…", "", hidden_dl
    else:
        yield (
            "⬇️ Model ilk kez indiriliyor (0.5–1.6 GB). Bağlantı hızına göre birkaç dakika sürebilir; "
            "ilerleme terminal penceresinde görünür.",
            "",
            hidden_dl,
        )
    progress(0, desc="Model hazırlanıyor")

    started = time.time()
    work_started: float | None = None  # model yüklendikten sonraki ilk güncellemede başlar
    last = engine.Update(text="", progress=0.0, duration=0.0)
    try:
        for last in engine.transcribe_file(file_path, model_key):
            if work_started is None:
                work_started = time.time()
            progress(last.progress, desc="İşleniyor")
            eta = ""
            if last.progress >= 0.05:
                remaining = (time.time() - work_started) * (1 - last.progress) / last.progress
                eta = f", kalan ~{_fmt_seconds(remaining)}"
            yield f"🎙️ İşleniyor… %{int(last.progress * 100)}{eta} — {name}", last.text, hidden_dl
    except (ValueError, RuntimeError) as exc:
        raise gr.Error(str(exc)) from exc

    elapsed = time.time() - started
    if not last.text.strip():
        yield f"⚠️ Konuşma bulunamadı ({_fmt_seconds(elapsed)}). Dosyada Japonca konuşma olduğundan emin olun.", "", hidden_dl
        return

    txt_path = _write_txt(name, last.text)
    yield (
        f"✅ Tamamlandı — {_fmt_seconds(elapsed)} sürdü (ses: {_fmt_seconds(last.duration)})",
        last.text,
        gr.DownloadButton(value=txt_path, visible=True),
    )


def on_stop():
    return "⏹️ Durduruldu. Kısmi metin yukarıda kaldı."


with gr.Blocks(title=TITLE) as demo:
    gr.Markdown(f"# 🎌 {TITLE}\n\n{DESCRIPTION}")

    with gr.Row():
        with gr.Column(scale=2):
            file_in = gr.File(
                label="Ses veya video dosyası (sürükleyip bırakabilirsiniz)",
                file_types=sorted(config.SUPPORTED_EXTS),
                type="filepath",
            )
            audio_preview = gr.Audio(label="Önizleme", visible=False, interactive=False)
        with gr.Column(scale=1):
            model_dd = gr.Dropdown(
                choices=model_choices(),
                value=default_model(),
                label="Model",
                info="Büyük model = daha doğru, daha yavaş. Zayıf bilgisayarda hızlı taslak için small.",
            )
            with gr.Row():
                run_btn = gr.Button("Transkript Et", variant="primary")
                stop_btn = gr.Button("Durdur", variant="stop")

    status = gr.Markdown("")
    output = gr.Textbox(
        label="Japonca transkript",
        lines=18,
        placeholder="Sonuç burada görünecek…",
        buttons=["copy"],
    )
    dl_btn = gr.DownloadButton("TXT olarak indir", visible=False)

    file_in.change(on_file_change, inputs=file_in, outputs=audio_preview)
    run_event = run_btn.click(
        transcribe,
        inputs=[file_in, model_dd],
        outputs=[status, output, dl_btn],
    )
    # Transkripsiyon sırasında model indirilmiş olabilir; listedeki "hazır" işaretlerini tazele.
    run_event.then(refresh_models, inputs=model_dd, outputs=model_dd)
    stop_btn.click(on_stop, outputs=status, cancels=[run_event])


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1)  # düşük RAM: aynı anda tek transkripsiyon
    demo.launch(
        server_name="127.0.0.1",
        inbrowser=True,
        footer_links=[],
        theme=gr.themes.Soft(),
    )
