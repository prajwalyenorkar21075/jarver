"""In-process Pocket-TTS synthesis for the cloned J.A.R.V.I.S. voice.

This module is the single voice identity used by ``POST /api/tts``: every
reply, in every supported language (English, Hindi, Marathi, Hinglish), is
spoken with the same cloned speaker derived from the user's JARVIS/Iron Man
reference recording.

It loads the local cloned-voice conditioning state
(``app/jarvis_cloned_voice_state.pt``) on top of the local model weights
referenced by ``backend/pocket_tts_cloning_config.yaml`` and synthesises
speech entirely inside the backend process, returning WAV bytes.

Because the cloned state belongs to the English Pocket-TTS model (which has no
Devanagari tokens), Hindi / Marathi replies are romanised first so they are
spoken by the exact same JARVIS speaker instead of falling back to a different
browser/system voice.

Phase 3 Enhancement: Emotion and intonation control via prosody markers,
automatic emotion detection from text content, and adaptive pacing.
"""

from __future__ import annotations

import io
import logging
import re
import threading
import wave
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np
import torch

logger = logging.getLogger("jarvis.tts")

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
CONFIG_PATH = BACKEND_DIR / "pocket_tts_cloning_config.yaml"
VOICE_STATE_PATH = APP_DIR / "jarvis_cloned_voice_state.pt"


class Emotion(Enum):
    """Voice emotion/intonation presets for JARVIS."""
    NEUTRAL = "neutral"
    CONFIRMING = "confirming"
    ALERT = "alert"
    ANALYTICAL = "analytical"
    CONGRATULATORY = "congratulatory"
    CONCERNED = "concerned"
    GREETING = "greeting"


@dataclass
class ProsodyConfig:
    """Prosody parameters for emotion-aware speech synthesis."""
    rate: float = 1.0
    pitch: float = 1.0
    pause_short: str = ", "
    pause_medium: str = ". "
    pause_long: str = "... "
    emphasis_prefix: str = ""
    emphasis_suffix: str = ""


EMOTION_PROSODY = {
    Emotion.NEUTRAL: ProsodyConfig(rate=1.0, pitch=1.0),
    Emotion.CONFIRMING: ProsodyConfig(rate=0.95, pitch=1.05),
    Emotion.ALERT: ProsodyConfig(rate=1.1, pitch=1.1),
    Emotion.ANALYTICAL: ProsodyConfig(rate=0.9, pitch=0.95),
    Emotion.CONGRATULATORY: ProsodyConfig(rate=1.05, pitch=1.15),
    Emotion.CONCERNED: ProsodyConfig(rate=0.85, pitch=0.9),
    Emotion.GREETING: ProsodyConfig(rate=0.95, pitch=1.05),
}

EMOTION_KEYWORDS = {
    Emotion.CONFIRMING: [
        "done", "completed", "finished", "success", "ready", "confirmed",
        "affirmative", "yes", "correct", "right", "exactly", "precisely",
    ],
    Emotion.ALERT: [
        "warning", "error", "critical", "danger", "attention", "alert",
        "urgent", "immediately", "hurry", "quick", "fast", "emergency",
    ],
    Emotion.ANALYTICAL: [
        "analyzing", "processing", "calculating", "examining", "investigating",
        "scanning", "reviewing", "checking", "verifying", "computing",
    ],
    Emotion.CONGRATULATORY: [
        "excellent", "brilliant", "perfect", "outstanding", "great job",
        "well done", "impressive", "magnificent", "superb", "fantastic",
    ],
    Emotion.CONCERNED: [
        "problem", "issue", "unfortunately", "sorry", "apologies", "concerned",
        "worried", "trouble", "difficulty", "unfortunately",
    ],
    Emotion.GREETING: [
        "hello", "good morning", "good afternoon", "good evening", "welcome",
        "hi", "greetings", "namaste",
    ],
}


