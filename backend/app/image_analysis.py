"""Image analysis service for JARVIS - OCR, object detection, and metadata extraction."""

from __future__ import annotations

import logging
from typing import Optional

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger("jarvis.image_analysis")


class ImageAnalysisService:
    """Handles image analysis operations including OCR and object detection."""

    def __init__(self):
        self.ocr_available = False
        self._check_ocr_availability()

    def _check_ocr_availability(self):
        """Check if Tesseract OCR is available."""
        try:
            import pytesseract
            # Try to get version to verify it's working
            pytesseract.get_tesseract_version()
            self.ocr_available = True
            logger.info("Tesseract OCR is available")
        except Exception as e:
            logger.warning(f"Tesseract OCR not available: {e}")
            self.ocr_available = False

    def perform_ocr(self, image: Image.Image, lang: str = "eng") -> dict:
        """Perform OCR on an image to extract text."""
        if not self.ocr_available:
            return {
                "success": False,
                "error": "Tesseract OCR not installed. Install with: pip install pytesseract and download Tesseract-OCR from https://github.com/UB-Mannheim/tesseract/wiki",
            }

        try:
            import pytesseract

            # Convert PIL Image to format expected by pytesseract
            text = pytesseract.image_to_string(image, lang=lang)

            # Get detailed data
            data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)

            # Extract words with confidence
            words = []
            for i in range(len(data["text"])):
                if data["text"][i].strip():
                    words.append(
                        {
                            "text": data["text"][i],
                            "confidence": data["conf"][i],
                            "x": data["left"][i],
                            "y": data["top"][i],
                            "width": data["width"][i],
                            "height": data["height"][i],
                        }
                    )

            return {
                "success": True,
                "text": text.strip(),
                "words": words,
                "word_count": len(words),
                "language": lang,
            }
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return {"success": False, "error": str(e)}

    def detect_edges(self, image: Image.Image) -> dict:
        """Detect edges in an image using Canny edge detection."""
        try:
            # Convert to OpenCV format
            img_cv = self._pil_to_cv2(image)

            # Convert to grayscale
            gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)

            # Apply Canny edge detection
            edges = cv2.Canny(gray, 100, 200)

            # Convert back to PIL
            edges_pil = Image.fromarray(edges)

            # Count edges
            edge_pixels = np.sum(edges > 0)
            total_pixels = edges.size
            edge_percentage = (edge_pixels / total_pixels) * 100

            return {
                "success": True,
                "edges_image": edges_pil,
                "edge_pixels": int(edge_pixels),
                "total_pixels": int(total_pixels),
                "edge_percentage": float(edge_percentage),
            }
        except Exception as e:
            logger.error(f"Edge detection failed: {e}")
            return {"success": False, "error": str(e)}

    def detect_shapes(self, image: Image.Image) -> dict:
        """Detect basic shapes (circles, rectangles, lines) in an image."""
        try:
            img_cv = self._pil_to_cv2(image)
            gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            shapes = []

            # Detect circles
            circles = cv2.HoughCircles(
                blurred,
                cv2.HOUGH_GRADIENT,
                dp=1.2,
                minDist=50,
                param1=100,
                param2=30,
                minRadius=10,
                maxRadius=200,
            )

            if circles is not None:
                circles = np.round(circles[0]).astype("int")
                for circle in circles:
                    shapes.append(
                        {
                            "type": "circle",
                            "x": int(circle[0]),
                            "y": int(circle[1]),
                            "radius": int(circle[2]),
                        }
                    )

            # Detect rectangles/contours
            edges = cv2.Canny(blurred, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                # Approximate contour
                peri = cv2.contourPerimeter(contour)
                approx = cv2.approxPolyDP(contour, 0.04 * peri, True)

                # If approx has 4 points, it's likely a rectangle
                if len(approx) == 4:
                    x, y, w, h = cv2.boundingRect(approx)
                    aspect_ratio = float(w) / h
                    if 0.8 <= aspect_ratio <= 1.2:
                        shapes.append(
                            {
                                "type": "square",
                                "x": x,
                                "y": y,
                                "width": w,
                                "height": h,
                            }
                        )
                    else:
                        shapes.append(
                            {
                                "type": "rectangle",
                                "x": x,
                                "y": y,
                                "width": w,
                                "height": h,
                            }
                        )

            return {
                "success": True,
                "shapes": shapes,
                "shape_count": len(shapes),
            }
        except Exception as e:
            logger.error(f"Shape detection failed: {e}")
            return {"success": False, "error": str(e)}

    def analyze_colors(self, image: Image.Image) -> dict:
        """Analyze dominant colors in an image."""
        try:
            img_cv = self._pil_to_cv2(image)

            # Convert to HSV for better color analysis
            hsv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2HSV)

            # Reshape for k-means
            pixels = hsv.reshape((-1, 3))
            pixels = np.float32(pixels)

            # Define criteria and apply k-means
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
            k = 5  # Number of dominant colors
            _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

            # Count pixels for each color
            unique_labels, counts = np.unique(labels, return_counts=True)
            total_pixels = len(labels)

            dominant_colors = []
            for i, count in enumerate(counts):
                # Convert HSV back to RGB
                hsv_color = np.uint8([[centers[i]]])
                rgb_color = cv2.cvtColor(hsv_color, cv2.COLOR_HSV2RGB)[0][0]

                percentage = (count / total_pixels) * 100
                dominant_colors.append(
                    {
                        "rgb": [int(rgb_color[0]), int(rgb_color[1]), int(rgb_color[2])],
                        "hex": "#{:02x}{:02x}{:02x}".format(
                            int(rgb_color[0]), int(rgb_color[1]), int(rgb_color[2])
                        ),
                        "percentage": float(percentage),
                    }
                )

            # Sort by percentage
            dominant_colors.sort(key=lambda x: x["percentage"], reverse=True)

            return {
                "success": True,
                "dominant_colors": dominant_colors,
                "color_count": len(dominant_colors),
            }
        except Exception as e:
            logger.error(f"Color analysis failed: {e}")
            return {"success": False, "error": str(e)}

    def detect_faces(self, image: Image.Image) -> dict:
        """Detect faces in an image using OpenCV's Haar cascades."""
        try:
            img_cv = self._pil_to_cv2(image)
            gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)

            # Load face cascade
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            face_cascade = cv2.CascadeClassifier(cascade_path)

            # Detect faces
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            face_list = []
            for x, y, w, h in faces:
                face_list.append(
                    {
                        "x": int(x),
                        "y": int(y),
                        "width": int(w),
                        "height": int(h),
                    }
                )

            return {
                "success": True,
                "faces": face_list,
                "face_count": len(face_list),
            }
        except Exception as e:
            logger.error(f"Face detection failed: {e}")
            return {"success": False, "error": str(e)}

    def get_image_statistics(self, image: Image.Image) -> dict:
        """Get statistical information about an image."""
        try:
            img_cv = self._pil_to_cv2(image)

            # Calculate basic statistics
            mean = np.mean(img_cv, axis=(0, 1))
            std = np.std(img_cv, axis=(0, 1))
            min_val = np.min(img_cv, axis=(0, 1))
            max_val = np.max(img_cv, axis=(0, 1))

            # Calculate histogram for each channel
            histograms = []
            for i in range(img_cv.shape[2]):
                hist = cv2.calcHist([img_cv], [i], None, [256], [0, 256])
                hist = hist.flatten() / np.sum(hist)  # Normalize
                histograms.append(hist.tolist())

            return {
                "success": True,
                "width": image.width,
                "height": image.height,
                "channels": img_cv.shape[2],
                "mean": mean.tolist(),
                "std": std.tolist(),
                "min": min_val.tolist(),
                "max": max_val.tolist(),
                "histograms": histograms,
            }
        except Exception as e:
            logger.error(f"Image statistics failed: {e}")
            return {"success": False, "error": str(e)}

    def _pil_to_cv2(self, image: Image.Image) -> np.ndarray:
        """Convert PIL Image to OpenCV format."""
        if image.mode != "RGB":
            image = image.convert("RGB")
        return np.array(image)

    def _cv2_to_pil(self, img_cv: np.ndarray) -> Image.Image:
        """Convert OpenCV format to PIL Image."""
        if len(img_cv.shape) == 2:
            return Image.fromarray(img_cv)
        return Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))


# Global instance
image_analysis_service = ImageAnalysisService()
