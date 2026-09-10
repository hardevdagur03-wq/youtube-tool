"""Image Optimizer — compresses and generates responsive image variants.

Optimizes images for web delivery: compression, responsive sizes,
format conversion (WebP), and placeholder generation.
Target: 50% size reduction without visible quality loss.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from export_delivery.config import ExportDeliveryConfig

logger = logging.getLogger(__name__)


class ImageOptimizer:
    """Optimizes images for export delivery.

    Provides compression, responsive variants, format conversion,
    and placeholder generation. Falls back gracefully when
    PIL/Pillow is not available.
    """

    def __init__(self, config: ExportDeliveryConfig | None = None) -> None:
        self._config = config or ExportDeliveryConfig.from_env()
        self._has_pil = False
        try:
            from PIL import Image
            self._has_pil = True
        except ImportError:
            pass

    def optimize(
        self, input_path: str, output_path: str | None = None,
        quality: int | None = None, max_width: int | None = None,
    ) -> dict[str, Any]:
        """Optimize a single image: compress and resize.

        Args:
            input_path: Source image path.
            output_path: Output path (default: overwrite input).
            quality: JPEG/WebP quality (1-100, default: 85).
            max_width: Maximum width in pixels (default: 1920).

        Returns:
            Dict with optimization results.
        """
        if not self._has_pil:
            logger.warning("Pillow not available, cannot optimize images")
            return {"success": False, "error": "Pillow not installed"}

        if not os.path.isfile(input_path):
            return {"success": False, "error": f"File not found: {input_path}"}

        from PIL import Image

        output_path = output_path or input_path
        quality = quality or self._config.image_quality
        max_width = max_width or self._config.image_max_width
        original_size = os.path.getsize(input_path)

        try:
            img = Image.open(input_path)
            orig_format = img.format or "JPEG"
            orig_width, orig_height = img.size

            # Resize if wider than max_width
            if orig_width > max_width:
                ratio = max_width / orig_width
                new_size = (max_width, int(orig_height * ratio))
                img = img.resize(new_size, Image.LANCZOS)

            # Convert RGBA to RGB for JPEG
            if img.mode == "RGBA" and output_path.lower().endswith((".jpg", ".jpeg")):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img = bg

            # Save optimized
            save_kwargs = {"quality": quality, "optimize": True}
            if output_path.lower().endswith(".webp"):
                save_kwargs["method"] = 6

            img.save(output_path, **save_kwargs)

            new_size = os.path.getsize(output_path)
            savings_pct = round((1 - new_size / max(original_size, 1)) * 100, 1)

            logger.info(
                "Image optimized: %s (%.1f KB → %.1f KB, %.0f%% savings)",
                os.path.basename(input_path),
                original_size / 1024, new_size / 1024, savings_pct,
            )

            return {
                "success": True,
                "original_size": original_size,
                "new_size": new_size,
                "savings_bytes": original_size - new_size,
                "savings_pct": savings_pct,
                "original_dimensions": (orig_width, orig_height),
                "new_dimensions": img.size,
            }

        except Exception as exc:
            logger.warning("Image optimization failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def generate_responsive(
        self, input_path: str, output_dir: str,
        widths: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate responsive image variants at specified widths.

        Args:
            input_path: Source image path.
            output_dir: Output directory for variants.
            widths: List of widths in pixels.

        Returns:
            List of variant info dicts.
        """
        if not self._has_pil:
            return []

        from PIL import Image

        widths = widths or self._config.image_responsive_widths
        variants = []
        base_name = os.path.splitext(os.path.basename(input_path))[0]

        try:
            img = Image.open(input_path)
            orig_width = img.width

            for target_width in widths:
                if target_width >= orig_width:
                    continue
                ratio = target_width / orig_width
                new_height = int(img.height * ratio)
                resized = img.resize((target_width, new_height), Image.LANCZOS)

                variant_name = f"{base_name}-{target_width}w.webp"
                variant_path = os.path.join(output_dir, variant_name)
                resized.save(variant_path, "WEBP", quality=85, method=6)

                variants.append({
                    "width": target_width,
                    "filename": variant_name,
                    "filepath": variant_path,
                    "size_bytes": os.path.getsize(variant_path),
                })

            logger.info(
                "Generated %d responsive variants for %s",
                len(variants), base_name,
            )

        except Exception as exc:
            logger.warning("Responsive generation failed: %s", exc)

        return variants

    def convert_to_webp(
        self, input_path: str, output_path: str | None = None,
        quality: int | None = None,
    ) -> dict[str, Any]:
        """Convert an image to WebP format.

        Args:
            input_path: Source image path.
            output_path: Output path (default: same name with .webp).
            quality: WebP quality (default: 85).

        Returns:
            Dict with conversion results.
        """
        if not self._has_pil:
            return {"success": False, "error": "Pillow not installed"}

        from PIL import Image

        output_path = output_path or os.path.splitext(input_path)[0] + ".webp"
        quality = quality or self._config.image_quality
        original_size = os.path.getsize(input_path)

        try:
            img = Image.open(input_path)
            # Handle RGBA for WebP (supports transparency)
            img.save(output_path, "WEBP", quality=quality, method=6)
            new_size = os.path.getsize(output_path)
            savings_pct = round((1 - new_size / max(original_size, 1)) * 100, 1)

            return {
                "success": True,
                "original_size": original_size,
                "new_size": new_size,
                "savings_pct": savings_pct,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def generate_placeholder(
        self, input_path: str, output_path: str | None = None,
        size: int = 20,
    ) -> dict[str, Any]:
        """Generate a tiny blurred placeholder image.

        Args:
            input_path: Source image path.
            output_path: Output path for placeholder.
            size: Placeholder size in pixels (default: 20).

        Returns:
            Dict with placeholder info.
        """
        if not self._has_pil:
            return {"success": False, "error": "Pillow not installed"}

        from PIL import Image, ImageFilter

        output_path = output_path or os.path.join(
            os.path.dirname(input_path),
            f"placeholder-{os.path.basename(input_path)}",
        )

        try:
            img = Image.open(input_path)
            img.thumbnail((size, size), Image.LANCZOS)
            img.save(output_path, "WEBP", quality=30)

            return {
                "success": True,
                "filename": os.path.basename(output_path),
                "filepath": output_path,
                "size_bytes": os.path.getsize(output_path),
                "dimensions": img.size,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}
