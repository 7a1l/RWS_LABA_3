import hashlib
import io
import os
import requests
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Веб-приложение изменения интенсивности цветовых каналов")

os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

RECAPTCHA_SITE_KEY = "6Le8PiouAAAAAPAZkaXLkQF0eytGn-XCCNu6tCRD"
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "YOUR_SECRET_KEY")


def adjust_channel_intensity(image: Image.Image, r_mult: float, g_mult: float, b_mult: float) -> Image.Image:
    if r_mult < 0 or g_mult < 0 or b_mult < 0:
        raise ValueError("Коэффициенты интенсивности не могут быть отрицательными")

    img_array = np.array(image.convert("RGB"), dtype=np.float32)
    img_array[:, :, 0] *= r_mult
    img_array[:, :, 1] *= g_mult
    img_array[:, :, 2] *= b_mult

    # Ограничиваем значения пикселей в допустимом диапазоне 0..255
    result_array = np.clip(img_array, 0, 255).astype(np.uint8)
    return Image.fromarray(result_array, mode="RGB")


def save_color_histogram(image: Image.Image, save_path: str, title_prefix: str):
    img_array = np.array(image.convert("RGB"))
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5))

    colors = [('red', 'Red (R)', 0), ('green', 'Green (G)', 1), ('blue', 'Blue (B)', 2)]
    for color, label, channel_idx in colors:
        hist, _ = np.histogram(img_array[:, :, channel_idx], bins=256, range=(0, 256))
        axes[channel_idx].plot(hist, color=color, linewidth=1.2)
        axes[channel_idx].set_title(f"{title_prefix}: {label}")
        axes[channel_idx].set_xlabel("Значение цвета (0-255)")
        axes[channel_idx].set_ylabel("Частота")
        axes[channel_idx].grid(True, linestyle='--', alpha=0.4)

    plt.tight_layout()
    fig.savefig(save_path, format='png', dpi=120)
    plt.close(fig)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "ready": False,
            "site_key": RECAPTCHA_SITE_KEY
        }
    )


@app.post("/process", response_class=HTMLResponse)
async def process_image(
    request: Request,
    r_mult: float = Form(...),
    g_mult: float = Form(...),
    b_mult: float = Form(...),
    file: UploadFile = File(...),
    resp: str = Form(default="")
):
    if RECAPTCHA_SECRET_KEY and RECAPTCHA_SECRET_KEY != "YOUR_SECRET_KEY":
        try:
            payload = {"secret": RECAPTCHA_SECRET_KEY, "response": resp}
            verify_url = "https://google.com" + "/recaptcha/api/siteverify"
            verify_response = requests.post(verify_url, data=payload, timeout=5)
            if verify_response.status_code == 200 and verify_response.text:
                if not verify_response.json().get("success"):
                    raise HTTPException(status_code=400, detail="Ошибка проверки капчи")
        except requests.RequestException:
            raise HTTPException(status_code=503, detail="Не удалось связаться с сервером reCAPTCHA")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Файл не выбран")

    for val in (r_mult, g_mult, b_mult):
        if val < 0.0 or val > 3.0:
            raise HTTPException(status_code=400, detail="Коэффициенты должны быть в диапазоне от 0.0 до 3.0")

    contents = await file.read()
    orig_img = Image.open(io.BytesIO(contents)).convert("RGB")

    processed_img = adjust_channel_intensity(orig_img, r_mult, g_mult, b_mult)

    file_hash = hashlib.sha256(
        f"{file.filename}_{r_mult}_{g_mult}_{b_mult}".encode("utf-8")
    ).hexdigest()[:12]

    orig_filename = f"{file_hash}_orig.png"
    proc_filename = f"{file_hash}_proc.png"
    hist_orig_filename = f"{file_hash}_hist_orig.png"
    hist_proc_filename = f"{file_hash}_hist_proc.png"

    orig_img.save(f"./static/{orig_filename}", "PNG")
    processed_img.save(f"./static/{proc_filename}", "PNG")

    save_color_histogram(orig_img, f"./static/{hist_orig_filename}", "Исходное")
    save_color_histogram(processed_img, f"./static/{hist_proc_filename}", "Новое")

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "ready": True,
            "site_key": RECAPTCHA_SITE_KEY,
            "r_mult": r_mult,
            "g_mult": g_mult,
            "b_mult": b_mult,
            "orig_url": f"/static/{orig_filename}",
            "proc_url": f"/static/{proc_filename}",
            "hist_orig_url": f"/static/{hist_orig_filename}",
            "hist_proc_url": f"/static/{hist_proc_filename}",
        }
    )