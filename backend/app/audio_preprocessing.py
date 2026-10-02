"""Audio preprocessing and noise cancellation pipeline for voice input.

Phase 3 Enhancement: Advanced audio processing to improve speech recognition
accuracy by reducing background noise, normalizing levels, and enhancing
speech clarity before sending to the STT engine.
"""

from __future__ import annotations

import io
import logging
import wave
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger("jarvis.audio")


@dataclass
class AudioStats:
    """Statistics about processed audio."""
    original_duration: float
    processed_duration: float
    noise_reduction_applied: bool
    normalization_factor: float
    snr_estimate: float


class AudioPreprocessor:
    """Real-time audio preprocessing pipeline for speech enhancement."""

    def __init__(
        self,
        sample_rate: int = 16000,
        noise_reduction: bool = True,
        normalization: bool = True,
        vad_threshold: float = 0.02,
    ):
        self.sample_rate = sample_rate
        self.noise_reduction = noise_reduction
        self.normalization = normalization
        self.vad_threshold = vad_threshold

        self.noise_profile: np.ndarray | None = None
        self.noise_frame_count = 0
        self.max_noise_frames = 20

    def _estimate_noise_profile(self, audio: np.ndarray) -> np.ndarray:
        """Estimate noise profile from the quietest 10% of frames."""
        frame_size = int(0.02 * self.sample_rate)
        n_frames = len(audio) // frame_size

        if n_frames < 10:
            return np.zeros(frame_size)

        energies = []
        for i in range(n_frames):
            frame = audio[i * frame_size:(i + 1) * frame_size]
            energies.append(np.mean(frame ** 2))

        energies = np.array(energies)
        threshold = np.percentile(energies, 10)
        noise_frames = [
            audio[i * frame_size:(i + 1) * frame_size]
            for i in range(n_frames)
            if energies[i] <= threshold
        ]

        if not noise_frames:
            return np.zeros(frame_size)

        return np.mean(noise_frames, axis=0)

    def _spectral_subtraction(
        self, audio: np.ndarray, noise_profile: np.ndarray
    ) -> np.ndarray:
        """Apply spectral subtraction to reduce stationary noise."""
        frame_size = len(noise_profile)
        n_frames = len(audio) // frame_size
        output = np.zeros_like(audio)

        noise_spectrum = np.abs(np.fft.rfft(noise_profile))
        alpha = 2.0

        for i in range(n_frames):
            start = i * frame_size
            end = start + frame_size
            frame = audio[start:end]

            frame_spectrum = np.fft.rfft(frame)
            magnitude = np.abs(frame_spectrum)
            phase = np.angle(frame_spectrum)

            clean_magnitude = np.maximum(magnitude - alpha * noise_spectrum, 0.1 * magnitude)
            clean_spectrum = clean_magnitude * np.exp(1j * phase)
            clean_frame = np.fft.irfft(clean_spectrum, n=frame_size)

            output[start:end] = clean_frame

        remainder = len(audio) % frame_size
        if remainder > 0:
            output[-remainder:] = audio[-remainder:]

        return output

    def _highpass_filter(self, audio: np.ndarray, cutoff: float = 80.0) -> np.ndarray:
        """Simple high-pass filter to remove low-frequency rumble."""
        rc = 1.0 / (2 * np.pi * cutoff)
        dt = 1.0 / self.sample_rate
        alpha = rc / (rc + dt)

        output = np.zeros_like(audio)
        output[0] = audio[0]

        for i in range(1, len(audio)):
            output[i] = alpha * (output[i - 1] + audio[i] - audio[i - 1])

        return output

    def _normalize(self, audio: np.ndarray, target_level: float = 0.8) -> tuple[np.ndarray, float]:
        """Normalize audio to target peak level."""
        peak = np.max(np.abs(audio))
        if peak < 0.001:
            return audio, 1.0

        factor = target_level / peak
        return audio * factor, factor

    def _estimate_snr(self, audio: np.ndarray) -> float:
        """Estimate signal-to-noise ratio in dB."""
        frame_size = int(0.02 * self.sample_rate)
        n_frames = len(audio) // frame_size

        if n_frames < 10:
            return 20.0

        energies = []
        for i in range(n_frames):
            frame = audio[i * frame_size:(i + 1) * frame_size]
            energies.append(np.mean(frame ** 2))

        energies = np.array(energies)
        signal_power = np.percentile(energies, 90)
        noise_power = np.percentile(energies, 10)

        if noise_power < 1e-10:
            return 40.0

        snr = 10 * np.log10(signal_power / noise_power)
        return float(np.clip(snr, 0, 60))

    def process(self, audio: np.ndarray) -> tuple[np.ndarray, AudioStats]:
        """Process audio through the full enhancement pipeline."""
        original_duration = len(audio) / self.sample_rate

        if self.noise_reduction:
            if self.noise_frame_count < self.max_noise_frames:
                current_noise = self._estimate_noise_profile(audio)
                if self.noise_profile is None:
                    self.noise_profile = current_noise
                else:
                    self.noise_profile = (
                        self.noise_profile * self.noise_frame_count + current_noise
                    ) / (self.noise_frame_count + 1)
                self.noise_frame_count += 1

            if self.noise_profile is not None and len(self.noise_profile) > 0:
                audio = self._spectral_subtraction(audio, self.noise_profile)

        audio = self._highpass_filter(audio)

        norm_factor = 1.0
        if self.normalization:
            audio, norm_factor = self._normalize(audio)

        snr = self._estimate_snr(audio)
        processed_duration = len(audio) / self.sample_rate

        stats = AudioStats(
            original_duration=original_duration,
            processed_duration=processed_duration,
            noise_reduction_applied=self.noise_reduction,
            normalization_factor=norm_factor,
            snr_estimate=snr,
        )

        logger.debug(
            f"Audio processed: {original_duration:.2f}s, SNR: {snr:.1f}dB, "
            f"norm: {norm_factor:.2f}x"
        )

        return audio, stats

    def reset_noise_profile(self):
        """Reset the noise profile for a new environment."""
        self.noise_profile = None
        self.noise_frame_count = 0
        logger.info("Noise profile reset")


