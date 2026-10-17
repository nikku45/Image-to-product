import io
from dataclasses import dataclass
from typing import Optional, Set
from PIL import Image, ImageOps, UnidentifiedImageError

from app.exceptions import ImageValidationError

# Supported formats and signatures
SUPPORTED_MIME_TYPES: Set[str] = {"image/jpeg", "image/png", "image/webp"}
SUPPORTED_FORMATS: Set[str] = {"JPEG", "PNG", "WEBP"}
MAX_DIMENSION: int = 2048  # Maximum width/height to prevent resource exhaustion


@dataclass
class ValidatedImage:
    """Represents a validated, sanitized, and normalized image buffer."""
    data: bytes
    format: str  # "JPEG", "PNG", or "WEBP"
    mime_type: str
    width: int
    height: int
    original_filename: str


def verify_image_signature(header: bytes) -> str:
    """
    Check the file signature (magic bytes) to verify it is authentic JPEG, PNG, or WebP.
    Does not rely on client-supplied extensions.
    """
    if len(header) < 12:
        raise ImageValidationError("File is too small to be a valid image")

    # JPEG signature: FF D8 FF
    if header.startswith(b"\xff\xd8\xff"):
        return "JPEG"

    # PNG signature: 89 50 4E 47 0D 0A 1A 0A
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"

    # WebP signature: RIFF....WEBP
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "WEBP"

    raise ImageValidationError(
        "Unsupported image format. Allowed formats are JPEG, PNG, and WebP."
    )


def validate_and_preprocess_image(
    file_bytes: bytes,
    original_filename: str = "upload.jpg",
    max_size_bytes: int = 10 * 1024 * 1024,
) -> ValidatedImage:
    """
    Validate, normalize, and strip metadata from an uploaded image.
    
    1. Check byte length against size limit.
    2. Validate file signature magic bytes.
    3. Decode image with Pillow to ensure byte integrity.
    4. Normalize EXIF orientation (transpose).
    5. Resize if oversized while preserving aspect ratio.
    6. Strip non-essential EXIF metadata to ensure privacy.
    """
    if not file_bytes:
        raise ImageValidationError("Uploaded image is empty")

    if len(file_bytes) > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise ImageValidationError(
            f"Image exceeds the maximum allowed size of {max_mb:.1f}MB"
        )

    # Verify signature
    detected_format = verify_image_signature(file_bytes[:16])

    # Decode and verify with Pillow
    try:
        img_buffer = io.BytesIO(file_bytes)
        with Image.open(img_buffer) as img:
            # Verify actual image content
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError) as e:
        raise ImageValidationError(f"Image is corrupted or cannot be decoded: {str(e)}")

    # Re-open for transformation (verify closes the image stream)
    try:
        img_buffer.seek(0)
        with Image.open(img_buffer) as img:
            actual_format = img.format
            if actual_format not in SUPPORTED_FORMATS:
                raise ImageValidationError(
                    f"Unsupported image format '{actual_format}'. Allowed: JPEG, PNG, WebP."
                )

            # Normalize orientation from EXIF transposition
            transposed_img = ImageOps.exif_transpose(img)
            if transposed_img is None:
                transposed_img = img

            # Downsample if dimensions exceed MAX_DIMENSION
            orig_w, orig_h = transposed_img.size
            if orig_w > MAX_DIMENSION or orig_h > MAX_DIMENSION:
                transposed_img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

            # Strip EXIF metadata by re-encoding to a clean buffer
            output_buffer = io.BytesIO()
            save_format = actual_format if actual_format in {"PNG", "WEBP"} else "JPEG"
            
            # Handle color modes
            if save_format == "JPEG" and transposed_img.mode in ("RGBA", "P"):
                clean_img = transposed_img.convert("RGB")
            else:
                clean_img = transposed_img

            clean_img.save(
                output_buffer,
                format=save_format,
                quality=92 if save_format in {"JPEG", "WEBP"} else None,
                optimize=True,
            )
            sanitized_bytes = output_buffer.getvalue()

            mime_map = {
                "JPEG": "image/jpeg",
                "PNG": "image/png",
                "WEBP": "image/webp",
            }

            return ValidatedImage(
                data=sanitized_bytes,
                format=save_format,
                mime_type=mime_map.get(save_format, "image/jpeg"),
                width=clean_img.width,
                height=clean_img.height,
                original_filename=original_filename,
            )

    except ImageValidationError:
        raise
    except Exception as e:
        raise ImageValidationError(f"Failed to process image: {str(e)}")