def detect_emotion(text: str) -> Emotion:
    """Detect the most appropriate emotion for the given text."""
    text_lower = text.lower()
    scores = {emotion: 0 for emotion in Emotion}

    for emotion, keywords in EMOTION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                scores[emotion] += 1

    if max(scores.values()) == 0:
        return Emotion.NEUTRAL

    return max(scores, key=scores.get)


def apply_prosody(text: str, emotion: Emotion) -> str:
    """Apply prosody markers to text based on emotion for natural intonation."""
    config = EMOTION_PROSODY.get(emotion, EMOTION_PROSODY[Emotion.NEUTRAL])

    text = text.strip()
    if not text:
        return text

    sentences = re.split(r'([.!?]+)', text)
    processed = []

    for i, segment in enumerate(sentences):
        segment = segment.strip()
        if not segment:
            continue

        if segment in ".!?":
            if emotion == Emotion.ALERT:
                processed.append("! ")
            elif emotion == Emotion.ANALYTICAL:
                processed.append(". ")
            else:
                processed.append(segment + " ")
        else:
            if emotion == Emotion.CONGRATULATORY and i == 0:
                segment = segment.capitalize()
            elif emotion == Emotion.CONCERNED:
                segment = segment.lower() if len(segment) < 20 else segment

            if len(segment) > 40 and "," not in segment:
                words = segment.split()
                mid = len(words) // 2
                segment = " ".join(words[:mid]) + config.pause_short + " ".join(words[mid:])

            processed.append(segment)

    result = "".join(processed).strip()

    if emotion == Emotion.ANALYTICAL and not result.endswith("."):
        result += "."

    return result

# ---------------------------------------------------------------------------
# Devanagari -> Latin romanisation (keeps the JARVIS speaker for hi / mr)
# ---------------------------------------------------------------------------

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

_INDEPENDENT_VOWELS = {
    "\u0905": "a",   # अ
    "\u0906": "aa",  # आ
    "\u0907": "i",   # इ
    "\u0908": "ee",  # ई
    "\u0909": "u",   # उ
    "\u090a": "oo",  # ऊ
    "\u090b": "ri",  # ऋ
    "\u090c": "ri",  # ॠ
    "\u090d": "e",   # ऍ
    "\u090e": "e",   # ऎ
    "\u090f": "e",   # ए
    "\u0910": "ai",  # ऐ
    "\u0911": "o",   # ऑ
    "\u0912": "o",   # ऒ
    "\u0913": "o",   # ओ
    "\u0914": "au",  # औ
}

_VOWEL_SIGNS = {
    "\u093e": "aa",  # ा
    "\u093f": "i",   # ि
    "\u0940": "ee",  # ी
    "\u0941": "u",   # उ
    "\u0942": "oo",  # ऊ
    "\u0943": "ri",  # ृ
    "\u0944": "ri",  # ॄ
    "\u0945": "e",   #ऍ
    "\u0946": "e",   # ऎ
    "\u0947": "e",   # ए
    "\u0948": "ai",  # ऐ
    "\u0949": "o",   # ऑ
    "\u094a": "o",   # ऒ
    "\u094b": "o",   # ओ
    "\u094c": "au",  # औ
}

_CONSONANTS = {
    "\u0915": "k",   "\u0916": "kh",  "\u0917": "g",   "\u0918": "gh",
    "\u0919": "ng",  "\u091a": "ch",  "\u091b": "chh", "\u091c": "j",
    "\u091d": "jh",  "\u091e": "ny",  "\u091f": "t",   "\u0920": "th",
    "\u0921": "d",   "\u0922": "dh",  "\u0923": "n",   "\u0924": "t",
    "\u0925": "th",  "\u0926": "d",   "\u0927": "dh",  "\u0928": "n",
    "\u0929": "n",   "\u092a": "p",   "\u092b": "ph",  "\u092c": "b",
    "\u092d": "bh",  "\u092e": "m",   "\u092f": "y",   "\u0930": "r",
    "\u0931": "r",   "\u0932": "l",   "\u0933": "l",   "\u0934": "zh",
    "\u0935": "v",   "\u0936": "sh",  "\u0937": "sh",  "\u0938": "s",
    "\u0939": "h",
    "\u0958": "q",   "\u0959": "kh",  "\u095a": "gh",  "\u095b": "z",
    "\u095c": "r",   "\u095d": "rh",  "\u095e": "f",   "\u095f": "y",
    "\u097b": "g",   "\u097c": "l",   "\u097e": "r",   "\u097f": "n",
}

