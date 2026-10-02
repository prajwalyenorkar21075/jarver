"""Computer Vision — knowledge domain for OpenCV, YOLO, and image processing."""

import logging
from ..base import KnowledgeDomain, KnowledgeEntry, DifficultyLevel

logger = logging.getLogger(__name__)


def create_vision_domain() -> KnowledgeDomain:
    domain = KnowledgeDomain(
        name="computer_vision",
        description="Computer vision for robotics — OpenCV, YOLO object detection, image processing, and visual perception for robot navigation and manipulation.",
        subcategories=["opencv", "image_processing", "object_detection", "yolo", "depth", "slam", "calibration"],
    )

    domain.add_entry(KnowledgeEntry(
        id="vision-opencv-001",
        title="OpenCV Basics — Image Operations and Processing",
        content="""OpenCV (Open Source Computer Vision Library) is the standard for computer vision in robotics — image processing, object detection, and visual perception.

Image Representation:
- Images as NumPy arrays: height × width × channels
- Color images: BGR format (Blue, Green, Red) — 3 channels, uint8 (0-255)
- Grayscale: Single channel, uint8 (0=black, 255=white)
- Floating point: float32 (0.0-1.0) for processing

Core Operations:
```python
import cv2
import numpy as np

# Read image
img = cv2.imread('image.jpg')  # BGR format
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Display
cv2.imshow('Window', img)
cv2.waitKey(0)
cv2.destroyAllWindows()

# Resize
resized = cv2.resize(img, (640, 480))

# Draw
cv2.line(img, (0,0), (100,100), (0,255,0), 2)
cv2.rectangle(img, (50,50), (150,150), (0,0,255), 2)
cv2.circle(img, (200,200), 50, (255,0,0), -1)  # filled
cv2.putText(img, 'Hello', (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
```

Color Spaces:
- BGR: Default OpenCV format
- RGB: Standard format (cv2.COLOR_BGR2RGB)
- HSV: Hue, Saturation, Value — good for color filtering
- GRAY: Grayscale — simplifies processing
- LAB: Perceptually uniform — good for color comparison

Image Arithmetic:
- cv2.add(), cv2.subtract(): Saturated arithmetic (clips to 0-255)
- cv2.bitwise_and(), bitwise_or(): Logical operations (masks)
- cv2.threshold(): Binary thresholding (grayscale → binary)
- cv2.inRange(): Color range filtering (HSV)""",
        domain="computer_vision",
        category="opencv",
        tags=["opencv", "cv2", "image processing", "basics"],
        difficulty=DifficultyLevel.BEGINNER,
        examples=[
            "Read: img = cv2.imread('robot.jpg'); gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)",
            "Color filter: hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV); mask = cv2.inRange(hsv, lower_red, upper_red)",
            "Threshold: _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="vision-contours-001",
        title="Contour Detection and Shape Analysis",
        content="""Contours are continuous curves connecting points of the same color/intensity — used for object detection, shape analysis, and measurement.

Contour Detection:
```python
import cv2

# Preprocessing
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
blurred = cv2.GaussianBlur(gray, (5, 5), 0)
_, binary = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)

# Find contours
contours, hierarchy = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Draw contours
cv2.drawContours(img, contours, -1, (0, 255, 0), 2)

# Contour properties
for cnt in contours:
    area = cv2.contourArea(cnt)
    perimeter = cv2.contourLength(cnt)
    x, y, w, h = cv2.boundingRect(cnt)  # bounding box
    (cx, cy), radius = cv2.minEnclosingCircle(cnt)  # circle
    rect = cv2.minAreaRect(cnt)  # rotated rectangle
    box = cv2.boxPoints(rect)
    box = np.int0(box)
    
    # Shape approximation
    epsilon = 0.02 * perimeter
    approx = cv2.approxPolyDP(cnt, epsilon, True)
    if len(approx) == 4:
        shape = "Rectangle"
    elif len(approx) == 3:
        shape = "Triangle"
    elif len(approx) > 8:
        shape = "Circle"
```

Contour Filtering:
- Area: Filter by size (remove noise, keep objects)
- Aspect ratio: width/height (detect elongated objects)
- Solidity: area / convex hull area (detect concave shapes)
- Extent: area / bounding rect area (how "full" the shape is)
- Circularity: 4π × area / perimeter² (1.0 = perfect circle)

Applications:
- Object counting (blobs, cells, parts)
- Shape sorting (triangles, squares, circles)
- Position estimation (centroid for robot grasping)
- Defect detection (missing parts, irregular shapes)""",
        domain="computer_vision",
        category="image_processing",
        tags=["opencv", "contours", "shapes", "detection", "measurement"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["vision-opencv-001"],
        examples=[
            "Find objects: contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)",
            "Filter by area: if cv2.contourArea(cnt) > 1000: # keep large objects",
            "Centroid: M = cv2.moments(cnt); cx = int(M['m10']/M['m00']); cy = int(M['m01']/M['m00'])",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="vision-yolo-001",
        title="YOLO — Real-Time Object Detection",
        content="""YOLO (You Only Look Once) is a state-of-the-art object detection model — detects multiple objects with bounding boxes and class labels in real-time.

YOLO Versions:
- YOLOv5: Popular, well-documented, Ultralytics implementation
- YOLOv8: Latest (2023), faster, more accurate, easier to use
- YOLO-NAS: Neural architecture search optimized
- YOLO-World: Open-vocabulary detection (no training needed)

YOLO Architecture:
1. Backbone: Feature extraction (CSPDarknet, EfficientNet)
2. Neck: Multi-scale feature fusion (FPN, PAN)
3. Head: Prediction (bounding boxes, confidence, class probabilities)

Using YOLOv8:
```python
from ultralytics import YOLO

# Load model
model = YOLO('yolov8n.pt')  # nano (fast), yolov8s/m/l/x (larger = more accurate)

# Inference
results = model('image.jpg')
# or
results = model(video_stream)

# Process results
for result in results:
    boxes = result.boxes  # bounding boxes
    masks = result.masks  # segmentation masks (if using YOLOv8-seg)
    keypoints = result.keypoints  # pose estimation (if using YOLOv8-pose)
    
    for box in boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()  # coordinates
        confidence = box.conf[0].item()
        class_id = int(box.cls[0].item())
        class_name = model.names[class_id]
        
        print(f"Detected {class_name} with {confidence:.2f} confidence at ({x1},{y1})-({x2},{y2})")

# Draw results
annotated_frame = results[0].plot()  # draws boxes on image
cv2.imshow('Detection', annotated_frame)
```

Training Custom YOLO:
```python
# Dataset format (YOLO format)
# images/
#   image1.jpg
#   image2.jpg
# labels/
#   image1.txt  # class_id x_center y_center width height (normalized 0-1)
#   image2.txt

# Train
model = YOLO('yolov8n.pt')
model.train(data='dataset.yaml', epochs=100, imgsz=640, batch=16)

# Validate
metrics = model.val()

# Export
model.export(format='onnx')  # ONNX, TensorRT, CoreML, TFLite
```

Performance:
- YOLOv8n: 80 FPS (RTX 3080), 37.3 mAP@50:95
- YOLOv8s: 45 FPS, 44.9 mAP
- YOLOv8m: 20 FPS, 50.2 mAP
- YOLOv8x: 8 FPS, 55.6 mAP""",
        domain="computer_vision",
        category="yolo",
        tags=["yolo", "object detection", "deep learning", "real-time"],
        difficulty=DifficultyLevel.INTERMEDIATE,
        prerequisites=["vision-opencv-001"],
        examples=[
            "Load: model = YOLO('yolov8n.pt'); results = model('image.jpg')",
            "Train: model.train(data='robot_parts.yaml', epochs=100, imgsz=640)",
            "Export: model.export(format='onnx') for deployment on edge devices",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="vision-depth-001",
        title="Depth Estimation — Stereo Vision and RGB-D Cameras",
        content="""Depth estimation provides 3D information about the scene — essential for robot navigation, obstacle avoidance, and manipulation.

Depth Sensing Methods:

1. Stereo Vision (Passive)
   - Two cameras (left, right) with known baseline
   - Disparity: Pixel shift between left and right images
   - Depth = (focal_length × baseline) / disparity
   - Pros: No special hardware, works outdoors
   - Cons: Requires texture, computationally intensive
   - Libraries: OpenCV StereoSGBM, OpenCV StereoBM

2. Structured Light (Active)
   - Project known pattern (dots, lines) onto scene
   - Pattern deformation → depth calculation
   - Pros: High accuracy, dense point cloud
   - Cons: Fails outdoors (sunlight), limited range
   - Examples: Intel RealSense D400, Kinect v1

3. Time-of-Flight (ToF)
   - Measure light travel time (pulsed or modulated)
   - Depth = (speed_of_light × time) / 2
   - Pros: Fast, works in dark, medium range (0.5-10m)
   - Cons: Lower resolution, multipath errors
   - Examples: Intel RealSense L515, Microsoft Azure Kinect

4. LiDAR (Active)
   - Laser scanning (see Sensors domain)
   - High accuracy, long range (up to 100m+)
   - Pros: Precise, works outdoors
   - Cons: Expensive, sparse point cloud (vs RGB-D)

RGB-D Cameras:
- Intel RealSense D435: Depth 0.3-3m, RGB 1920x1080, 30-90 FPS, $200
- Intel RealSense D455: Depth 0.6-6m, longer baseline, $250
- Microsoft Azure Kinect: Depth 0.5-5.5m, ToF, 30 FPS, $400
- OAK-D (Luxonis): Stereo + AI processing, $150-300

Using RealSense:
```python
import pyrealsense2 as rs

pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
pipeline.start(config)

frames = pipeline.wait_for_frames()
depth_frame = frames.get_depth_frame()
color_frame = frames.get_color_frame()

depth_image = np.asanyarray(depth_frame.get_data())
color_image = np.asanyarray(color_frame.get_data())

# Get depth at pixel (x, y)
depth_mm = depth_image[y, x]  # 16-bit, in millimeters
```

Applications:
- Obstacle detection (point cloud thresholding)
- Object pose estimation (ICP, template matching)
- Bin picking (segmentation + grasping)
- SLAM (visual odometry, 3D mapping)""",
        domain="computer_vision",
        category="depth",
        tags=["depth", "stereo", "rgb-d", "realsense", "3d", "point cloud"],
        difficulty=DifficultyLevel.ADVANCED,
        prerequisites=["vision-opencv-001"],
        examples=[
            "RealSense: pipeline = rs.pipeline(); pipeline.start(); frames = pipeline.wait_for_frames()",
            "Depth value: depth_mm = depth_image[y, x] # 16-bit millimeters",
            "Point cloud: pcl = rs.pointcloud(); points = pcl.calculate(depth_frame)",
        ],
    ))

    domain.add_entry(KnowledgeEntry(
        id="vision-calibration-001",
        title="Camera Calibration and Distortion Correction",
        content="""Camera calibration determines intrinsic parameters (focal length, optical center) and distortion coefficients — essential for accurate measurements and AR/VR.

Camera Model:
- Pinhole camera model: 3D world → 2D image projection
- Intrinsic matrix K: [[fx, 0, cx], [0, fy, cy], [0, 0, 1]]
  - fx, fy: Focal length in pixels
  - cx, cy: Optical center (principal point)
- Distortion coefficients: k1, k2, p1, p2, k3 (radial and tangential)

Calibration Process:
```python
import cv2
import numpy as np

# Prepare object points (chessboard corners in world coordinates)
objp = np.zeros((6*7, 3), np.float32)
objp[:, :2] = np.mgrid[0:7, 0:6].T.reshape(-1, 2)
objp *= square_size  # real-world size (e.g., 25mm)

# Arrays to store object points and image points
objpoints = []  # 3D points in real world
imgpoints = []  # 2D points in image

# Process calibration images
for fname in calibration_images:
    img = cv2.imread(fname)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Find chessboard corners
    ret, corners = cv2.findChessboardCorners(gray, (7, 6), None)
    
    if ret:
        objpoints.append(objp)
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        imgpoints.append(corners2)

# Calibrate camera
ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)

# mtx: Camera matrix (intrinsic)
# dist: Distortion coefficients
# rvecs, tvecs: Rotation and translation vectors for each image
```

Undistortion:
```python
# Undistort image
h, w = img.shape[:2]
newcameramtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, (w, h), 1, (w, h))
dst = cv2.undistort(img, mtx, dist, None, newcameramtx)

# Undistort point
point_undistorted = cv2.undistortPoints(point_distorted, mtx, dist, P=newcameramtx)
```

Calibration Patterns:
- Chessboard: High contrast, easy corner detection
- Circle grid: More robust to occlusion, asymmetric for pose
- ArUco markers: Dynamic, can be detected during operation

Accuracy:
- Reprojection error: < 0.5 pixels (good), < 0.2 pixels (excellent)
- Use 15-25 images from different angles and distances
- Cover entire field of view (corners and edges)""",
        domain="computer_vision",
        category="calibration",
        tags=["camera", "calibration", "distortion", "intrinsic", "chessboard"],
        difficulty=DifficultyLevel.ADVANCED,
        prerequisites=["vision-opencv-001"],
        examples=[
            "Calibrate: ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, size)",
            "Undistort: dst = cv2.undistort(img, mtx, dist, None, newcameramtx)",
            "Reprojection error: < 0.5 pixels = good calibration",
        ],
    ))

    logger.info(f"[KNOWLEDGE] Created Computer Vision domain with {len(domain.entries)} entries")
    return domain
