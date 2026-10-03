import io
import hashlib
from typing import Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont

ALLOWED_IMAGE_MIMES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
    "image/jpg": "JPEG"
}

def compute_dhash(image: Image.Image, hash_size: int = 8) -> str:
    """
    Computes difference hash (dHash) for perceptual similarity and duplicate detection.
    """
    # Resize to (hash_size + 1, hash_size) in grayscale
    resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(resized.getdata())
    
    # Compare adjacent pixels
    difference = []
    for row in range(hash_size):
        for col in range(hash_size):
            pixel_left = resized.getpixel((col, row))
            pixel_right = resized.getpixel((col + 1, row))
            difference.append(pixel_left > pixel_right)
            
    # Convert bool list to hex string
    decimal_value = 0
    hex_string = []
    for index, value in enumerate(difference):
        if value:
            decimal_value += 2 ** (index % 4)
        if (index % 4) == 3:
            hex_string.append(hex(decimal_value)[2:])
            decimal_value = 0
    return "".join(hex_string)

def process_image(file_bytes: bytes, max_size_bytes: int = 15 * 1024 * 1024) -> Dict[str, Any]:
    """
    Runs all pre-checks on an uploaded image:
    - Verifies real MIME & integrity
    - Checks file size & dimensions
    - Computes pHash & content SHA256
    - Strips EXIF metadata
    - Generates a safe, watermarked downscaled preview
    """
    if len(file_bytes) > max_size_bytes:
        raise ValueError(f"Image exceeds maximum size of {max_size_bytes // (1024 * 1024)}MB")

    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.verify()  # verify integrity
        # Re-open after verify() as verify alters file pointer
        image = Image.open(io.BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"Invalid or corrupted image file: {str(e)}")

    format_name = image.format.upper() if image.format else ""
    mime_type = f"image/{format_name.lower()}"
    if mime_type == "image/jpg":
        mime_type = "image/jpeg"
        
    if mime_type not in ALLOWED_IMAGE_MIMES:
        raise ValueError(f"Unsupported image format: {format_name}. Allowed: JPEG, PNG, WEBP")

    width, height = image.size
    if width < 32 or height < 32:
        raise ValueError(f"Image resolution {width}x{height} is too small. Minimum resolution is 32x32")

    # Content SHA256 and pHash
    content_hash = hashlib.sha256(file_bytes).hexdigest()
    phash = compute_dhash(image)

    # Check EXIF
    has_exif = hasattr(image, "_getexif") and image._getexif() is not None

    # Generate Safe Preview: Downscaled, EXIF-stripped, Watermarked
    preview_bytes = generate_image_preview(image)

    return {
        "mime": mime_type,
        "width": width,
        "height": height,
        "size": len(file_bytes),
        "phash": phash,
        "content_hash": content_hash,
        "exif_stripped": has_exif,
        "preview_bytes": preview_bytes,
        "preview_mime": "image/jpeg"
    }

def generate_image_preview(image: Image.Image, max_dim: int = 600) -> bytes:
    """
    Downscales image and creates a safe preview without EXIF data.
    """
    # Convert RGBA/P to RGB for JPEG preview
    if image.mode in ("RGBA", "P", "LA"):
        preview_img = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode == "P":
            preview_img.paste(image.convert("RGBA"), mask=image.convert("RGBA").split()[3])
        else:
            preview_img.paste(image, mask=image.split()[3] if len(image.split()) == 4 else None)
    else:
        preview_img = image.convert("RGB")

    # Downscale if larger than max_dim
    preview_img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    # Add Subtle Watermark
    draw = ImageDraw.Draw(preview_img)
    w, h = preview_img.size
    watermark_text = "REACT N DATA PREVIEW"
    # Draw simple watermark in bottom corner
    draw.text((15, h - 25), watermark_text, fill=(200, 200, 200))

    # Save to buffer (this automatically strips EXIF as we created a fresh Image)
    out_buf = io.BytesIO()
    preview_img.save(out_buf, format="JPEG", quality=80, optimize=True)
    return out_buf.getvalue()
