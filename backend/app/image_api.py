"""Image processing API endpoints for JARVIS."""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
import base64
import io

from app.image_service import image_service
from app.image_analysis import image_analysis_service

router = APIRouter(prefix="/api/images", tags=["images"])


class ImageEditRequest(BaseModel):
    operation: str
    params: dict = {}


class ImageSaveRequest(BaseModel):
    path: str
    format: Optional[str] = None


class ImageResizeRequest(BaseModel):
    width: int
    height: int
    maintain_aspect: bool = True


class ImageCropRequest(BaseModel):
    left: int
    top: int
    right: int
    bottom: int


class ImageRotateRequest(BaseModel):
    angle: float
    expand: bool = True


class ImageFilterRequest(BaseModel):
    filter_name: str


class ImageAdjustRequest(BaseModel):
    factor: float


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """Upload an image for processing."""
    try:
        contents = await file.read()
        base64_data = base64.b64encode(contents).decode("utf-8")
        result = image_service.load_image_from_base64(base64_data)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load")
async def load_image(path: str):
    """Load an image from file path."""
    result = image_service.load_image(path)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/info")
async def get_image_info():
    """Get information about the current image."""
    return image_service.get_image_info()


@router.get("/preview")
async def get_image_preview(format: str = "PNG"):
    """Get current image as base64 for preview."""
    result = image_service.get_image_as_base64(format)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/save")
async def save_image(req: ImageSaveRequest):
    """Save the current image to a file."""
    result = image_service.save_image(req.path, req.format)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/resize")
async def resize_image(req: ImageResizeRequest):
    """Resize the current image."""
    result = image_service.resize(req.width, req.height, req.maintain_aspect)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/crop")
async def crop_image(req: ImageCropRequest):
    """Crop the current image."""
    result = image_service.crop(req.left, req.top, req.right, req.bottom)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/rotate")
async def rotate_image(req: ImageRotateRequest):
    """Rotate the current image."""
    result = image_service.rotate(req.angle, req.expand)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/filter")
async def apply_filter(req: ImageFilterRequest):
    """Apply a filter to the current image."""
    result = image_service.apply_filter(req.filter_name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/brightness")
async def adjust_brightness(req: ImageAdjustRequest):
    """Adjust image brightness."""
    result = image_service.adjust_brightness(req.factor)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/contrast")
async def adjust_contrast(req: ImageAdjustRequest):
    """Adjust image contrast."""
    result = image_service.adjust_contrast(req.factor)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/grayscale")
async def convert_to_grayscale():
    """Convert image to grayscale."""
    result = image_service.convert_to_grayscale()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/flip/horizontal")
async def flip_horizontal():
    """Flip image horizontally."""
    result = image_service.flip_horizontal()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/flip/vertical")
async def flip_vertical():
    """Flip image vertically."""
    result = image_service.flip_vertical()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/undo")
async def undo():
    """Undo the last edit operation."""
    return image_service.undo()


@router.post("/redo")
async def redo():
    """Redo the last undone operation."""
    return image_service.redo()


# Analysis endpoints


@router.post("/analyze/ocr")
async def perform_ocr(lang: str = "eng"):
    """Perform OCR on the current image."""
    if not image_service.current_image:
        raise HTTPException(status_code=400, detail="No image loaded")

    result = image_analysis_service.perform_ocr(image_service.current_image, lang)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/analyze/edges")
async def detect_edges():
    """Detect edges in the current image."""
    if not image_service.current_image:
        raise HTTPException(status_code=400, detail="No image loaded")

    result = image_analysis_service.detect_edges(image_service.current_image)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    # Convert edges image to base64 for display
    edges_b64 = image_service.get_image_as_base64.__func__(
        type("TempService", (), {"current_image": result["edges_image"]})()
    )

    return {
        "success": True,
        "edge_pixels": result["edge_pixels"],
        "total_pixels": result["total_pixels"],
        "edge_percentage": result["edge_percentage"],
        "edges_preview": edges_b64.get("data") if edges_b64["success"] else None,
    }


@router.post("/analyze/shapes")
async def detect_shapes():
    """Detect shapes in the current image."""
    if not image_service.current_image:
        raise HTTPException(status_code=400, detail="No image loaded")

    result = image_analysis_service.detect_shapes(image_service.current_image)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/analyze/colors")
async def analyze_colors():
    """Analyze dominant colors in the current image."""
    if not image_service.current_image:
        raise HTTPException(status_code=400, detail="No image loaded")

    result = image_analysis_service.analyze_colors(image_service.current_image)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/analyze/faces")
async def detect_faces():
    """Detect faces in the current image."""
    if not image_service.current_image:
        raise HTTPException(status_code=400, detail="No image loaded")

    result = image_analysis_service.detect_faces(image_service.current_image)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/analyze/statistics")
async def get_image_statistics():
    """Get statistical information about the current image."""
    if not image_service.current_image:
        raise HTTPException(status_code=400, detail="No image loaded")

    result = image_analysis_service.get_image_statistics(image_service.current_image)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
