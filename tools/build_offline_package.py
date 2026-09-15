"""Çevrimdışı dağıtım paketi oluşturur.

İnternet erişimi olan BİR makinede, sistemdeki Python ile bir kez çalıştırılır:

    python tools\\build_offline_package.py                 # large-v3-turbo + small (~2.1 GB model)
    python tools\\build_offline_package.py --model small   # sadece belirtilen model(ler)
    python tools\\build_offline_package.py --all-models    # listedeki tüm modeller (~5 GB)

Yaptıkları (hepsi proje klasörünün içine):
  1. python/    gömülebilir (embeddable) Python indirilir ve açılır; kurulum/yönetici hakkı gerekmez
  2. packages/  requirements.txt'teki tüm paketler bu klasöre kurulur
  3. models/    seçilen Whisper modeli indirilir (symlink'ler gerçek dosyaya çevrilir)
  4. Paket bütünlüğü doğrulanır

Sonrasında proje klasörü olduğu gibi (USB / ağ paylaşımı) diğer bilgisayarlara kopyalanır;
orada run.bat çift tıklanır, hiçbir şey indirilmez.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY_DIR = ROOT / "python"
PKG_DIR = ROOT / "packages"
MODELS_DIR = ROOT / "models"
REQUIREMENTS = ROOT / "requirements.txt"

sys.path.insert(0, str(ROOT))
from transcriber import config  # noqa: E402

MAJOR, MINOR, MICRO = sys.version_info[:3]
PY_VERSION = f"{MAJOR}.{MINOR}.{MICRO}"
EMBED_ZIP_URL = f"https://www.python.org/ftp/python/{PY_VERSION}/python-{PY_VERSION}-embed-amd64.zip"


def log(msg: str) -> None:
    print(f"[paket] {msg}", flush=True)


def retry(label: str, fn, tries: int = 5, wait: int = 10):
    last: Exception | None = None
    for attempt in range(1, tries + 1):
        try:
            return fn()
        except Exception as exc:  # ağ hataları dahil her şey
            last = exc
            log(f"{label}: deneme {attempt}/{tries} başarısız: {str(exc)[:200]}")
            if attempt < tries:
                time.sleep(wait)
    raise RuntimeError(f"{label}: {tries} denemede başarılamadı. Son hata: {last}")


# ---------------------------------------------------------------- 1) Python
def step_python(force: bool) -> None:
    exe = PY_DIR / "python.exe"
    if exe.exists() and not force:
        log(f"python/ zaten var, atlanıyor ({exe})")
        return
    if PY_DIR.exists():
        shutil.rmtree(PY_DIR)
    PY_DIR.mkdir(parents=True)
    zip_path = PY_DIR / "python-embed.zip"

    def download():
        log(f"Gömülebilir Python indiriliyor: {EMBED_ZIP_URL}")
        urllib.request.urlretrieve(EMBED_ZIP_URL, zip_path)
        if zip_path.stat().st_size < 1_000_000:
            raise RuntimeError("İndirilen dosya çok küçük, muhtemelen hatalı")

    retry("Python indirme", download)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(PY_DIR)
    zip_path.unlink()

    # ._pth dosyası: sys.path'i sabitler; ortam değişkenleri ve sistem Python'u yok sayılır.
    pth_files = list(PY_DIR.glob("python*._pth"))
    if not pth_files:
        raise RuntimeError("._pth dosyası bulunamadı, gömülebilir Python beklenen yapıda değil")
    pth = pth_files[0]
    pth.write_text(
        f"python{MAJOR}{MINOR}.zip\n.\n..\\packages\n..\n#import site\n",
        encoding="ascii",
    )
    log(f"python/ hazır ({pth.name} güncellendi)")


# ---------------------------------------------------------------- 2) Paketler
def step_packages(force: bool) -> None:
    marker = PKG_DIR / "gradio"
    if marker.exists() and not force:
        log("packages/ zaten var, atlanıyor (yeniden kurmak için --force)")
        return
    if PKG_DIR.exists():
        shutil.rmtree(PKG_DIR)
    cmd = [
        sys.executable, "-m", "pip", "install",
        "--target", str(PKG_DIR),
        "--only-binary=:all:",
        "--platform", "win_amd64",
        "--python-version", f"{MAJOR}.{MINOR}",
        "--implementation", "cp",
        "-r", str(REQUIREMENTS),
    ]
    log("Paketler packages/ altına kuruluyor (yaklaşık 1 GB indirme)...")

    def install():
        subprocess.run(cmd, check=True)

    retry("pip install", install, tries=3, wait=15)
    for junk in ("bin", "Scripts"):
        shutil.rmtree(PKG_DIR / junk, ignore_errors=True)
    log("packages/ hazır")


# ---------------------------------------------------------------- 3) Modeller
def _materialize_symlinks(root: Path) -> int:
    """Geliştirici modu açık makinelerde HF önbelleği symlink kullanır; kopyalanınca kırılır.
    Symlink'leri gerçek dosyalarla değiştirir."""
    count = 0
    for p in root.rglob("*"):
        if p.is_symlink():
            target = p.resolve()
            p.unlink()
            shutil.copy2(target, p)
            count += 1
    return count