# Nukta (़) applied to an already emitted consonant cluster.
_NUKTA_VARIANTS = {
    "k": "q", "kh": "q", "g": "gh", "j": "z", "d": "r", "dh": "rh",
    "ph": "f", "b": "bh", "y": "y",
}

_VIRAMA = "\u094d"
_NUKTA = "\u093c"

_OTHER = {
    "\u0901": "n",   # ँ chandrabindu
    "\u0902": "n",   # ं anusvara
    "\u0903": "h",   # ः visarga
    "\u093d": "'",   # ऽ avagraha
    "\u0964": ". ",  # । danda
    "\u0965": ".. ", # ॥ double danda
    "\u0966": "0", "\u0967": "1", "\u0968": "2", "\u0969": "3",
    "\u096a": "4", "\u096b": "5", "\u096c": "6", "\u096d": "7",
    "\u096e": "8", "\u096f": "9",
    "\u0970": "-",  # ॰ abbreviation sign
    "\u0971": "'",  # ॑
}

# Symbols that would otherwise be spelled out (or garbled) by the English model.
_SYMBOL_MAP = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u00a0": " ",
    "\u2713": "", "\u2714": "",
}


def has_devanagari(text: str) -> bool:
    """True when ``text`` contains Devanagari characters (Hindi / Marathi)."""
    return bool(DEVANAGARI_RE.search(text or ""))


def romanize_devanagari(text: str) -> str:
    """Transliterate Devanagari (Hindi / Marathi) into Latin script.

    The cloned JARVIS voice state belongs to the English Pocket-TTS model, so
    feeding raw Devanagari to it produces garbled audio. Romanising lets every
    language be spoken by that exact same JARVIS speaker instead of a
    different system/browser voice.
    """
    text = text or ""
    out: list[str] = []
    i, n = 0, len(text)

    while i < n:
        ch = text[i]
        code = ord(ch)

        if 0x0900 <= code <= 0x097F:
            if ch in _INDEPENDENT_VOWELS:
                out.append(_INDEPENDENT_VOWELS[ch])
                i += 1
            elif ch in _CONSONANTS:
                consonant = _CONSONANTS[ch]
                i += 1
                if i < n and text[i] == _NUKTA:
                    consonant = _NUKTA_VARIANTS.get(consonant, consonant)
                    i += 1
                if i < n and text[i] == _VIRAMA:
                    out.append(consonant)
                    i += 1
                elif i < n and text[i] in _VOWEL_SIGNS:
                    out.append(consonant + _VOWEL_SIGNS[text[i]])
                    i += 1
                elif i >= n or text[i] not in _CONSONANTS:
                    # Word-final inherent vowel (schwa) is silent in Hindi and
                    # Marathi: "सर" is "sar", not "sara".
                    out.append(consonant)
                else:
                    out.append(consonant + "a")
            elif ch in _VOWEL_SIGNS:
                out.append(_VOWEL_SIGNS[ch])
                i += 1
            elif ch in _OTHER:
                nasal = ch in ("\u0901", "\u0902")  # ँ / ं
                if nasal and out:
                    # "मंद" -> "mand", "संग" -> "sang": the nasal needs the
                    # preceding consonant's vowel when it had none.
                    if out[-1] and out[-1][-1].lower() not in "aeiou":
                        out[-1] = out[-1] + "a"
                out.append(_OTHER[ch])
                i += 1
            else:
                i += 1
        else:
            out.append(ch)
            i += 1

    return "".join(out)


