from PIL import Image
import main


def test_adjust_channel_intensity():
    img = Image.new("RGB", (10, 10), color=(100, 100, 100))
    processed = main.adjust_channel_intensity(img, r_mult=2.0, g_mult=0.5, b_mult=3.0)
    assert processed.getpixel((0, 0)) == (200, 50, 255)