def step_models(model_names: list[str]) -> None:
    MODELS_DIR.mkdir(exist_ok=True)
    py = PY_DIR / "python.exe"
    env = {
        **os.environ,
        "HF_HUB_DISABLE_XET": "1",  # klasik HTTPS indirme: proxy/kararsız ağlarda daha dayanıklı, kaldığı yerden devam eder
        "HF_HUB_DISABLE_SYMLINKS_WARNING": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    code = (
        "import sys; from faster_whisper import download_model; "
        "print(download_model(sys.argv[1], cache_dir=sys.argv[2]))"
    )
    for name in model_names:
        log(f"Model indiriliyor: {name}")

        def download():
            subprocess.run([str(py), "-c", code, name, str(MODELS_DIR)], check=True, env=env, cwd=ROOT)

        retry(f"Model {name}", download, tries=6, wait=15)
        log(f"Model hazır: {name}")

    fixed = _materialize_symlinks(MODELS_DIR)
    if fixed:
        log(f"{fixed} symlink gerçek dosyaya çevrildi")


# ---------------------------------------------------------------- 4) Doğrulama
def step_verify(model_names: list[str]) -> None:
    py = PY_DIR / "python.exe"
    code = (
        "import faster_whisper, gradio, ctranslate2, av, onnxruntime, sys\n"
        "print('  paketler OK: faster-whisper', faster_whisper.__version__, '| gradio', gradio.__version__,\n"
        "      '| python', sys.version.split()[0])\n"
        "from faster_whisper import download_model\n"
        "for n in sys.argv[1:]:\n"
        "    download_model(n, cache_dir='models', local_files_only=True); print('  model OK:', n)\n"
        "import app; print('  app.py OK')\n"
    )
    subprocess.run([str(py), "-c", code, *model_names], check=True, cwd=ROOT,
                   env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def folder_size_mb(p: Path) -> float:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6 if p.exists() else 0.0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", action="append", default=[],
                    help="İndirilecek model (kısa ad veya HF repo id). Birden fazla kez verilebilir.")
    ap.add_argument("--all-models", action="store_true", help="config.MODELS içindeki tüm modelleri indir")
    ap.add_argument("--force", action="store_true", help="python/ ve packages/ klasörlerini yeniden oluştur")
    ap.add_argument("--skip-models", action="store_true", help="Model indirme adımını atla")
    args = ap.parse_args()

    if sys.platform != "win32":
        sys.exit("Bu betik Windows dağıtım paketi üretir; Windows'ta çalıştırın.")

    if args.all_models:
        models = list(dict.fromkeys(config.MODELS.values()))
    elif args.model:
        models = args.model
    else:
        # Varsayılan: doğru model (turbo) + zayıf bilgisayarlar için hızlı model (small)
        models = list(dict.fromkeys([config.MODELS[config.DEFAULT_MODEL], config.MODELS[config.FAST_MODEL]]))

    log(f"Proje: {ROOT}")
    log(f"Python {PY_VERSION} | modeller: {', '.join(models)}")

    step_python(args.force)
    step_packages(args.force)
    if not args.skip_models:
        step_models(models)
    step_verify([] if args.skip_models else models)

    log("Tamamlandı. Klasör boyutları:")
    for d in (PY_DIR, PKG_DIR, MODELS_DIR):
        log(f"  {d.name:9s} {folder_size_mb(d):8.0f} MB")
    log("Bu klasörü olduğu gibi kopyalayın; hedef bilgisayarda run.bat çift tıklanır.")


if __name__ == "__main__":
    main()
