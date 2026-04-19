"""
evidence_analyzer.py
Place this file at:  home/evidence_analyzer.py

Real-world evidence verification — NO paid external API required.
Uses:
  - PIL / Pillow  (already in most Django projects)
  - piexif        (pip install piexif)
  - numpy         (pip install numpy)

What it actually checks (and WHY each matters in a real police system):

1. EXIF metadata integrity
   AI-generated images (Midjourney, DALL-E, Stable Diffusion) typically have
   NO camera EXIF data, or suspiciously missing GPS/timestamp fields.
   Real phone photos always embed Make, Model, DateTime, sometimes GPS.

2. Colour channel noise variance
   Real photographs have natural sensor noise across R/G/B channels.
   AI images are suspiciously "clean" — very low per-channel variance.

3. Error Level Analysis (ELA)
   Save the image at a known JPEG quality, then diff it against original.
   Tampered/composited regions re-compress differently and glow bright in ELA.
   This is a standard forensic technique used by real labs.

4. Aspect ratio + resolution sanity
   Phones produce specific resolution ranges. A 512×512 or 1024×1024 image
   is a classic AI generator output size — a red flag for review.

5. Metadata software tag
   Many AI tools embed "Adobe Firefly", "DALL-E", "Stable Diffusion" etc.
   in the JPEG Software tag. We check for known strings.

The output is a VerificationResult dataclass — not a simple bool — so you
can store the per-signal detail and show it to the SHO for manual review.
"""

import io
import math
import struct
from dataclasses import dataclass, field
from typing import Optional

try:
    from PIL import Image, ImageChops, ImageEnhance
    import numpy as np
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import piexif
    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False


# ── Known AI software strings in EXIF ────────────────────────────────────────
AI_SOFTWARE_SIGNATURES = [
    "midjourney", "dall-e", "stable diffusion", "firefly", "nightcafe",
    "dreamstudio", "novelai", "bing image", "canva ai", "adobe generative",
    "fotor ai", "getimg", "runway", "pika", "sora",
]

# Classic AI generator output sizes (width, height) — both orientations
AI_TYPICAL_SIZES = {
    (512, 512), (768, 768), (1024, 1024), (1024, 768), (768, 1024),
    (1280, 720), (720, 1280), (1152, 896), (896, 1152),
    (2048, 2048), (1536, 1024), (1024, 1536),
}

# ── Result dataclass ──────────────────────────────────────────────────────────
@dataclass
class VerificationResult:
    is_suspicious: bool = False           # Final verdict
    confidence: float = 0.0              # 0.0 (clean) → 1.0 (definitely suspicious)
    flags: list = field(default_factory=list)   # Human-readable flag list
    detail: dict = field(default_factory=dict)  # Per-signal raw data for SHO view
    recommendation: str = "Manual review recommended"

    @property
    def status(self) -> str:
        if self.confidence < 0.25:
            return "Verified"
        elif self.confidence < 0.55:
            return "Review"   # SHO should manually check
        else:
            return "Flagged"

    @property
    def status_display(self) -> str:
        return {
            "Verified": "✅ Authentic — no manipulation signals detected",
            "Review":   "⚠️ Needs manual review — some anomalies found",
            "Flagged":  "🚨 Likely AI-generated or tampered — block submission",
        }[self.status]


