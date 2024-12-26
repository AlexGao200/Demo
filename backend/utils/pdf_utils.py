"""
Utility functions for processing PDF files, including page extraction and image conversion.
"""

import fitz  # PyMuPDF
from PIL import Image
import io
import base64
from typing import List, Tuple
from loguru import logger
import asyncio


def extract_and_process_pdf_pages(
    file_path: str,
    target_width: int = 1568,
    target_height: int = 1568,
    zoom: float = 3.0,
) -> List[str]:
    """
    Extract pages from a PDF file, convert them to images, resize them to target dimensions,
    and encode them as base64 strings.

    Args:
        file_path: Path to the PDF file
        target_width: Target width for the resized images (default 1568 for Claude)
        target_height: Target height for the resized images (default 1568 for Claude)
        zoom: Zoom factor for initial PDF rendering (higher means better quality)

    Returns:
        List[str]: List of base64-encoded strings for each page image
    """
    try:
        pdf = fitz.open(file_path)
        base64_images = []

        # Initial rendering matrix with zoom
        mat = fitz.Matrix(zoom, zoom)

        for page_num in range(pdf.page_count):
            # Get the page
            page = pdf[page_num]

            # Render page to pixmap
            pix = page.get_pixmap(matrix=mat)

            # Convert pixmap to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Calculate aspect ratio preserving dimensions
            orig_width, orig_height = img.size
            aspect_ratio = orig_width / orig_height

            if aspect_ratio > 1:  # Wider than tall
                new_width = target_width
                new_height = int(target_width / aspect_ratio)
            else:  # Taller than wide
                new_height = target_height
                new_width = int(target_height * aspect_ratio)

            # Resize image preserving aspect ratio
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert to base64
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=85)  # Use JPEG with good quality
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            base64_images.append(img_base64)

        pdf.close()
        return base64_images

    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return []


def get_pdf_dimensions(file_path: str) -> List[Tuple[float, float]]:
    """
    Get the dimensions of each page in a PDF file.

    Args:
        file_path: Path to the PDF file

    Returns:
        List[Tuple[float, float]]: List of (width, height) tuples for each page
    """
    try:
        pdf = fitz.open(file_path)
        dimensions = []

        for page in pdf:
            rect = page.rect
            dimensions.append((rect.width, rect.height))

        pdf.close()
        return dimensions

    except Exception as e:
        print(f"Error getting PDF dimensions: {str(e)}")
        return []


async def process_page_to_image(
    page: fitz.Page,
    target_width: int,
    target_height: int,
    zoom: float,
) -> str:
    """
    Process a single PDF page to a base64 encoded image string.

    Args:
        page: PyMuPDF page object
        target_width: Target width for the resized image
        target_height: Target height for the resized image
        zoom: Zoom factor for initial PDF rendering

    Returns:
        str: Base64-encoded image string
    """
    try:
        # Create rendering matrix with zoom
        mat = fitz.Matrix(zoom, zoom)

        # Render page to pixmap
        pix = page.get_pixmap(matrix=mat)

        # Convert pixmap to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Calculate aspect ratio preserving dimensions
        orig_width, orig_height = img.size
        aspect_ratio = orig_width / orig_height

        if aspect_ratio > 1:  # Wider than tall
            new_width = target_width
            new_height = int(target_width / aspect_ratio)
        else:  # Taller than wide
            new_height = target_height
            new_width = int(target_height * aspect_ratio)

        # Resize image preserving aspect ratio
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Convert to base64
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)  # Use JPEG with good quality
        img_base64 = base64.b64encode(buffered.getvalue()).decode()

        return img_base64
    except Exception as e:
        logger.error(f"Error processing page to image: {str(e)}")
        return ""


async def async_extract_and_process_pdf_pages(
    file_path: str,
    target_width: int = 1568,
    target_height: int = 1568,
    zoom: float = 3.0,
) -> List[str]:
    """
    Extract pages from a PDF file, convert them to images, resize them to target dimensions,
    and encode them as base64 strings asynchronously.

    Args:
        file_path: Path to the PDF file
        target_width: Target width for the resized images (default 1568 for Claude)
        target_height: Target height for the resized images (default 1568 for Claude)
        zoom: Zoom factor for initial PDF rendering (higher means better quality)

    Returns:
        List[str]: List of base64-encoded strings for each page image
    """
    try:
        pdf = fitz.open(file_path)

        # Process all pages concurrently
        tasks = [
            process_page_to_image(pdf[page_num], target_width, target_height, zoom)
            for page_num in range(pdf.page_count)
        ]

        base64_images = await asyncio.gather(*tasks)

        # Filter out any failed conversions (empty strings)
        base64_images = [img for img in base64_images if img]

        pdf.close()
        return base64_images

    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        return []


async def async_get_pdf_dimensions(file_path: str) -> List[Tuple[float, float]]:
    """
    Get the dimensions of each page in a PDF file asynchronously.

    Args:
        file_path: Path to the PDF file

    Returns:
        List[Tuple[float, float]]: List of (width, height) tuples for each page
    """
    try:
        pdf = fitz.open(file_path)
        dimensions = []

        for page in pdf:
            rect = page.rect
            dimensions.append((rect.width, rect.height))

        pdf.close()
        return dimensions

    except Exception as e:
        logger.error(f"Error getting PDF dimensions: {str(e)}")
        return []
