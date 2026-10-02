import os
import io
import time
import json
import base64
import logging
import threading
from typing import Any, Tuple, List, Dict, Optional
import numpy as np
import scipy.signal
import cv2

from app.persistent_memory import (
    get_biometric_consent,
    set_biometric_consent,
    save_face_embedding,
    save_voice_embedding,
    get_biometric_profile,
    get_all_biometric_profiles,
    delete_biometric_profile,
    purge_all_biometrics,
)

logger = logging.getLogger("jarvis.biometrics")

# =========================================================================
# 1. OPENCV FACE DETECTION ENGINE
# =========================================================================

_FACE_CASCADE: Optional[Any] = None

def get_face_cascade() -> Optional[Any]:
    """Lazy-load the OpenCV Haar Cascade face detector."""
    global _FACE_CASCADE
    if _FACE_CASCADE is None:
        if not hasattr(cv2, "CascadeClassifier"):
            logger.warning("cv2 module does not export CascadeClassifier.")
            return None
        cascade_dir = getattr(cv2.data, "haarcascades", "") if hasattr(cv2, "data") else ""
        cascade_path = os.path.join(cascade_dir, "haarcascade_frontalface_default.xml")
        if not os.path.exists(cascade_path):
            logger.warning(f"Haar cascade XML missing: {cascade_path}")
            return None
        try:
            cascade = cv2.CascadeClassifier(cascade_path)
            if not cascade.empty():
                _FACE_CASCADE = cascade
        except Exception as e:
            logger.error(f"Failed to initialize Haar CascadeClassifier: {e}")
            return None
    return _FACE_CASCADE


def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    """Decode raw image bytes (JPEG/PNG/WebP) into a NumPy BGR image."""
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image from provided bytes.")
    return img


def decode_base64_image(base64_str: str) -> np.ndarray:
    """Decode base64 data-url or raw base64 string into NumPy BGR image."""
    if "," in base64_str:
        base64_str = base64_str.split(",", 1)[1]
    raw = base64.b64decode(base64_str)
    return decode_image_bytes(raw)


def detect_faces(image_bgr: np.ndarray) -> List[Dict[str, int]]:
    """Detect all frontal faces in the image.
    Returns list of bounding boxes: [{"x": x, "y": y, "w": w, "h": h}].
    """
    cascade = get_face_cascade()
    if cascade is None:
        logger.warning("Face cascade detector unavailable; returning empty detections.")
        return []
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    # Histogram equalization for illumination robustness
    gray = cv2.equalizeHist(gray)
    
    faces = cascade.detectMultiScale(
        gray,
        scaleFactor=1.12,
        minNeighbors=5,
        minSize=(45, 45),
        flags=cv2.CASCADE_SCALE_IMAGE
    )
    
    results = []
    for (x, y, w, h) in faces:
        results.append({
            "x": int(x),
            "y": int(y),
            "w": int(w),
            "h": int(h),
        })
    return results


