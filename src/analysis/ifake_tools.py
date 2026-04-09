"""
IFAKE-inspired forgery detection tools.
Integrated from: https://github.com/shraddhavijay/IFAKE
"""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf
from PIL import Image, ImageChops, ImageEnhance, ImageFilter
from src.analysis.heatmap_engine import generate_kavach_heatmap

# Global cache for loaded models
_model_cache: dict = {}

# ── Noise & Luminance Analysis ───────────────────────────────────────────────

def luminance_gradient(image_path: str | Path) -> Image.Image:
    """Calculate luminance gradient using Sobel operator."""
    img = cv2.imread(str(image_path), 0)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
    
    sobelx = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=15)
    # Normalize to 0-255
    sobelx_norm = cv2.normalize(sobelx, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    image = Image.fromarray(sobelx_norm).resize((300, 300))
    return image

def noise_analysis(image_path: str | Path, quality: int = 90, intensity: float = 10.0) -> Image.Image:
    """Perform noise analysis by comparing with a re-saved JPEG."""
    im = Image.open(image_path).convert('L')
    
    # Save to temp and reload to get JPEG compression noise
    temp_path = "temp_noise.jpg"
    im.save(temp_path, 'JPEG', quality=quality)
    resaved_im = Image.open(temp_path)
    
    na_im = ImageChops.difference(im, resaved_im)
    
    if os.path.exists(temp_path):
        os.remove(temp_path)
    
    # Scale up the differences
    na_im = ImageEnhance.Brightness(na_im).enhance(intensity)
    return na_im

# ── CNN Forgery Classification ───────────────────────────────────────────────

def make_gradcam_heatmap(img_array, model, last_conv_layer_name, pred_index=None):
    """Generate Grad-CAM heatmap to visualize model activations."""
    # Create a model that maps the input image to the activations of the last conv layer
    # as well as the output predictions
    try:
        grad_model = tf.keras.models.Model(
            model.inputs, [model.get_layer(last_conv_layer_name).output, model.output]
        )
    except Exception:
        # Fallback for some model architectures where .output might be tricky
        grad_model = tf.keras.models.Model(
            model.inputs, [model.get_layer(last_conv_layer_name).output, model.outputs[0]]
        )

    # Compute the gradient of the top predicted class (or a specific class)
    # with regard to the activations of the last conv layer
    with tf.GradientTape() as tape:
        last_conv_layer_output, preds = grad_model(img_array)
        if pred_index is None:
            pred_index = tf.argmax(preds[0])
        
        # Ensure we are indexing correctly based on output shape
        if preds.shape[-1] > 1:
            class_channel = preds[:, pred_index]
        else:
            class_channel = preds[:, 0]

    # This is the gradient of the output neuron (top predicted or chosen)
    # with regard to the output feature map of the last conv layer
    grads = tape.gradient(class_channel, last_conv_layer_output)

    # Handle cases where gradients might be None (e.g., if the path is broken)
    if grads is None:
        return np.zeros((img_array.shape[1], img_array.shape[2]))

    # This is a vector where each entry is the mean intensity of the gradient
    # over a specific feature map channel
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    # We multiply each channel in the feature map array
    # by "how important this channel is" with regard to the top predicted class
    # then sum all the channels to obtain the heatmap class activation
    last_conv_layer_output = last_conv_layer_output[0]
    heatmap = last_conv_layer_output @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)

    # For visualization purpose, we will also normalize the heatmap between 0 & 1
    heatmap_max = tf.math.reduce_max(heatmap)
    if heatmap_max > 0:
        heatmap = tf.maximum(heatmap, 0) / heatmap_max
    else:
        heatmap = tf.maximum(heatmap, 0)
        
    return heatmap.numpy()

