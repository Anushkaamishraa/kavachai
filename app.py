"""
DocAuth — Document Forgery Detection and Analysis
Streamlit multi-tab application.

Run with:
    streamlit run app.py

Tabs:
  1. Signature Verification    — Siamese network pair comparison
  2. Copy-Move Detection       — ORB+RANSAC / photoholmes
  3. Document Analysis         — ELA, edge detection, OCR, wavelet
"""

from __future__ import annotations

import io
import requests
import tempfile
from pathlib import Path

import numpy as np
import plotly.express as px
import streamlit as st
from PIL import Image

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Kavach AI — Enterprise Forensics",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for Premium SaaS UI ───────────────────────────────────────────
st.markdown("""
<style>
    /* Global Theme */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0a0a0a;
        color: #ededed;
        font-family: 'Inter', sans-serif;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: transparent !important;
        border: none !important;
        color: rgba(255, 255, 255, 0.4) !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-size: 12px !important;
    }
    .stTabs [aria-selected="true"] {
        color: #00FF9C !important;
        border-bottom: 2px solid #00FF9C !important;
    }

    /* Cards / Containers */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 24px !important;
        padding: 24px !important;
    }

    /* Buttons */
    .stButton > button {
        background: #00FF9C !important;
        color: black !important;
        font-weight: 900 !important;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        border-radius: 12px !important;
        border: none !important;
        padding: 12px 24px !important;
        transition: all 0.3s ease !important;
        width: 100%;
    }
    .stButton > button:hover {
        box-shadow: 0 0 25px rgba(0, 255, 156, 0.4) !important;
        transform: translateY(-2px);
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        font-weight: 900 !important;
        color: #00FF9C !important;
        letter-spacing: -0.05em;
    }
    [data-testid="stMetricLabel"] {
        text-transform: uppercase;
        font-size: 10px !important;
        font-weight: 700 !important;
        letter-spacing: 0.2em;
        color: rgba(255, 255, 255, 0.4) !important;
    }

    /* Headers */
    h1, h2, h3 {
        font-weight: 900 !important;
        letter-spacing: -0.02em !important;
    }
    .neon-text {
        color: #00FF9C;
        text-shadow: 0 0 10px rgba(0, 255, 156, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# ── Chatbot Sidebar ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<h1 class="neon-text">🛡️ KAVACH</h1>', unsafe_allow_html=True)
    st.caption("v2.0 ENTERPRISE PRO")
    st.markdown("---")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about fraud detection..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # Prepare context for the chatbot
            context = None
            if "last_analysis" in st.session_state:
                la = st.session_state.last_analysis
                context = {
                    "trust_score": la.get("trust_score", 0),
                    "risk": la.get("risk", "unknown"),
                    "findings": f"User is asking about their recent analysis which showed {la.get('risk')} risk."
                }

            # Call our FastAPI chat endpoint
            try:
                response = requests.post(
                    "http://localhost:8000/api/chat",
                    json={
                        "messages": st.session_state.messages,
                        "context": context
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    answer = response.json()["content"]
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                else:
                    st.error("Assistant is unavailable.")
            except Exception as e:
                st.error(f"Error: {e}")

    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

st.markdown('<h1 class="neon-text">KAVACH AI</h1>', unsafe_allow_html=True)
st.caption("ENTERPRISE DOCUMENT FORENSIC PIPELINE · V2.0 PRO")
st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "✍️  Signature Verification",
    "🔍  Copy-Move Detection",
    "📄  Document Analysis",
    "🛡️  IFAKE Forgery Analysis",
    "📦  Batch Analysis",
])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def calculate_risk(trust_score: int) -> str:
    if trust_score >= 80:
        return "Safe"
    elif trust_score >= 50:
        return "Medium"
    else:
        return "High"

def analyze_document(file_path: Path) -> dict:
    """Analyze a single document and return trust score and risk."""
    from src.analysis.ifake_tools import predict_ifake_forgery
    from src.analysis.ela import generate_ela, ela_score
    
    IFAKE_IMG_WEIGHTS = Path("weights/proposed_ela_50_casia_fidac.h5")
    
    # 1. Run IFAKE Analysis if weights exist
    if IFAKE_IMG_WEIGHTS.exists():
        res = predict_ifake_forgery(file_path, IFAKE_IMG_WEIGHTS)
        if "error" not in res:
            verdict = res["verdict"]
            confidence = res["confidence"]
            
            if verdict == "Authentic":
                trust_score = int(confidence * 100)
            else:
                trust_score = int((1 - confidence) * 100)
                
            return {
                "trust_score": trust_score,
                "risk": calculate_risk(trust_score)
            }
            
    # 2. Fallback to ELA
    try:
        ela_img = generate_ela(file_path)
        score = ela_score(ela_img)
        trust_score = max(0, min(100, int(100 - (score * 1000))))
        return {
            "trust_score": trust_score,
            "risk": calculate_risk(trust_score)
        }
    except Exception:
        return {"trust_score": 50, "risk": "Medium"}

def _save_upload(uploaded) -> Path:
    """Save a Streamlit UploadedFile to a temp file and return the path."""
    suffix = Path(uploaded.name).suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getbuffer())
        return Path(tmp.name)


# ─────────────────────────────────────────────────────────────────────────────
# UI Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ai_explanation_panel(explanations):
    """Render a clean structured AI explanation panel in Streamlit."""
    st.subheader("🧠 AI Explanation Engine")
    
    if not explanations:
        st.info("No detailed explanations available for this analysis.")
        return
        
    for exp in explanations:
        with st.container(border=True):
            col_icon, col_text = st.columns([0.1, 0.9])
            
            # Severity color and icon mapping
            severity = exp.get("severity", "low").lower()
            icon = "🚨" if severity == "high" else "⚠️" if severity == "medium" else "ℹ️"
            color = "#f8d7da" if severity == "high" else "#fff3cd" if severity == "medium" else "#e2e3e5"
            text_color = "#721c24" if severity == "high" else "#856404" if severity == "medium" else "#383d41"
            
            # Icon per type
            type_icon = {
                "tampering": "🛠️",
                "metadata": "📄",
                "text": "🔤",
                "template": "📏"
            }.get(exp.get("type"), "🔍")
            
            with col_icon:
                st.markdown(f"### {type_icon}")
                
            with col_text:
                st.markdown(f"**{exp.get('type', 'Analysis').capitalize()}**")
                st.markdown(f"{exp.get('message')}")
                
                # Severity and Confidence badges
                badge_html = f"""
                <div style="display: flex; gap: 8px; margin-top: 8px;">
                    <span style="background-color: {color}; color: {text_color}; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; text-transform: uppercase;">
                        {icon} {severity} severity
                    </span>
                    <span style="background-color: #cfe2ff; color: #084298; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: bold;">
                        Confidence: {exp.get('confidence', 0):.1%}
                    </span>
                </div>
                """
                st.markdown(badge_html, unsafe_allow_html=True)

def _verdict_badge(verdict: str) -> None:
    colours = {"Authentic": "🟢", "Genuine": "🟢", "Suspicious": "🟡", "Forged": "🔴"}
    icon = colours.get(verdict, "⚪")
    st.markdown(f"## {icon} {verdict}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Signature Verification
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.subheader("Offline Signature Verification")
    st.markdown(
        "Upload a **reference** (enrolled) signature and a **query** (candidate) signature. "
        "The Siamese network compares their embeddings and determines if they match."
    )

    col_ref, col_qry = st.columns(2)
    with col_ref:
        ref_file = st.file_uploader(
            "Reference signature", type=["png", "jpg", "jpeg"], key="sig_ref"
        )
        if ref_file:
            st.image(ref_file, caption="Reference", use_container_width=True)

    with col_qry:
        qry_file = st.file_uploader(
            "Query signature", type=["png", "jpg", "jpeg"], key="sig_qry"
        )
        if qry_file:
            st.image(qry_file, caption="Query", use_container_width=True)

    weights_path = st.text_input(
        "Model weights path", value="weights/siamese_best.pt",
        help="Run `python -m src.signature.train` to generate weights."
    )

    if st.button("🔎 Verify Signatures", disabled=not (ref_file and qry_file)):
        ref_path = _save_upload(ref_file)
        qry_path = _save_upload(qry_file)
        weights = Path(weights_path)

        if not weights.exists():
            st.warning(
                f"Weights file `{weights_path}` not found. "
                "Train the model first with:\n"
                "```\npython -m src.signature.train\n```"
            )
        else:
            with st.spinner("Running Siamese network..."):
                from src.signature.inference import verify
                result = verify(ref_path, qry_path, weights=weights)

            _verdict_badge(result["verdict"])
            m1, m2, m3 = st.columns(3)
            m1.metric("Confidence", f"{result['confidence']:.1%}")
            m2.metric("Cosine Distance", f"{result['distance']:.4f}")
            m3.metric("Match", "Yes ✓" if result["match"] else "No ✗")

    st.divider()
    with st.expander("ℹ️  About the model"):
        st.markdown("""
**Architecture**: Siamese Network with shared EfficientNet-B0 backbone (timm) +
projection head (Linear → BN → ReLU → Dropout → Linear).

**Training**: Contrastive loss (pytorch-metric-learning), AdamW optimiser,
CosineAnnealingLR scheduler. Default 30 epochs on CEDAR-style paired data.

**References**:
- HTCSigNet (Pattern Recognition, 2025) — Hybrid Transformer-Conv signature network
- Multi-Scale CNN-CrossViT (Complex & Intelligent Systems, 2025) — 98.85% on CEDAR
- TransOSV (Pattern Recognition, 2023) — First ViT-based writer-independent verification
        """)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Copy-Move Detection
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("Copy-Move Forgery Detection")
    st.markdown(
        "Upload a document image. The detector identifies regions that have been "
        "copied and pasted within the same image using ORB keypoint matching and "
        "RANSAC geometric verification."
    )

    img_file = st.file_uploader(
        "Document image", type=["png", "jpg", "jpeg", "tiff"], key="cm_img"
    )

    if img_file:
        img_pil = Image.open(img_file).convert("RGB")
        st.image(img_pil, caption="Uploaded image", use_container_width=True)

        if st.button("🔎 Detect Copy-Move"):
            img_path = _save_upload(img_file)
            with st.spinner("Running copy-move detector..."):
                from src.copy_move.detector import detect_copy_move
                from src.copy_move.visualizer import overlay_heatmap, annotate_regions

                result = detect_copy_move(img_path)

            _verdict_badge(result["verdict"])
            m1, m2 = st.columns(2)
            m1.metric("Forgery Score", f"{result['score']:.1%}")
            m2.metric("Detection Method", result["method"])

            st.subheader("Detection Results")
            c1, c2 = st.columns(2)
            with c1:
                mask = result["mask"]
                if mask.any():
                    overlay = overlay_heatmap(np.array(img_pil), mask, alpha=0.4)
                    st.image(overlay, caption="Heatmap overlay", use_container_width=True)
                else:
                    st.info("No significant copy-move regions detected.")

            with c2:
                if result["heatmap"] is not None:
                    st.image(result["heatmap"], caption="Photoholmes heatmap", use_container_width=True)
                elif mask.any():
                    annotated = annotate_regions(np.array(img_pil), mask)
                    st.image(annotated, caption="Annotated regions", use_container_width=True)

    st.divider()
    with st.expander("ℹ️  About the detector"):
        st.markdown("""
**Primary**: [PhotoHolmes](https://github.com/photoholmes/photoholmes) (Splicebuster) when installed.

**Fallback**: ORB feature extraction → BFMatcher → RANSAC homography estimation.
Inlier ratio determines the forgery confidence score.

**References**:
- CMFDFormer (arXiv 2311.13263, 2023): MiT transformer backbone for CMFD
- PhotoHolmes (arXiv 2412.14969, Springer 2025): unified forensics library
- MVSS-Net++ (T-PAMI): multi-view multi-scale supervision
        """)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — Document Analysis (ELA + Edge + OCR + Wavelet)
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("Document Analysis")
    st.markdown("Upload a document to run Error Level Analysis, edge detection, OCR, and wavelet decomposition.")

    doc_file = st.file_uploader(
        "Document image", type=["png", "jpg", "jpeg", "tiff", "bmp"], key="doc_img"
    )

    if doc_file:
        doc_pil = Image.open(doc_file).convert("RGB")
        st.image(doc_pil, caption="Uploaded document", use_container_width=True)

        analysis_options = st.multiselect(
            "Select analyses to run",
            ["Error Level Analysis (ELA)", "Edge Detection", "OCR", "Wavelet Decomposition"],
            default=["Error Level Analysis (ELA)", "Edge Detection"],
        )

        if st.button("▶ Run Analysis"):
            doc_path = _save_upload(doc_file)

            # ── ELA ───────────────────────────────────────────────────────────
            if "Error Level Analysis (ELA)" in analysis_options:
                st.subheader("Error Level Analysis")
                with st.spinner("Generating ELA map..."):
                    from src.analysis.ela import generate_ela, ela_score
                    ela_quality = st.session_state.get("ela_quality", 95)
                    ela_img = generate_ela(doc_pil, quality=ela_quality, scale=15)
                    score = ela_score(ela_img)

                c1, c2 = st.columns(2)
                with c1:
                    st.image(doc_pil, caption="Original", use_container_width=True)
                with c2:
                    st.image(ela_img, caption="ELA Map", use_container_width=True)

                verdict = "Forged" if score > 0.08 else ("Suspicious" if score > 0.03 else "Authentic")
                _verdict_badge(verdict)
                st.metric("ELA Intensity Score", f"{score:.4f}")
                st.caption(
                    "Bright regions in the ELA map indicate areas that may have been "
                    "digitally manipulated. Uniform texture suggests an authentic image."
                )

            # ── Edge Detection ─────────────────────────────────────────────────
            if "Edge Detection" in analysis_options:
                st.subheader("Edge Detection")
                detector = st.selectbox(
                    "Detector", ["canny", "sobel", "laplacian", "prewitt_x", "prewitt_y"],
                    key="edge_det",
                )
                with st.spinner("Running edge detection..."):
                    from src.analysis.edge_detection import detect_all
                    edges = detect_all(doc_pil)

                c1, c2 = st.columns(2)
                with c1:
                    st.image(doc_pil, caption="Original", use_container_width=True)
                with c2:
                    st.image(edges[detector], caption=f"{detector.capitalize()} edges", use_container_width=True)

            # ── OCR ───────────────────────────────────────────────────────────
            if "OCR" in analysis_options:
                st.subheader("Optical Character Recognition")
                handwritten = st.toggle("Handwritten text mode (uses TrOCR)", value=False, key="ocr_hw")
                with st.spinner("Extracting text..."):
                    from src.analysis.ocr import extract_text
                    ocr_result = extract_text(doc_path, handwritten=handwritten)

                st.text_area("Extracted text", ocr_result["full_text"], height=200)
                m1, m2 = st.columns(2)
                m1.metric("Avg. Confidence", f"{ocr_result['avg_confidence']:.1%}")
                m2.metric("Engine", ocr_result["engine"])

                if ocr_result["words"]:
                    with st.expander("Word-level results"):
                        import pandas as pd
                        df = pd.DataFrame([
                            {"Text": w["text"], "Confidence": f"{w['confidence']:.1%}"}
                            for w in ocr_result["words"]
                        ])
                        st.dataframe(df, use_container_width=True)

            # ── Wavelet ────────────────────────────────────────────────────────
            if "Wavelet Decomposition" in analysis_options:
                st.subheader("Wavelet Decomposition")
                col_w, col_l = st.columns(2)
                wavelet = col_w.selectbox("Wavelet", ["haar", "db1", "db4", "sym4"], key="wav_name")
                level = col_l.slider("Decomposition level", 1, 6, 3, key="wav_level")

                with st.spinner("Running wavelet decomposition..."):
                    from src.analysis.wavelet import decompose
                    wav_result = decompose(doc_pil, wavelet=wavelet, level=level)

                c1, c2 = st.columns(2)
                with c1:
                    st.image(doc_pil, caption="Original", use_container_width=True)
                with c2:
                    st.image(wav_result["heatmap"], caption=f"{wavelet} detail heatmap (level {level})", use_container_width=True)

    st.divider()
    with st.expander("ℹ️  ELA quality setting"):
        quality = st.slider(
            "JPEG re-compression quality", min_value=70, max_value=99, value=95,
            help="Lower quality amplifies differences in manipulated regions.",
            key="ela_quality",
        )

# ── TAB 4 — IFAKE Analysis ────────────────────────────────────────────────────
with tab4:
    st.markdown("""
    <div style="background: rgba(0, 255, 156, 0.05); border: 1px solid rgba(0, 255, 156, 0.1); border-radius: 16px; padding: 20px; margin-bottom: 32px;">
        <h3 style="margin: 0; color: #00FF9C;">IFAKE Neural Engine</h3>
        <p style="margin: 0; color: rgba(255, 255, 255, 0.6); font-size: 14px;">Deep learning classification using ELA-preprocessed feature maps.</p>
    </div>
    """, unsafe_allow_html=True)

    mode = st.radio("Select Input Mode", ["🖼️ Image Forgery", "🎥 Video Forgery"], horizontal=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if mode == "🖼️ Image Forgery":
        with st.container(border=True):
            if_file = st.file_uploader(
                "Upload document image for forensic scan", type=["png", "jpg", "jpeg", "tiff"], key="ifake_img"
            )
        
        if if_file:
            st.markdown("<br>", unsafe_allow_html=True)
            col_preview, col_settings = st.columns([0.7, 0.3])
            
            with col_preview:
                if_pil = Image.open(if_file).convert("RGB")
                st.image(if_pil, caption="Forensic Source", use_container_width=True)
            
            with col_settings:
                ifake_img_weights = st.text_input(
                    "Model Weights", value="weights/proposed_ela_50_casia_fidac.h5",
                    help="Target .h5 weights for the CNN classifier.",
                    key="ifake_img_weights_path"
                )
                st.markdown("<br>", unsafe_allow_html=True)
                run_btn = st.button("⚡ Run Forensic Scan", use_container_width=True)
            
            if run_btn:
                if_path = _save_upload(if_file)
                
                # ── CNN Analysis ──
                st.markdown("---")
                with st.spinner("Executing neural classification..."):
                    from src.analysis.ifake_tools import predict_ifake_forgery
                    res = predict_ifake_forgery(if_path, ifake_img_weights)
                
                if "error" in res:
                    st.error(f"Neural Engine Error: {res['error']}")
                else:
                    c1, c2 = st.columns([0.4, 0.6])
                    with c1:
                        st.markdown('<p style="text-transform: uppercase; font-size: 10px; font-weight: 900; letter-spacing: 0.2em; color: rgba(255,255,255,0.4);">Final Verdict</p>', unsafe_allow_html=True)
                        _verdict_badge(res["verdict"])
                    with c2:
                        st.metric("Neural Confidence", f"{res['confidence']:.1%}")
                    
                    if res.get("heatmap"):
                        st.markdown("<br>", unsafe_allow_html=True)
                        col_h, col_e = st.columns([0.6, 0.4])
                        
                        with col_h:
                            st.subheader("Forensic Heatmap")
                            st.image(
                                res["heatmap"], 
                                caption=f"Anomalies: {len(res.get('bboxes', []))} high-frequency regions detected.",
                                use_container_width=True
                            )
                        
                        with col_e:
                            _ai_explanation_panel(res.get("explanations", []))
                    elif res.get("explanations"):
                         _ai_explanation_panel(res["explanations"])
                
                # ── Noise & Luminance Analysis ──
                st.markdown("<br>", unsafe_allow_html=True)
                st.subheader("Signal Inconsistency Analysis")
                with st.spinner("Analyzing light and noise gradients..."):
                    from src.analysis.ifake_tools import luminance_gradient, noise_analysis
                    lum = luminance_gradient(if_path)
                    noise = noise_analysis(if_path)
                
                c1, c2 = st.columns(2)
                with c1:
                    with st.container(border=True):
                        st.image(lum, caption="Luminance Gradient (Lighting Inconsistency)", use_container_width=True)
                with c2:
                    with st.container(border=True):
                        st.image(noise, caption="Noise Variance (Surface Tampering)", use_container_width=True)

    else: # Video Forgery
        with st.container(border=True):
            vf_file = st.file_uploader(
                "Upload video for frame analysis", type=["mp4", "avi", "mov"], key="ifake_vid"
            )
        if vf_file:
            st.markdown("<br>", unsafe_allow_html=True)
            st.video(vf_file)
            
            ifake_vid_weights = st.text_input(
                "Video Model Weights", value="weights/forgery_model_me.hdf5",
                help="Target .hdf5 weights for the ResNet50 video classifier.",
                key="ifake_vid_weights_path"
            )
            
            if st.button("⚡ Analyze Temporal Frames", use_container_width=True):
                vf_path = _save_upload(vf_file)
                with st.spinner("Processing frame-by-frame temporal analysis..."):
                    from src.analysis.ifake_tools import detect_video_forgery
                    res = detect_video_forgery(vf_path, ifake_vid_weights)
                
                if "error" in res:
                    st.error(res["error"])
                else:
                    st.markdown("---")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        _verdict_badge(res["verdict"])
                    with c2:
                        st.metric("Tampered Frames", res["forged_frames"])
                    with c3:
                        st.metric("Total Frames", res["total_frames"])
                    
                    st.progress(res["forgery_ratio"])
                    st.caption(f"Forgery Ratio: {res['forgery_ratio']:.1%}")

    st.divider()
    with st.expander("ℹ️  About IFAKE integration"):
        st.markdown("""
**IFAKE (Image Forgery Analysis and Knowledge Extraction)** provides additional forensic tools:

1. **CNN Classification**: Uses a Convolutional Neural Network trained on the FIDAC & CASIA datasets. It analyzes ELA-preprocessed images to classify them as 'Authentic' or 'Forged'.
2. **Luminance Gradient**: Uses the Sobel operator to detect inconsistencies in lighting across the image.
3. **Noise Analysis**: Highlights differences between the original image and a re-saved version to surface high-frequency noise artefacts indicative of tampering.
4. **Video Forensics**: Performs frame-by-frame forgery classification to identify manipulated sequences in video files.
**Reference**: [Pawar et al. (2024). Image Forgery Detection and Classification Using Deep Learning and FIDAC Dataset. IEEE Explore.](https://github.com/shraddhavijay/IFAKE)
        """)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — Batch Analysis
# ─────────────────────────────────────────────────────────────────────────────
with tab5:
    st.markdown("""
    <div style="background: rgba(0, 255, 156, 0.05); border: 1px solid rgba(0, 255, 156, 0.1); border-radius: 16px; padding: 20px; margin-bottom: 32px;">
        <h3 style="margin: 0; color: #00FF9C;">Bulk Ingestion Hub</h3>
        <p style="margin: 0; color: rgba(255, 255, 255, 0.6); font-size: 14px;">High-volume analytic pipeline for enterprise document verification.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        batch_files = st.file_uploader(
            "Upload your documents (Drag & drop or click to browse)", 
            type=["png", "jpg", "jpeg", "pdf"], 
            accept_multiple_files=True,
            key="batch_uploader"
        )

    if batch_files:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⚡ Initiate Bulk Analysis", use_container_width=True):
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, uploaded_file in enumerate(batch_files):
                status_text.markdown(f"**Scanning Node {i+1}:** `{uploaded_file.name}`")
                file_path = _save_upload(uploaded_file)
                
                analysis = analyze_document(file_path)
                
                results.append({
                    "Document": uploaded_file.name,
                    "Integrity": f"{analysis['trust_score']}%",
                    "Risk Level": analysis["risk"],
                    "Status": "Verified"
                })
                progress_bar.progress((i + 1) / len(batch_files))

            status_text.success("Analytic pipeline complete. Results synchronized.")
            
            # Summary Section
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Load", len(results))
            with c2:
                st.metric("Integrity Verified", len([r for r in results if r["Risk Level"] == "Safe"]))
            with c3:
                st.metric("Threats Isolated", len([r for r in results if r["Risk Level"] == "High"]))

            # Results Table
            import pandas as pd
            df = pd.DataFrame(results)
            
            def style_risk(row):
                if row["Risk Level"] == "Safe":
                    return ["color: #00FF9C; font-weight: bold"] * len(row)
                elif row["Risk Level"] == "Medium":
                    return ["color: #fbbf24; font-weight: bold"] * len(row)
                elif row["Risk Level"] == "High":
                    return ["color: #f43f5e; font-weight: bold"] * len(row)
                return [""] * len(row)

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("Intelligence Feed")
            st.dataframe(
                df.style.apply(style_risk, axis=1),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.markdown("""
        <div style="text-align: center; padding: 100px 20px; opacity: 0.3;">
            <h1 style="font-size: 64px; margin: 0;">📦</h1>
            <p style="font-weight: 700; text-transform: uppercase; letter-spacing: 0.2em;">System Standby</p>
            <p style="font-size: 12px;">Waiting for document ingestion queue...</p>
        </div>
        """, unsafe_allow_html=True)