def prepare_speech_text(text: str) -> str:
    """Normalise any reply into plain speakable text for the cloned voice."""
    text = (text or "").strip()
    if not text:
        return "Yes, sir."

    if has_devanagari(text):
        text = romanize_devanagari(text)

    for src, dst in _SYMBOL_MAP.items():
        if src in text:
            text = text.replace(src, dst)

    # Drop markdown emphasis / stray emoji so the model only hears words.
    text = re.sub(r"[*_`#~|]+", " ", text)
    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) < 128)
    return re.sub(r"\s{2,}", " ", text).strip() or "Yes, sir."


_model = None
_voice_state = None
_load_error: Exception | None = None
_load_lock = threading.Lock()
_generation_lock = threading.Lock()


def _load_engine():
    """Load the Pocket-TTS model + cloned voice state exactly once."""
    global _model, _voice_state, _load_error

    if _model is not None:
        return _model, _voice_state
    if _load_error is not None:
        raise _load_error

    with _load_lock:
        if _model is not None:
            return _model, _voice_state
        if _load_error is not None:
            raise _load_error

        try:
            from pocket_tts import TTSModel

            logger.info("Loading Pocket-TTS model for the cloned JARVIS voice...")
            if CONFIG_PATH.exists():
                model = TTSModel.load_model(config=str(CONFIG_PATH))
            else:
                model = TTSModel.load_model()

            voice_state = None
            if VOICE_STATE_PATH.exists():
                voice_state = torch.load(
                    VOICE_STATE_PATH, map_location=model.device, weights_only=True
                )
                logger.info(
                    "Cloned JARVIS voice state loaded (%d conditioning modules)",
                    len(voice_state),
                )
            else:
                logger.warning("Cloned voice state missing at %s", VOICE_STATE_PATH)

            _model = model
            _voice_state = voice_state
            logger.info("Pocket-TTS engine ready (sample rate %d Hz)", model.sample_rate)
        except Exception as exc:  # pragma: no cover - surfaced to the endpoint
            _load_error = exc
            logger.exception("Pocket-TTS engine failed to load")
            raise

    return _model, _voice_state


def warm_up() -> None:
    """Pre-load the engine in the background so the first reply is instant."""
    threading.Thread(target=_safe_warm_up, name="JarvisTTSWarmup", daemon=True).start()


def _safe_warm_up() -> None:
    try:
        _load_engine()
    except Exception as exc:  # pragma: no cover
        logger.warning("TTS warm-up skipped: %s", exc)


def _audio_to_wav(audio: torch.Tensor, sample_rate: int) -> bytes:
    """Encode a [channels, samples] float tensor as 16-bit PCM WAV bytes."""
    pcm = audio.detach().to("cpu", torch.float32).numpy()
    if pcm.ndim == 2:
        pcm = pcm[0] if pcm.shape[0] == 1 else pcm.mean(axis=0)
    pcm = np.clip(pcm, -1.0, 1.0)
    samples = (pcm * 32767.0).astype("<i2")

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())
    return buffer.getvalue()


def synthesize_speech(text: str, emotion: Emotion | None = None) -> bytes:
    """Synthesize ``text`` with the cloned JARVIS voice and return WAV bytes.

    Every language reaches the same cloned speaker: Devanagari (Hindi /
    Marathi) is romanised before synthesis so no reply ever falls back to a
    different voice.

    Phase 3 Enhancement: If ``emotion`` is None, it will be automatically
    detected from the text content. Prosody markers are applied to create
    natural intonation matching the detected emotion.
    """
    text = prepare_speech_text(text)

    if emotion is None:
        emotion = detect_emotion(text)

    text = apply_prosody(text, emotion)

    model, voice_state = _load_engine()

    if voice_state is None:
        raise RuntimeError(
            "Cloned voice state not found at " + str(VOICE_STATE_PATH)
        )

    with _generation_lock:
        audio = model.generate_audio(
            model_state=voice_state,
            text_to_generate=text,
            copy_state=True,
        )

    wav_bytes = _audio_to_wav(audio, model.sample_rate)
    logger.info(
        "TTS synthesized %d chars -> %.2fs audio (emotion: %s)",
        len(text),
        audio.shape[-1] / max(model.sample_rate, 1),
        emotion.value,
    )
    return wav_bytes
