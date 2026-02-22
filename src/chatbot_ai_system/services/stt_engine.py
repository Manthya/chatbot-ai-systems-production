"""
STT Engine — Phase 5.0

Speech-to-Text using faster-whisper for real-time and batch transcription.
"""

import io
import logging
import os
import tempfile
from typing import AsyncGenerator, Optional

from chatbot_ai_system.config import get_settings

logger = logging.getLogger(__name__)

# Singleton model instance (lazy loaded)
_whisper_model = None


def _get_whisper_model():
    """Lazy-load the Whisper model (heavy resource, load once)."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        settings = get_settings()
        logger.info(f"Loading Whisper model: {settings.stt_model} on {settings.stt_device} (int8)")
        _whisper_model = WhisperModel(
            settings.stt_model,
            device=settings.stt_device,
            compute_type="int8",
        )
        logger.info("Whisper model loaded successfully")
    return _whisper_model


class STTEngine:
    """Speech-to-Text engine wrapping faster-whisper."""

    def __init__(self):
        self.settings = get_settings()

    async def transcribe(self, audio_bytes: bytes, language: Optional[str] = None) -> dict:
        """
        Transcribe audio bytes to text.

        Args:
            audio_bytes: Raw audio data (WAV, MP3, etc.)
            language: Optional language code (e.g., "en", "ja")

        Returns:
            dict with keys: text, language, language_probability, duration
        """
        model = _get_whisper_model()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            kwargs = {"beam_size": 5}
            if language:
                kwargs["language"] = language

            segments, info = model.transcribe(tmp_path, **kwargs)
            text = " ".join(segment.text.strip() for segment in segments)

            result = {
                "text": text,
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
            }

            logger.info(
                f"STT: {info.language} ({info.language_probability:.1%}), "
                f"{len(text)} chars, {info.duration:.1f}s"
            )
            return result

        finally:
            os.unlink(tmp_path)

    async def transcribe_stream(
        self, audio_chunks: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[str, None]:
        """
        Stream transcription: accumulate audio chunks, transcribe on silence.

        For real-time voice: VAD detects speech end, then this transcribes the segment.

        Yields:
            Transcribed text segments
        """
        buffer = io.BytesIO()

        async for chunk in audio_chunks:
            buffer.write(chunk)

            # Transcribe when buffer reaches ~2 seconds of audio (16kHz, 16-bit mono = 32KB/s)
            if buffer.tell() >= 64000:  # ~2 seconds
                buffer.seek(0)
                result = await self.transcribe(buffer.read())
                if result["text"].strip():
                    yield result["text"]
                buffer = io.BytesIO()

        # Final flush
        if buffer.tell() > 0:
            buffer.seek(0)
            result = await self.transcribe(buffer.read())
            if result["text"].strip():
                yield result["text"]
