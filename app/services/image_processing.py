from PIL import Image
import cv2
import numpy as np

def adjust_channel_curve_lab(image, clip_limit=1.0):
    lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(1,10))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

def balance_colors(image, red_factor=0.9, green_factor=1.0, blue_factor=1.2):
    b, g, r = cv2.split(image)
    r = np.clip(r * red_factor, 0, 255).astype(np.uint8)
    g = np.clip(g * green_factor, 0, 255).astype(np.uint8)
    b = np.clip(b * blue_factor, 0, 255).astype(np.uint8)
    return cv2.merge([b, g, r])

def clip_histogram(image, r_clip_low=5, r_clip_high=99, g_clip_low=5, g_clip_high=99, b_clip_low=5, b_clip_high=99 ):
    image = image.astype(np.uint8)
    b, g, r = cv2.split(image)
    b = cv2.equalizeHist(b)
    g = cv2.equalizeHist(g)
    r = cv2.equalizeHist(r)
    r_min, r_max = np.percentile(r, [r_clip_low, r_clip_high])
    r = np.clip(r, r_min, r_max).astype(np.uint8)
    g_min, g_max = np.percentile(g, [g_clip_low, g_clip_high])
    g = np.clip(g, g_min, g_max).astype(np.uint8)
    b_min, b_max = np.percentile(b, [b_clip_low,  b_clip_high])
    b = np.clip(b, b_min, b_max).astype(np.uint8)
    return cv2.merge([b, g, r])
 
def desaturate_red_and_yellow_lab(image, red_intensity=0.5, yellow_intensity=0.5, yellow_threshold=135):
    """
    Reduce el rojo (a*) y el amarillo (b*) en una imagen en espacio LAB.
    :param image: imagen BGR
    :param red_intensity: factor de reducción de rojos (0.0 = sin rojo, 1.0 = sin cambio)
    :param yellow_intensity: factor de reducción de amarillo
    :param yellow_threshold: umbral mínimo para considerar que hay amarillo
    :return: imagen corregida
    """
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # --- Rojo (canal a*) ---
    a = a.astype(np.int16)
    red_mask = a > 128
    a[red_mask] = 128 + ((a[red_mask] - 128) * red_intensity)
    a = np.clip(a, 0, 255).astype(np.uint8)

    # --- Amarillo (canal b*) ---
    b = b.astype(np.int16)
    yellow_mask = b > yellow_threshold
    b[yellow_mask] = yellow_threshold + ((b[yellow_mask] - yellow_threshold) * yellow_intensity)
    b = np.clip(b, 0, 255).astype(np.uint8)

    lab_modified = cv2.merge([l, a, b])
    result = cv2.cvtColor(lab_modified, cv2.COLOR_LAB2BGR)
    return result


def process_image(image_path: str, output_path: str):
    img = Image.open(image_path).convert('RGB')
    inverted_img = Image.eval(img, lambda x: 255 - x)
    na = np.array(inverted_img, dtype=np.uint8)

    # Aplicar recorte del histograma
    clipped = clip_histogram(na)


    # Normalizar
    normalized = cv2.normalize(clipped, None, 0, 245, cv2.NORM_MINMAX)

    # Balancear colores
    balanced = balance_colors(normalized, red_factor=0.9, green_factor=0.85, blue_factor=1.0)

    # Reducir saturación del rojo
    ajustada = desaturate_red_and_yellow_lab(balanced, red_intensity=0.6, yellow_intensity=0.9, yellow_threshold=100)


    # Guardar imagen
    processed_img = Image.fromarray(ajustada.astype(np.uint8))
    processed_img.save(output_path)
