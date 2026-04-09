
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
from pathlib import Path

def generate_kavach_heatmap(image_path: str | Path):
    """
    Generate a realistic fraud heatmap using multi-signal analysis:
    1. Grayscale conversion
    2. Canny Edge Detection
    3. Noise Inconsistency (ELA-based)
    4. Morphological cleaning & Bounding Boxes
    """
    # Load image
    img = cv2.imread(str(image_path))
    if img is None:
        return None, []
    
    original_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # --- 1. Edge Detection (Canny) ---
    edges = cv2.Canny(gray, 50, 150)
    
    # --- 2. Noise Inconsistency Analysis (ELA Logic) ---
    # We simulate ELA by comparing the image with a compressed version
    pil_img = Image.fromarray(original_rgb)
    temp_path = "temp_heatmap_ela.jpg"
    pil_img.save(temp_path, "JPEG", quality=90)
    compressed_img = Image.open(temp_path)
    
    ela_diff = ImageChops.difference(pil_img, compressed_img)
    extrema = ela_diff.getextrema()
    max_diff = max([ex[1] for ex in extrema])
    if max_diff == 0:
        max_diff = 1
    scale = 255.0 / max_diff
    ela_diff = ImageEnhance.Brightness(ela_diff).enhance(scale)
    ela_gray = cv2.cvtColor(np.array(ela_diff), cv2.COLOR_RGB2GRAY)
    
    import os
    if os.path.exists(temp_path):
        os.remove(temp_path)
        
    # --- 3. Combine Signals ---
    # Combine edges and noise inconsistencies to find high-frequency anomalies
    combined_signal = cv2.addWeighted(edges, 0.3, ela_gray, 0.7, 0)
    
    # --- 4. Binary Mask & Morphological Cleaning ---
    _, mask = cv2.threshold(combined_signal, 40, 255, cv2.THRESH_BINARY)
    
    kernel = np.ones((5,5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # --- 5. Bounding Boxes & Filtering ---
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    bboxes = []
    
    # Create a copy for drawing bounding boxes
    draw_img = original_rgb.copy()
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 100: # Filter small noise regions
            x, y, w, h = cv2.boundingRect(cnt)
            bboxes.append({"x": x, "y": y, "w": w, "h": h, "area": area})
            # Draw realistic bounding box
            cv2.rectangle(draw_img, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
    # --- 6. Create Heatmap Color Overlay ---
    # Use the combined signal as the intensity for the heatmap
    heatmap_color = cv2.applyColorMap(combined_signal, cv2.COLORMAP_JET)
    heatmap_color = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)
    
    # --- 7. Superimpose Heatmap on Original ---
    alpha = 0.5
    superimposed = cv2.addWeighted(heatmap_color, alpha, draw_img, 1 - alpha, 0)
    
    return Image.fromarray(superimposed), bboxes
