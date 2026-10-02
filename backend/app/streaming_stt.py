"""Streaming speech-to-text service with WebSocket support.

Provides real-time transcription with partial results for lower latency
and better user experience during voice input.
"""

from __future__ import annotations

import asyncio
import io
import logging
from typing import AsyncGenerator, Optional

import httpx

logger = logging.getLogger("jarvis.streaming_stt")

# Chunk size for streaming (200ms of audio at 16kHz mono 16-bit)
CHUNK_DURATION_MS = 200
CHUNK_SIZE_BYTES = 6400  # 200ms * 16000Hz * 2 bytes


class StreamingSTTService:
    """Streaming speech-to-text service with partial result support."""
    
    def __init__(self, groq_api_key: str):
        self.groq_api_key = groq_api_key
        self.audio_buffer = bytearray()
        self.is_streaming = False
        self.last_partial = ""
        
    async def stream_audio_chunk(self, chunk: bytes) -> Optional[dict]:
        """Process an audio chunk and return partial/final transcription.
        
        Returns:
            dict with keys:
                - text: transcribed text
                - is_final: True if this is a final result
                - confidence: confidence score (0.0 to 1.0)
                - language: detected language code
        """
        if not chunk:
            return None
            
        self.audio_buffer.extend(chunk)
        
        # Only transcribe when we have enough audio (at least 500ms)
        min_chunk_size = CHUNK_SIZE_BYTES * 2.5
        if len(self.audio_buffer) < min_chunk_size:
            return None
        
        # Extract audio segment for transcription
        audio_segment = bytes(self.audio_buffer)
        self.audio_buffer = bytearray()  # Clear buffer
        
        try:
            result = await self._transcribe_segment(audio_segment)
            if result:
                self.last_partial = result.get("text", "")
            return result
        except Exception as e:
            logger.warning(f"Streaming STT chunk failed: {e}")
            return None
    
    async def _transcribe_segment(self, audio_bytes: bytes) -> Optional[dict]:
        """Transcribe an audio segment using Groq Whisper."""
        if not self.groq_api_key:
            logger.error("GROQ_API_KEY not configured")
            return None
        
        try:
            # Convert raw PCM to WAV format for Whisper
            wav_bytes = self._pcm_to_wav(audio_bytes)
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
                data = {
                    "model": "whisper-large-v3-turbo",
                    "response_format": "verbose_json",
                    "temperature": "0.0",
                }
                
                resp = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.groq_api_key}"},
                    files=files,
                    data=data,
                )
                
                if resp.status_code != 200:
                    logger.warning(f"Whisper API error: {resp.status_code}")
                    return None
                
                res_json = resp.json()
                text = res_json.get("text", "").strip()
                
                if not text:
                    return None
                
                # Use enhanced language detection
                try:
                    from app.language_detection import detect_language, get_speech_lang_code
                    detection = detect_language(text)
                    language = get_speech_lang_code(detection)
                    confidence = detection.confidence
                except ImportError:
                    language = res_json.get("language", "en")
                    confidence = 0.5
                
                return {
                    "text": text,
                    "is_final": False,  # Will be marked final by caller
                    "confidence": confidence,
                    "language": language,
                }
                
        except Exception as e:
            logger.error(f"Transcription segment failed: {e}")
            return None
    
    def _pcm_to_wav(self, pcm_bytes: bytes, sample_rate: int = 16000) -> bytes:
        """Convert raw PCM bytes to WAV format."""
        import wave
        
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_bytes)
        
        return buffer.getvalue()
    
    async def finalize(self) -> Optional[dict]:
        """Finalize streaming and return the final transcription.
        
        Call this when the user stops speaking to get the complete transcription.
        """
        if not self.audio_buffer:
            if self.last_partial:
                return {
                    "text": self.last_partial,
                    "is_final": True,
                    "confidence": 0.8,
                    "language": "en-IN",
                }
            return None
        
        # Transcribe remaining buffer
        audio_segment = bytes(self.audio_buffer)
        self.audio_buffer = bytearray()
        
        result = await self._transcribe_segment(audio_segment)
        if result:
            result["is_final"] = True
            return result
        
        # Fallback to last partial
        if self.last_partial:
            return {
                "text": self.last_partial,
                "is_final": True,
                "confidence": 0.6,
                "language": "en-IN",
            }
        
        return None
    
    def reset(self):
        """Reset the streaming state."""
        self.audio_buffer = bytearray()
        self.is_streaming = False
        self.last_partial = ""


# Global instance (initialized in main.py)
_streaming_stt: Optional[StreamingSTTService] = None


def get_streaming_stt(groq_api_key: str) -> StreamingSTTService:
    """Get or create the global streaming STT instance."""
    global _streaming_stt
    if _streaming_stt is None:
        _streaming_stt = StreamingSTTService(groq_api_key)
    return _streaming_stt