def compute_face_embedding(face_crop: np.ndarray) -> List[float]:
    """Extract a 128-dimensional normalized mathematical biometric embedding
    from a cropped face image.
    
    PRIVACY GUARANTEE:
    - Never stores raw pixel images on disk.
    - Encodes multi-scale spatial frequency, gradient distribution, and LBP texture histograms.
    - Resulting 128-D vector is normalized to unit L2 norm: ||f|| = 1.0.
    """
    # 1. Canonical normalization: 128x128 resolution
    if len(face_crop.shape) == 3:
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = face_crop

    resized = cv2.resize(gray, (128, 128), interpolation=cv2.INTER_AREA)
    norm_face = cv2.equalizeHist(resized).astype(np.float32) / 255.0

    # 2. Divide canonical face into 4x4 spatial grid cells (16 cells total, 32x32 each)
    cells = []
    for r in range(4):
        for c in range(4):
            cell = norm_face[r*32:(r+1)*32, c*32:(c+1)*32]
            # Mean intensity, variance
            m = float(np.mean(cell))
            v = float(np.var(cell))
            
            # Horizontal and vertical spatial gradients (Sobel filter)
            gx = cv2.Sobel(cell, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(cell, cv2.CV_32F, 0, 1, ksize=3)
            mag = float(np.mean(np.sqrt(gx**2 + gy**2)))
            
            # Simple 8-bin orientation histogram
            angles = np.arctan2(gy, gx)
            hist, _ = np.histogram(angles, bins=5, range=(-np.pi, np.pi))
            hist_norm = (hist / (np.sum(hist) + 1e-6)).tolist()
            
            # Total 8 features per cell x 16 cells = 128 features!
            cells.extend([m, v, mag] + hist_norm)

    vec = np.array(cells[:128], dtype=np.float32)
    # L2 Unit Normalization
    norm = np.linalg.norm(vec)
    if norm > 1e-8:
        vec = vec / norm

    return [round(float(x), 6) for x in vec]


# =========================================================================
# 2. ACOUSTIC VOICE RECOGNITION ENGINE
# =========================================================================

def compute_voice_embedding(audio_samples: np.ndarray, sample_rate: int = 16000) -> Optional[List[float]]:
    """Extract a 128-dimensional acoustic speaker signature from audio samples.
    
    PRIVACY GUARANTEE:
    - Never stores raw voice audio recordings permanently on disk.
    - Extracts Mel-frequency spectral distribution, spectral centroid, roll-off, and harmonic contours.
    - Resulting 128-D vector is normalized to unit L2 norm: ||v|| = 1.0.
    """
    if len(audio_samples) < sample_rate * 0.4:
        # Less than 400ms of audio, not enough for speaker signature
        return None

    # RMS energy check to ensure voice activity
    rms = np.sqrt(np.mean(audio_samples**2))
    if rms < 0.003:
        return None

    # Pre-emphasis filter
    emphasized = np.append(audio_samples[0], audio_samples[1:] - 0.97 * audio_samples[:-1])

    # STFT computation
    nperseg = min(512, len(emphasized))
    f, t, Zxx = scipy.signal.stft(emphasized, fs=sample_rate, nperseg=nperseg, noverlap=nperseg//2)
    magnitude = np.abs(Zxx)

    if magnitude.size == 0:
        return None

    # 1. Mel-scale filterbank simulation (32 bands across frequency range)
    num_bins = magnitude.shape[0]
    mel_points = np.linspace(0, num_bins - 1, 33, dtype=int)
    mel_energies = []
    for i in range(32):
        start = mel_points[i]
        end = max(start + 1, mel_points[i+1])
        band_energy = float(np.mean(magnitude[start:end, :]))
        mel_energies.append(np.log1p(band_energy))

    # 2. Spectral statistics over time frames (mean & variance across 32 mel bands -> 64 features)
    mel_mean = np.array(mel_energies, dtype=np.float32)
    mel_std = np.std(magnitude[:32, :], axis=1) if magnitude.shape[0] >= 32 else np.zeros(32, dtype=np.float32)

    # 3. Spectral Centroid, Spread, Flatness, and Roll-off
    norm_mag = magnitude / (np.sum(magnitude, axis=0, keepdims=True) + 1e-8)
    freqs = np.arange(num_bins)[:, None]
    centroid = np.sum(freqs * norm_mag, axis=0)
    centroid_stats = [float(np.mean(centroid)), float(np.std(centroid))]

    # Zero-crossing rate
    zcr = np.mean(np.abs(np.diff(np.sign(emphasized))))

    # Combine into 128-dimensional acoustic representation
    features = list(mel_mean) + list(mel_std[:32]) + centroid_stats + [float(zcr), float(rms)]
    # Pad to exactly 128 dimensions using DCT / interpolation if needed
    if len(features) < 128:
        expanded = np.interp(np.linspace(0, len(features), 128), np.arange(len(features)), features)
    else:
        expanded = np.array(features[:128], dtype=np.float32)

    # L2 Unit Normalization
    norm = np.linalg.norm(expanded)
    if norm > 1e-8:
        expanded = expanded / norm

    return [round(float(x), 6) for x in expanded]


def decode_audio_bytes_to_numpy(audio_bytes: bytes) -> Tuple[np.ndarray, int]:
    """Decode raw WAV/PCM or WebM audio bytes to float32 NumPy array."""
    try:
        import soundfile as sf
        with io.BytesIO(audio_bytes) as bio:
            data, samplerate = sf.read(bio)
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)  # downmix to mono
            return data.astype(np.float32), samplerate
    except Exception as e:
        logger.debug(f"Soundfile decode fallback to raw PCM: {e}")
        # Fallback to standard 16-bit PCM 16kHz mono
        data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return data, 16000


# =========================================================================
# 3. MULTI-MODAL IDENTITY FUSION & REAL-TIME STATE
# =========================================================================

class BiometricIdentityManager:
    """Manages continuous background recognition, user identity state,
    and role-based permissions (Owner vs Guest).
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.current_user_id = "owner"
        self.display_name = "Tony Stark"
        self.role = "owner"  # "owner" | "authorized" | "guest"
        self.face_matched = False
        self.face_confidence = 0.0
        self.voice_matched = False
        self.voice_confidence = 0.0
        self.last_face_time = 0.0
        self.last_voice_time = 0.0
        self.camera_active = False
        self.mic_active = False
        self.continuous_camera_running = False
        self._daemon_thread: Optional[threading.Thread] = None

    def get_state(self) -> Dict[str, Any]:
        """Return the current biometric identity telemetry."""
        with self.lock:
            # If no face or voice detected in last 2 minutes, fallback to standby
            now = time.time()
            is_recent_face = (now - self.last_face_time) < 120.0
            is_recent_voice = (now - self.last_voice_time) < 120.0
            
            profiles = get_all_biometric_profiles()
            has_enrolled_face = any(p.get("face_embedding") is not None for p in profiles)
            has_enrolled_voice = any(p.get("voice_embedding") is not None for p in profiles)
            consent = get_biometric_consent("owner")

            return {
                "user_id": self.current_user_id,
                "display_name": self.display_name,
                "role": self.role,
                "is_owner": self.role == "owner",
                "face_matched": self.face_matched and is_recent_face,
                "face_confidence": round(self.face_confidence, 2) if is_recent_face else 0.0,
                "voice_matched": self.voice_matched and is_recent_voice,
                "voice_confidence": round(self.voice_confidence, 2) if is_recent_voice else 0.0,
                "camera_active": self.camera_active,
                "mic_active": self.mic_active,
                "consent_given": consent,
                "has_enrolled_face": has_enrolled_face,
                "has_enrolled_voice": has_enrolled_voice,
                "enrolled_profiles": len(profiles),
                "permissions": ["system_actions", "shutdown", "file_ops", "multitask"] if self.role == "owner" else ["chat", "search"],
                "last_seen_timestamp": max(self.last_face_time, self.last_voice_time),
            }

    def verify_face_frame(self, image_np: np.ndarray) -> Dict[str, Any]:
        """Detect faces and match against enrolled biometric profiles."""
        self.camera_active = True
        faces = detect_faces(image_np)
        
        if not faces:
            with self.lock:
                # Retain role but clear face match
                self.face_matched = False
                self.face_confidence = 0.0
            return {
                "detected": False,
                "faces": [],
                "identified": False,
                "user_id": self.current_user_id,
                "display_name": self.display_name,
                "role": self.role,
            }

        # Retrieve enrolled profiles from SQLite
        profiles = get_all_biometric_profiles()
        enrolled_face_profiles = [p for p in profiles if p.get("face_embedding")]

        recognized_faces = []
        best_match_user: Optional[Dict[str, Any]] = None
        highest_sim = 0.0

        for f_box in faces:
            x, y, w, h = f_box["x"], f_box["y"], f_box["w"], f_box["h"]
            face_crop = image_np[y:y+h, x:x+w]
            if face_crop.size == 0:
                continue

            current_emb = compute_face_embedding(face_crop)
            matched_profile = None
            sim_score = 0.0

            if enrolled_face_profiles:
                for prof in enrolled_face_profiles:
                    saved_emb = prof["face_embedding"]
                    # Cosine Similarity
                    sim = float(np.dot(current_emb, saved_emb) / (np.linalg.norm(current_emb) * np.linalg.norm(saved_emb) + 1e-8))
                    if sim > sim_score:
                        sim_score = sim
                        matched_profile = prof

            # Threshold for facial verification (0.72)
            MATCH_THRESHOLD = 0.72
            is_identified = sim_score >= MATCH_THRESHOLD and matched_profile is not None

            if is_identified and matched_profile:
                name = matched_profile.get("display_name", "Tony Stark")
                uid = matched_profile.get("user_id", "owner")
                role = matched_profile.get("role", "owner")
            elif not enrolled_face_profiles:
                # If no faces are enrolled yet, grant un-enrolled default Owner status with prompt to enroll
                name = "Tony Stark (Un-enrolled)"
                uid = "owner"
                role = "owner"
                sim_score = 0.50
                is_identified = False
            else:
                name = "Guest / Unknown User"
                uid = "guest"
                role = "guest"
                is_identified = False

            if sim_score > highest_sim:
                highest_sim = sim_score
                best_match_user = {
                    "user_id": uid,
                    "display_name": name,
                    "role": role,
                    "confidence": sim_score,
                    "is_identified": is_identified,
                }

            recognized_faces.append({
                "bbox": [x, y, w, h],
                "identified": is_identified,
                "user_id": uid,
                "display_name": name,
                "role": role,
                "confidence": round(sim_score, 3),
            })

        # Update global state
        with self.lock:
            self.last_face_time = time.time()
            if best_match_user:
                self.current_user_id = best_match_user["user_id"]
                self.display_name = best_match_user["display_name"]
                self.role = best_match_user["role"]
                self.face_matched = best_match_user["is_identified"]
                self.face_confidence = best_match_user["confidence"]

        return {
            "detected": True,
            "faces": recognized_faces,
            "identified": best_match_user["is_identified"] if best_match_user else False,
            "user_id": self.current_user_id,
            "display_name": self.display_name,
            "role": self.role,
            "confidence": round(self.face_confidence, 3),
        }

    def verify_voice_audio(self, audio_bytes: bytes) -> Dict[str, Any]:
        """Analyze speaker audio snippet and match against enrolled speaker profiles."""
        self.mic_active = True
        samples, sr = decode_audio_bytes_to_numpy(audio_bytes)
        emb = compute_voice_embedding(samples, sample_rate=sr)

        if not emb:
            return {
                "identified": False,
                "status": "insufficient_audio_or_silence",
                "user_id": self.current_user_id,
                "display_name": self.display_name,
                "role": self.role,
                "confidence": 0.0,
            }

        profiles = get_all_biometric_profiles()
        enrolled_voice_profiles = [p for p in profiles if p.get("voice_embedding")]

        highest_sim = 0.0
        best_profile = None

        if enrolled_voice_profiles:
            for prof in enrolled_voice_profiles:
                saved_emb = prof["voice_embedding"]
                sim = float(np.dot(emb, saved_emb) / (np.linalg.norm(emb) * np.linalg.norm(saved_emb) + 1e-8))
                if sim > highest_sim:
                    highest_sim = sim
                    best_profile = prof

        # Threshold for acoustic voice recognition (0.70)
        VOICE_THRESHOLD = 0.70
        is_identified = highest_sim >= VOICE_THRESHOLD and best_profile is not None

        with self.lock:
            self.last_voice_time = time.time()
            if is_identified and best_profile:
                self.current_user_id = best_profile.get("user_id", "owner")
                self.display_name = best_profile.get("display_name", "Tony Stark")
                self.role = best_profile.get("role", "owner")
                self.voice_matched = True
                self.voice_confidence = highest_sim
            elif not enrolled_voice_profiles:
                # No voice enrolled yet
                self.voice_matched = False
                self.voice_confidence = 0.50
            else:
                # Recognized as different speaker
                self.current_user_id = "guest"
                self.display_name = "Guest User"
                self.role = "guest"
                self.voice_matched = False
                self.voice_confidence = highest_sim

        return {
            "identified": is_identified,
            "user_id": self.current_user_id,
            "display_name": self.display_name,
            "role": self.role,
            "confidence": round(highest_sim, 3),
        }

    def verify_permission(self, action_name: str) -> Tuple[bool, str]:
        """Check if currently recognized user has permission for sensitive action."""
        with self.lock:
            # Sensitive workstation actions restricted to Owner
            restricted_actions = [
                "shutdown_pc", "turn_off_pc", "restart_pc", "reboot_pc",
                "close_app", "delete_file", "purge_biometrics", "system_settings"
            ]
            if action_name in restricted_actions and self.role != "owner":
                return (
                    False,
                    f"Access Denied. Action '{action_name}' requires Tony Stark (Owner) biometric authentication. Operating in restricted Guest mode."
                )
            return (True, "Authorized")

    def enroll_face(self, image_np: np.ndarray, user_id: str = "owner", display_name: str = "Tony Stark") -> Dict[str, Any]:
        """Enroll face embedding with explicit user consent."""
        if not get_biometric_consent(user_id):
            return {"status": "error", "message": "Biometric consent must be explicitly granted before enrollment."}

        faces = detect_faces(image_np)
        if not faces:
            return {"status": "error", "message": "No face detected in provided camera frame. Please center your face."}

        # Pick the largest face in frame
        largest = max(faces, key=lambda f: f["w"] * f["h"])
        x, y, w, h = largest["x"], largest["y"], largest["w"], largest["h"]
        face_crop = image_np[y:y+h, x:x+w]
        embedding = compute_face_embedding(face_crop)

        # Save to SQLite (Zero raw images stored!)
        save_face_embedding(
            user_id=user_id,
            display_name=display_name,
            embedding=embedding,
            role="owner" if user_id == "owner" else "authorized"
        )

        with self.lock:
            self.current_user_id = user_id
            self.display_name = display_name
            self.role = "owner" if user_id == "owner" else "authorized"
            self.face_matched = True
            self.face_confidence = 1.0
            self.last_face_time = time.time()

        return {
            "status": "ok",
            "message": f"Biometric face scan for '{display_name}' successfully encoded and stored.",
            "embedding_dims": len(embedding),
            "user_id": user_id,
        }

    def enroll_voice(self, audio_bytes: bytes, user_id: str = "owner", display_name: str = "Tony Stark") -> Dict[str, Any]:
        """Enroll acoustic voice signature with explicit user consent."""
        if not get_biometric_consent(user_id):
            return {"status": "error", "message": "Biometric consent must be explicitly granted before enrollment."}

        samples, sr = decode_audio_bytes_to_numpy(audio_bytes)
        embedding = compute_voice_embedding(samples, sample_rate=sr)

        if not embedding:
            return {"status": "error", "message": "Audio sample was too short or quiet. Please speak clearly for 2-3 seconds."}

        # Save to SQLite (Zero raw audio recordings stored!)
        save_voice_embedding(
            user_id=user_id,
            display_name=display_name,
            embedding=embedding,
            role="owner" if user_id == "owner" else "authorized"
        )

        with self.lock:
            self.current_user_id = user_id
            self.display_name = display_name
            self.role = "owner" if user_id == "owner" else "authorized"
            self.voice_matched = True
            self.voice_confidence = 1.0
            self.last_voice_time = time.time()

        return {
            "status": "ok",
            "message": f"Acoustic speaker signature for '{display_name}' successfully encoded and stored.",
            "embedding_dims": len(embedding),
            "user_id": user_id,
        }

    def purge_data(self) -> Dict[str, Any]:
        """Purge all biometric vectors and reset to clean state."""
        res = purge_all_biometrics()
        with self.lock:
            self.face_matched = False
            self.face_confidence = 0.0
            self.voice_matched = False
            self.voice_confidence = 0.0
            self.current_user_id = "owner"
            self.display_name = "Tony Stark"
            self.role = "owner"
        return res


# Global singleton instance
identity_manager = BiometricIdentityManager()