def wav_bytes_to_numpy(wav_bytes: bytes) -> tuple[np.ndarray, int]:
    """Convert WAV bytes to numpy array and sample rate."""
    with io.BytesIO(wav_bytes) as buf:
        with wave.open(buf, "rb") as wf:
            sample_rate = wf.getframerate()
            n_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            n_frames = wf.getnframes()

            raw_data = wf.readframes(n_frames)

    if sample_width == 2:
        dtype = np.int16
    elif sample_width == 4:
        dtype = np.int32
    else:
        dtype = np.uint8

    audio = np.frombuffer(raw_data, dtype=dtype)

    if n_channels > 1:
        audio = audio.reshape(-1, n_channels).mean(axis=1)

    if sample_width == 2:
        audio = audio.astype(np.float32) / 32768.0
    elif sample_width == 4:
        audio = audio.astype(np.float32) / 2147483648.0
    else:
        audio = (audio.astype(np.float32) - 128.0) / 128.0

    return audio, sample_rate


def numpy_to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    """Convert numpy array to WAV bytes."""
    audio = np.clip(audio, -1.0, 1.0)
    samples = (audio * 32767.0).astype(np.int16)

    with io.BytesIO() as buf:
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(samples.tobytes())
        return buf.getvalue()


def preprocess_audio(wav_bytes: bytes) -> tuple[bytes, AudioStats]:
    """Convenience function to preprocess WAV audio bytes."""
    audio, sample_rate = wav_bytes_to_numpy(wav_bytes)
    preprocessor = AudioPreprocessor(sample_rate=sample_rate)
    processed, stats = preprocessor.process(audio)
    return numpy_to_wav_bytes(processed, sample_rate), stats
