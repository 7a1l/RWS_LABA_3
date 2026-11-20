import numpy as np
from PIL import Image
import main


def test_adjust_channel_intensity():
    img = Image.new("RGB", (10, 10), color=(100, 100, 100))
    processed = main.adjust_channel_intensity(img, r_mult=2.0, g_mult=0.5, b_mult=3.0)
    arr = np.array(processed)
    # R: 100*2.0 = 200, G: 100*0.5 = 50, B: min(100*3.0, 255) = 255
    assert tuple(arr) == (200, 50, 255)