# ── Main analyser ─────────────────────────────────────────────────────────────
def analyze_image(image_file) -> VerificationResult:
    """
    Analyse a Django InMemoryUploadedFile or any file-like object.
    Returns a VerificationResult.
    """
    result = VerificationResult()

    if not PIL_AVAILABLE:
        result.flags.append("PIL not installed — skipping visual analysis")
        result.recommendation = "Install Pillow and numpy for AI detection."
        return result

    try:
        image_file.seek(0)
        raw_bytes = image_file.read()
        image_file.seek(0)

        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        width, height = img.size
        result.detail["dimensions"] = f"{width}×{height}"

        score = 0.0  # accumulate suspicion score

        # ── Signal 1: EXIF presence ───────────────────────────────────────────
        exif_data = img._getexif() if hasattr(img, "_getexif") else None
        has_exif = bool(exif_data)
        result.detail["has_exif"] = has_exif

        if not has_exif:
            score += 0.25
            result.flags.append("No EXIF metadata — real phone photos always have this")
        else:
            # Check for camera make/model (tags 271, 272)
            make  = exif_data.get(271, "")
            model = exif_data.get(272, "")
            software = str(exif_data.get(305, "")).lower()
            datetime_tag = exif_data.get(306, "")

            result.detail["camera_make"]  = make  or "missing"
            result.detail["camera_model"] = model or "missing"
            result.detail["software"]     = software or "missing"
            result.detail["datetime"]     = str(datetime_tag) or "missing"

            if not make and not model:
                score += 0.15
                result.flags.append("Camera make/model absent — unusual for device photos")

            if not datetime_tag:
                score += 0.10
                result.flags.append("Photo timestamp missing from EXIF")

            # Check known AI software strings
            for sig in AI_SOFTWARE_SIGNATURES:
                if sig in software:
                    score += 0.50
                    result.flags.append(f"AI software detected in EXIF: '{software}'")
                    break

        # ── Signal 2: Typical AI generator resolution ─────────────────────────
        if (width, height) in AI_TYPICAL_SIZES:
            score += 0.20
            result.flags.append(f"Resolution {width}×{height} matches common AI generator output")

        # ── Signal 3: Colour channel noise variance ───────────────────────────
        arr = np.array(img, dtype=np.float32)
        channel_vars = [float(np.var(arr[:, :, c])) for c in range(3)]
        avg_var = sum(channel_vars) / 3
        result.detail["channel_variance"] = round(avg_var, 2)

        # Real photos typically have variance > 800 (lots of sensor noise + detail)
        # AI images are often very smooth: variance < 300
        if avg_var < 300:
            score += 0.25
            result.flags.append(
                f"Unusually low colour variance ({avg_var:.0f}) — AI images are typically too smooth"
            )
        elif avg_var < 600:
            score += 0.10
            result.flags.append(f"Moderately low colour variance ({avg_var:.0f})")

        # ── Signal 4: Error Level Analysis (ELA) ─────────────────────────────
        ela_score = _compute_ela_score(img, raw_bytes)
        result.detail["ela_score"] = round(ela_score, 4)

        if ela_score > 0.08:
            score += 0.25
            result.flags.append(
                f"ELA analysis ({ela_score:.3f}) suggests image tampering or compositing"
            )
        elif ela_score > 0.05:
            score += 0.10
            result.flags.append(f"ELA shows minor inconsistencies ({ela_score:.3f})")

        # ── Signal 5: File size vs resolution ratio ───────────────────────────
        file_size_kb = len(raw_bytes) / 1024
        pixels = width * height
        bytes_per_pixel = file_size_kb * 1024 / pixels if pixels else 0
        result.detail["bytes_per_pixel"] = round(bytes_per_pixel, 4)

        # AI images compressed from generation are abnormally small per pixel
        if bytes_per_pixel < 0.08:
            score += 0.10
            result.flags.append(
                f"Very low file size per pixel ({bytes_per_pixel:.3f}) — may indicate AI compression"
            )

        # ── Final scoring ─────────────────────────────────────────────────────
        result.confidence = min(score, 1.0)
        result.is_suspicious = result.confidence >= 0.40

        if result.confidence < 0.25:
            result.recommendation = "Image appears authentic. Proceed with report."
        elif result.confidence < 0.55:
            result.recommendation = (
                "Some anomalies detected. SHO should manually inspect this image "
                "before approving the report."
            )
        else:
            result.recommendation = (
                "Strong indicators of AI generation or tampering. "
                "Reject submission and ask citizen for original device photos."
            )

        result.detail["signals_checked"] = 5
        result.detail["flags_raised"] = len(result.flags)

    except Exception as e:
        result.flags.append(f"Analysis error: {str(e)}")
        result.recommendation = "Could not analyse image — manual review required."

    return result


def _compute_ela_score(img: "Image.Image", raw_bytes: bytes) -> float:
    """
    Error Level Analysis: save at 75% quality, diff against original.
    High mean diff → potential tampering.
    """
    try:
        # Re-save at lower quality
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        buf.seek(0)
        recompressed = Image.open(buf).convert("RGB")

        # Pixel-wise absolute difference
        diff = ImageChops.difference(img, recompressed)
        # Enhance to amplify small differences
        diff_enhanced = ImageEnhance.Brightness(diff).enhance(10)
        arr = np.array(diff_enhanced, dtype=np.float32)
        return float(np.mean(arr)) / 255.0
    except Exception:
        return 0.0


# ── Video basic check ─────────────────────────────────────────────────────────
def analyze_video_basic(video_file) -> dict:
    """
    Basic video sanity check — no deepfake ML model needed.
    Checks file size, extension, and reads first few bytes for valid MP4/MOV magic bytes.
    """
    result = {"ok": True, "flags": [], "recommendation": "Video accepted for manual review by SHO."}

    MAX_SIZE_MB = 50
    size_mb = video_file.size / (1024 * 1024)

    if size_mb > MAX_SIZE_MB:
        result["ok"] = False
        result["flags"].append(f"File too large ({size_mb:.1f} MB). Max is {MAX_SIZE_MB} MB.")
        return result

    # Check magic bytes for MP4 / MOV / AVI
    video_file.seek(0)
    header = video_file.read(12)
    video_file.seek(0)

    VALID_SIGNATURES = [
        b"ftyp",         # MP4/MOV at offset 4
        b"\x00\x00\x00", # common MP4 box start
        b"RIFF",          # AVI
    ]
    valid = any(sig in header for sig in VALID_SIGNATURES) or (len(header) >= 8 and header[4:8] == b"ftyp")

    if not valid:
        result["ok"] = False
        result["flags"].append("File does not appear to be a valid video (invalid file signature).")

    allowed_exts = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
    name = getattr(video_file, "name", "").lower()
    if not any(name.endswith(ext) for ext in allowed_exts):
        result["flags"].append(f"Unusual file extension: {name.split('.')[-1]}")

    result["size_mb"] = round(size_mb, 2)
    return result