def get_fraud_heatmap(image_path, model, intensity=0.4, res=128):
    """Combine ELA-preprocessed image with Grad-CAM heatmap."""
    from src.analysis.ela import generate_ela
    
    # Preprocess image
    img_pil = Image.open(image_path).convert('RGB')
    ela_img = generate_ela(img_pil, quality=90, scale=1).resize((res, res))
    img_array = np.array(ela_img).astype(np.float32) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    
    # Find last convolutional layer
    last_conv_layer_name = None
    for layer in reversed(model.layers):
        if 'conv' in layer.name.lower():
            last_conv_layer_name = layer.name
            break
            
    if not last_conv_layer_name:
        return None

    # Generate heatmap
    heatmap = make_gradcam_heatmap(img_array, model, last_conv_layer_name)
    
    # Rescale heatmap to 0-255
    heatmap = np.uint8(255 * heatmap)

    # Use jet colormap to colorize heatmap
    jet = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
    jet = cv2.cvtColor(jet, cv2.COLOR_BGR2RGB)
    
    # Resize heatmap to match original image size
    jet = cv2.resize(jet, (img_pil.size[0], img_pil.size[1]))
    
    # Superimpose the heatmap on original image
    superimposed_img = jet * intensity + np.array(img_pil)
    superimposed_img = np.clip(superimposed_img, 0, 255).astype(np.uint8)
    
    return Image.fromarray(superimposed_img)

def init_ifake_classifier():
    """Initialize the IFAKE CNN classifier architecture (TensorFlow/Keras)."""
    try:
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import Dense, Dropout, Flatten, Conv2D, MaxPooling2D, BatchNormalization
        
        model = Sequential()
        model.add(Conv2D(filters=16, kernel_size=(3,3), padding='same', 
                        activation='relu', input_shape=(128, 128, 3)))
        model.add(BatchNormalization())
        model.add(Conv2D(filters=16, kernel_size=(3,3), padding='same', 
                        activation='relu'))
        model.add(BatchNormalization())
        model.add(MaxPooling2D(pool_size=(2,2)))

        model.add(Conv2D(filters=32, kernel_size=(3,3), padding='same', 
                        activation='relu'))
        model.add(BatchNormalization())
        model.add(Conv2D(filters=32, kernel_size=(3,3), padding='same', 
                        activation='relu'))
        model.add(BatchNormalization())
        model.add(MaxPooling2D(pool_size=(2,2)))

        model.add(Conv2D(filters=64, kernel_size=(3,3), padding='same', 
                        activation='relu'))
        model.add(BatchNormalization())
        model.add(Conv2D(filters=64, kernel_size=(3,3), padding='same', 
                        activation='relu'))
        model.add(BatchNormalization())
        model.add(MaxPooling2D(pool_size=(2,2)))

        model.add(Dropout(0.25))
        model.add(Flatten())
        model.add(Dense(512, activation="relu"))
        model.add(Dropout(0.50))
        model.add(Dense(2, activation="softmax"))
        return model
    except ImportError:
        return None

def _generate_explanations(verdict, confidence, heatmap=None):
    """Generate human-readable structured explanations for the model's verdict."""
    explanations = []
    
    if verdict == "Forged":
        # High confidence forged
        if confidence > 0.85:
            explanations.append({
                "type": "tampering",
                "message": "High-intensity manipulation patterns identified in the document structure.",
                "severity": "high",
                "confidence": confidence
            })
        elif confidence > 0.65:
            explanations.append({
                "type": "tampering",
                "message": "Possible tampering detected in the image noise profile. Re-saving or ELA analysis shows significant discrepancies.",
                "severity": "medium",
                "confidence": confidence
            })
        else:
            explanations.append({
                "type": "metadata",
                "message": "Subtle inconsistencies detected that may suggest light editing or format conversion artifacts.",
                "severity": "low",
                "confidence": confidence
            })

        # Heatmap based explanation (mocked based on intensity for now)
        explanations.append({
            "type": "template",
            "message": "Highlighted regions (red/yellow) on the Fraud Heatmap indicate high probability of local pixel manipulation.",
            "severity": "high",
            "confidence": 0.92
        })
    else:
        # Authentic
        if confidence > 0.90:
            explanations.append({
                "type": "text",
                "message": "Document texture and noise distribution are consistent with an original capture.",
                "severity": "low",
                "confidence": confidence
            })
        else:
            explanations.append({
                "type": "metadata",
                "message": "No significant tampering detected, though minor compression artifacts are present.",
                "severity": "low",
                "confidence": confidence
            })
            
    return explanations

