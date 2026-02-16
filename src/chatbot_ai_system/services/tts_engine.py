"""
TTS Engine — Phase 5.0

Text-to-Speech for voice conversation responses.
Uses subprocess-based synthesis (piper-tts or system TTS as fallback).
"""

import io
import logging
import subprocess
import tempfile
import os
import shutil
from typing import AsyncGenerator, Optional

from chatbot_ai_system.config import get_settings

logger = logging.getLogger(__name__)


class TTSEngine:
    """Text-to-Speech engine with multiple backend support."""

    def __init__(self):
        self.settings = get_settings()
        self.voice = self.settings.tts_voice
        self._backend = self._detect_backend()
        logger.info(f"TTS Engine initialized with backend: {self._backend}")

    def _detect_backend(self) -> str:
        """Detect available TTS backend."""
        # Check for piper-tts
        if shutil.which("piper"):
            return "piper"
        
        # Check for macOS say command
        if shutil.which("say"):
            return "macos_say"
        
        # Check for espeak
        if shutil.which("espeak-ng") or shutil.which("espeak"):
            return "espeak"
        
        logger.warning("No TTS backend found. Voice output will be unavailable.")
        return "none"

    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        """
        Convert text to audio bytes (WAV format).
        
        Args:
            text: Text to synthesize
            voice: Optional voice override
        
        Returns:
            WAV audio bytes
        """
        if not text.strip():
            return b""

        voice = voice or self.voice

        if self._backend == "piper":
            return await self._synthesize_piper(text, voice)
        elif self._backend == "macos_say":
            return await self._synthesize_macos(text)
        elif self._backend == "espeak":
            return await self._synthesize_espeak(text)
        else:
            logger.error("No TTS backend available")
            return b""

    async def _synthesize_piper(self, text: str, voice: str) -> bytes:
        """Synthesize using piper-tts."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            proc = subprocess.run(
                ["piper", "--model", voice, "--output_file", tmp_path],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )
            if proc.returncode != 0:
                logger.error(f"Piper TTS failed: {proc.stderr.decode()}")
                return b""
            
            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    async def _synthesize_macos(self, text: str) -> bytes:
        """Synthesize using macOS `say` command (AIFF → WAV)."""
        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
            tmp_path = tmp.name

        wav_path = tmp_path.replace(".aiff", ".wav")

        try:
            # Generate AIFF with natural speech rate
            proc = subprocess.run(
                ["say", "-r", "175", "-o", tmp_path, text],
                capture_output=True,
                timeout=30,
            )
            if proc.returncode != 0:
                logger.error(f"macOS say failed: {proc.stderr.decode()}")
                return b""

            # Convert to WAV using afconvert (built-in macOS)
            proc = subprocess.run(
                ["afconvert", "-f", "WAVE", "-d", "LEI16@22050", tmp_path, wav_path],
                capture_output=True,
                timeout=10,
            )
            if proc.returncode != 0:
                logger.error(f"afconvert failed: {proc.stderr.decode()}")
                return b""

            with open(wav_path, "rb") as f:
                return f.read()

        finally:
            for p in [tmp_path, wav_path]:
                if os.path.exists(p):
                    os.unlink(p)

    async def _synthesize_espeak(self, text: str) -> bytes:
        """Synthesize using espeak-ng."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            cmd = "espeak-ng" if shutil.which("espeak-ng") else "espeak"
            proc = subprocess.run(
                [cmd, "-w", tmp_path, text],
                capture_output=True,
                timeout=30,
            )
            if proc.returncode != 0:
                logger.error(f"espeak TTS failed: {proc.stderr.decode()}")
                return b""

            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    async def synthesize_stream(
        self, text_chunks: AsyncGenerator[str, None]
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream TTS: synthesize each text chunk as it arrives from LLM.
        Yields WAV audio bytes for each chunk.
        """
        buffer = ""
        # Synthesize on sentence boundaries for natural speech
        sentence_endings = {".", "!", "?", "\n"}

        async for chunk in text_chunks:
            buffer += chunk
            
            # Check for sentence boundary
            if buffer and buffer[-1] in sentence_endings and len(buffer) > 10:
                audio = await self.synthesize(buffer.strip())
                if audio:
                    yield audio
                buffer = ""

        # Final flush
        if buffer.strip():
            audio = await self.synthesize(buffer.strip())
            if audio:
                yield audio

    @property
    def is_available(self) -> bool:
        """Check if TTS is available."""
        return self._backend != "none"