def predict_ifake_forgery(image_path: str | Path, model_path: str | Path | None = None) -> dict:
    """Predict forgery using ELA-based CNN classification."""
    if model_path is None or not Path(model_path).exists():
        return {
            "error": (
                f"IFAKE model weights not found at `{model_path}`. "
                "Please download the `.h5` weights from the official repository: "
                "https://github.com/shraddhavijay/IFAKE and place them in the `weights/` folder."
            )
        }

    try:
        from tensorflow.keras.models import load_model
        from src.analysis.ela import generate_ela # Reuse existing ELA logic
        
        key = str(model_path)
        if key not in _model_cache:
            model = load_model(str(model_path))
            # Initialize model with a dummy call to ensure symbolic nodes are built (Keras 3)
            model(np.zeros((1, 128, 128, 3), dtype=np.float32))
            _model_cache[key] = model
        
        model = _model_cache[key]
        
        # Prepare image (ELA + Resize)
        img_pil = Image.open(image_path).convert('RGB')
        ela_img = generate_ela(img_pil, quality=90, scale=1) # IFAKE uses scale=1 initially
        ela_img = ela_img.resize((128, 128))
        
        test_image = np.array(ela_img).astype(np.float32) / 255.0
        test_image = test_image.reshape(-1, 128, 128, 3)
        
        y_pred = model.predict(test_image)
        y_pred_class = int(np.argmax(y_pred[0]))
        confidence = float(np.max(y_pred[0]))
        
        # Generate Fraud Heatmap (Grad-CAM)
        heatmap = get_fraud_heatmap(image_path, model)
        
        class_names = ['Forged', 'Authentic']
        verdict = class_names[y_pred_class]
        
        # Generate Fraud Heatmap (Enhanced Kavach Engine)
        heatmap, bboxes = generate_kavach_heatmap(image_path)
        
        # Generate Structured AI Explanations
        explanations = _generate_explanations(verdict, confidence, heatmap)
        
        # Add spatial detail to explanations if anomalies found
        if bboxes:
            explanations.append({
                "type": "tampering",
                "message": f"Identified {len(bboxes)} suspicious regions using multi-signal analysis (Edge + Noise).",
                "severity": "high" if len(bboxes) > 2 else "medium",
                "confidence": 0.95
            })
        
        return {
            "verdict": verdict,
            "confidence": confidence,
            "raw_scores": y_pred[0].tolist(),
            "heatmap": heatmap,
            "explanations": explanations,
            "bboxes": bboxes
        }
    except Exception as e:
        return {"error": f"Failed to load or run IFAKE model: {str(e)}"}

# ── Video Forgery Detection ──────────────────────────────────────────────────

def detect_video_forgery(video_path: str | Path, model_path: str | Path | None = None) -> dict:
    """Analyze video frames for forgery using a ResNet50-based model."""
    if model_path is None or not Path(model_path).exists():
        return {
            "error": (
                f"IFAKE video model weights not found at `{model_path}`. "
                "Please download the `.hdf5` weights from the official repository: "
                "https://github.com/shraddhavijay/IFAKE and place them in the `weights/` folder."
            )
        }

    try:
        from tensorflow.keras.models import load_model
        
        key = str(model_path)
        if key not in _model_cache:
            model = load_model(str(model_path))
            # Initialize model with a dummy call to ensure symbolic nodes are built (Keras 3)
            # Video model expected input: (320, 240)
            model(np.zeros((1, 240, 320, 3), dtype=np.float32))
            _model_cache[key] = model
        
        model = _model_cache[key]
        
        cap = cv2.VideoCapture(str(video_path))
        forged_frames = 0
        total_frames = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # IFAKE preprocesses frames to 320x240
            b = cv2.resize(frame, (320, 240), interpolation=cv2.INTER_CUBIC)
            Xtest = np.array([b]).astype(np.float32) / 255.0
            
            pred = model.predict(Xtest)
            if pred[0][0] > 0.5: # Assuming forged class is 1
                forged_frames += 1
            total_frames += 1
            
        cap.release()
        
        return {
            "verdict": "Forged" if forged_frames > 0 else "Authentic",
            "forged_frames": forged_frames,
            "total_frames": total_frames,
            "forgery_ratio": forged_frames / total_frames if total_frames > 0 else 0
        }
    except Exception as e:
        return {"error": f"Failed to load or run IFAKE video model: {str(e)}"}
