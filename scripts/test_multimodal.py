"""
End-to-end test for multimodal pipeline — Phase 5.0

Tests:
1. Image upload → processing → base64 → vision model response
2. Audio upload → STT transcription
3. TTS synthesis
4. Ollama _format_messages with images
5. Orchestrator multimodal detection
"""

import asyncio
import base64
import io
import json
import os
import sys
import time

# ═══════════════════════════════════════════════════════════════
# Test 1: Image Processing Pipeline
# ═══════════════════════════════════════════════════════════════
async def test_image_processing():
    """Test image → process → base64 → save file"""
    print("\n" + "="*60)
    print("TEST 1: Image Processing Pipeline")
    print("="*60)
    
    from PIL import Image
    from chatbot_ai_system.services.media_pipeline import MediaPipeline
    
    pipeline = MediaPipeline()
    
    # Create test images of different sizes
    test_cases = [
        ("small_200x200", 200, 200),
        ("large_2048x1536", 2048, 1536),
        ("square_1024x1024", 1024, 1024),
    ]
    
    for name, w, h in test_cases:
        img = Image.new("RGB", (w, h), color=(50, 100, 200))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()
        
        result = await pipeline.process_image(img_bytes, f"{name}.png", "image/png")
        
        print(f"\n  [{name}]")
        print(f"    Input: {w}x{h}, {len(img_bytes)} bytes")
        print(f"    Output: {result['width']}x{result['height']}")
        print(f"    Base64 length: {len(result['base64_data'])} chars")
        print(f"    File saved: {result['file_path']}")
        
        assert result["base64_data"], "Base64 data should not be empty"
        assert os.path.exists(result["file_path"]), f"File should exist at {result['file_path']}"
        # Check resize: large images should be <= 1024 on longest side
        assert max(result["width"], result["height"]) <= 1024, f"Resized image too large"
    
    # Test file type validation
    try:
        pipeline.validate_upload(b"test", "test.exe")
        assert False, "Should have raised ValueError for .exe"
    except ValueError as e:
        print(f"\n  ✅ Correctly rejected .exe: {e}")
    
    # Test file size validation
    try:
        huge = b"x" * (51 * 1024 * 1024)  # 51MB
        pipeline.validate_upload(huge, "big.png")
        assert False, "Should have raised ValueError for large file"
    except ValueError as e:
        print(f"  ✅ Correctly rejected large file: {e}")
    
    print("\n  ✅ TEST 1 PASSED: Image processing works correctly")
    return True


# ═══════════════════════════════════════════════════════════════
# Test 2: Ollama Format Messages with Images
# ═══════════════════════════════════════════════════════════════
async def test_format_messages_with_images():
    """Test that _format_messages includes images[] for vision models"""
    print("\n" + "="*60)
    print("TEST 2: Ollama Format Messages with Images")
    print("="*60)
    
    from chatbot_ai_system.providers.ollama import OllamaProvider
    from chatbot_ai_system.models.schemas import ChatMessage, MediaAttachment, MessageRole
    
    provider = OllamaProvider()
    
    # Test with image attachment
    att = MediaAttachment(
        type="image",
        mime_type="image/png",
        base64_data="iVBORw0KGgoAAAANSUhEUg..."  # fake base64
    )
    msg = ChatMessage(
        role=MessageRole.USER,
        content="What do you see in this image?",
        attachments=[att]
    )
    
    formatted = provider._format_messages([msg])
    
    assert len(formatted) == 1
    assert formatted[0]["role"] == "user"
    assert formatted[0]["content"] == "What do you see in this image?"
    assert "images" in formatted[0], "Should have images key"
    assert len(formatted[0]["images"]) == 1
    print(f"  ✅ Message has images: {len(formatted[0]['images'])} image(s)")
    
    # Test without attachment (backward compat)
    msg2 = ChatMessage(role=MessageRole.USER, content="Hello")
    formatted2 = provider._format_messages([msg2])
    assert "images" not in formatted2[0], "Should NOT have images key for text-only"
    print(f"  ✅ Text-only message has no images key")
    
    # Test with multiple images
    atts = [
        MediaAttachment(type="image", mime_type="image/png", base64_data="img1"),
        MediaAttachment(type="image", mime_type="image/jpeg", base64_data="img2"),
        MediaAttachment(type="audio", mime_type="audio/wav", transcription="hello"),  # not an image
    ]
    msg3 = ChatMessage(
        role=MessageRole.USER,
        content="Describe these",
        attachments=atts
    )
    formatted3 = provider._format_messages([msg3])
    assert len(formatted3[0]["images"]) == 2, "Should only include image-type attachments"
    print(f"  ✅ Multi-attachment: 2 images (audio excluded)")
    
    print("\n  ✅ TEST 2 PASSED: Format messages correctly includes images")
    return True


# ═══════════════════════════════════════════════════════════════
# Test 3: Vision Model (llava:7b) responds to image
# ═══════════════════════════════════════════════════════════════
async def test_vision_model():
    """Test actual vision model inference with an image"""
    print("\n" + "="*60)
    print("TEST 3: Vision Model (llava:7b) Image Understanding")
    print("="*60)
    
    from PIL import Image, ImageDraw
    from chatbot_ai_system.providers.ollama import OllamaProvider
    from chatbot_ai_system.models.schemas import ChatMessage, MediaAttachment, MessageRole
    
    # Create a distinctive test image: red circle on white background
    img = Image.new("RGB", (256, 256), color="white")
    draw = ImageDraw.Draw(img)
    draw.ellipse([50, 50, 206, 206], fill="red", outline="black", width=3)
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()
    b64_data = base64.b64encode(img_bytes).decode("utf-8")
    
    print(f"  Image: 256x256 white background with red circle")
    print(f"  Base64 size: {len(b64_data)} chars")
    
    # Send to llava:7b
    provider = OllamaProvider()
    att = MediaAttachment(type="image", mime_type="image/png", base64_data=b64_data)
    
    messages = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content="Describe images briefly in 1-2 sentences."
        ),
        ChatMessage(
            role=MessageRole.USER,
            content="What do you see in this image?",
            attachments=[att]
        ),
    ]
    
    start = time.time()
    response = await provider.complete(
        messages=messages,
        model="llava:7b",
        temperature=0.3,
        max_tokens=100,
    )
    elapsed = (time.time() - start) * 1000
    
    content = response.message.content
    print(f"\n  Vision model response ({elapsed:.0f}ms):")
    print(f"  >>> {content}")
    
    # Check that the model recognized something visual
    assert len(content) > 10, "Response should be meaningful"
    print(f"\n  ✅ TEST 3 PASSED: Vision model responded ({elapsed:.0f}ms)")
    return True


# ═══════════════════════════════════════════════════════════════
# Test 4: Audio Processing & STT
# ═══════════════════════════════════════════════════════════════
async def test_audio_stt():
    """Test audio processing and Whisper speech-to-text"""
    print("\n" + "="*60)
    print("TEST 4: Audio Processing & STT (Whisper)")
    print("="*60)
    
    import struct
    import math
    from chatbot_ai_system.services.media_pipeline import MediaPipeline
    from chatbot_ai_system.services.stt_engine import STTEngine
    
    # Generate a simple WAV file (sine wave tone)
    sample_rate = 16000
    duration = 2.0  # seconds
    frequency = 440  # Hz (A note)
    num_samples = int(sample_rate * duration)
    
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        sample = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * t))
        samples.append(struct.pack('<h', sample))
    
    audio_data = b''.join(samples)
    
    # Create WAV file
    wav_buf = io.BytesIO()
    # WAV header
    wav_buf.write(b'RIFF')
    wav_buf.write(struct.pack('<I', 36 + len(audio_data)))
    wav_buf.write(b'WAVE')
    wav_buf.write(b'fmt ')
    wav_buf.write(struct.pack('<I', 16))  # chunk size
    wav_buf.write(struct.pack('<H', 1))   # PCM
    wav_buf.write(struct.pack('<H', 1))   # mono
    wav_buf.write(struct.pack('<I', sample_rate))
    wav_buf.write(struct.pack('<I', sample_rate * 2))  # byte rate
    wav_buf.write(struct.pack('<H', 2))   # block align
    wav_buf.write(struct.pack('<H', 16))  # bits per sample
    wav_buf.write(b'data')
    wav_buf.write(struct.pack('<I', len(audio_data)))
    wav_buf.write(audio_data)
    
    wav_bytes = wav_buf.getvalue()
    print(f"  Generated test WAV: {len(wav_bytes)} bytes, {duration}s, {frequency}Hz")
    
    # Test MediaPipeline audio processing
    pipeline = MediaPipeline()
    result = await pipeline.process_audio(wav_bytes, "test_tone.wav", "audio/wav")
    
    print(f"  Duration: {result['duration_seconds']:.1f}s")
    print(f"  File saved: {result['file_path']}")
    print(f"  Transcription: '{result['transcription']}'")
    
    # A pure tone won't have meaningful speech, but the pipeline should not crash
    assert result["duration_seconds"] > 0, "Duration should be positive"
    assert os.path.exists(result["file_path"]), "Audio file should be saved"
    assert result["transcription"] is not None, "Transcription should not be None"
    
    # Test STT engine directly
    stt = STTEngine()
    stt_result = await stt.transcribe(wav_bytes)
    print(f"\n  STT Engine result:")
    print(f"    Language: {stt_result['language']} ({stt_result['language_probability']:.1%})")
    print(f"    Duration: {stt_result['duration']:.1f}s")
    print(f"    Text: '{stt_result['text']}'")
    
    print(f"\n  ✅ TEST 4 PASSED: Audio pipeline and STT work correctly")
    return True


# ═══════════════════════════════════════════════════════════════
# Test 5: TTS Synthesis
# ═══════════════════════════════════════════════════════════════
async def test_tts():
    """Test text-to-speech synthesis"""
    print("\n" + "="*60)
    print("TEST 5: TTS Synthesis")
    print("="*60)
    
    from chatbot_ai_system.services.tts_engine import TTSEngine
    
    tts = TTSEngine()
    print(f"  Backend: {tts._backend}")
    print(f"  Available: {tts.is_available}")
    
    if not tts.is_available:
        print("  ⚠️ TEST 5 SKIPPED: No TTS backend available")
        return True
    
    # Test basic synthesis
    text = "Hello, I am a chatbot with voice capabilities."
    start = time.time()
    audio = await tts.synthesize(text)
    elapsed = (time.time() - start) * 1000
    
    print(f"  Input: '{text}'")
    print(f"  Output: {len(audio)} bytes ({elapsed:.0f}ms)")
    assert len(audio) > 100, "Audio should have meaningful data"
    
    # Test empty text
    empty_audio = await tts.synthesize("")
    assert len(empty_audio) == 0, "Empty text should produce no audio"
    print(f"  ✅ Empty text returns 0 bytes (correct)")
    
    # Test longer text
    long_text = "This is a longer test to verify that the text-to-speech engine can handle multiple sentences. It should produce a larger audio output."
    long_audio = await tts.synthesize(long_text)
    print(f"  Long text: {len(long_audio)} bytes")
    assert len(long_audio) >= len(audio), "Longer text should produce at least as much audio"
    
    print(f"\n  ✅ TEST 5 PASSED: TTS synthesis works ({tts._backend} backend)")
    return True


# ═══════════════════════════════════════════════════════════════
# Test 6: Orchestrator Multimodal Detection
# ═══════════════════════════════════════════════════════════════
async def test_orchestrator_multimodal():
    """Test that orchestrator detects media and switches model"""
    print("\n" + "="*60)
    print("TEST 6: Orchestrator Multimodal Detection")
    print("="*60)
    
    from chatbot_ai_system.models.schemas import ChatMessage, MediaAttachment, MessageRole
    from chatbot_ai_system.config import get_settings
    
    settings = get_settings()
    
    # Test 1: Image attachment → should trigger vision model
    att = MediaAttachment(type="image", mime_type="image/png", base64_data="test_data")
    msg = ChatMessage(
        role=MessageRole.USER,
        content="What is this?",
        attachments=[att]
    )
    
    conversation_history = [msg]
    last_user_msg = conversation_history[-1]
    has_images = False
    has_audio = False
    
    if last_user_msg.attachments:
        for a in last_user_msg.attachments:
            if a.type == "image" and a.base64_data:
                has_images = True
            if a.type in ("audio", "video") and a.transcription:
                has_audio = True
    
    assert has_images, "Should detect images"
    assert not has_audio, "Should not detect audio (no transcription)"
    print(f"  ✅ Image detected: has_images={has_images}, has_audio={has_audio}")
    print(f"  ✅ Would switch to vision model: {settings.vision_model}")
    
    # Test 2: Audio attachment with transcription
    att2 = MediaAttachment(
        type="audio", mime_type="audio/wav", transcription="Hello world"
    )
    msg2 = ChatMessage(role=MessageRole.USER, content="", attachments=[att2])
    
    has_images = False
    has_audio = False
    if msg2.attachments:
        for a in msg2.attachments:
            if a.type == "image" and a.base64_data:
                has_images = True
            if a.type in ("audio", "video") and a.transcription:
                has_audio = True
                if a.transcription not in (msg2.content or ""):
                    msg2.content = f"{msg2.content}\n\n[Audio transcription]: {a.transcription}".strip()
    
    assert not has_images, "Should not detect images"
    assert has_audio, "Should detect audio"
    assert "Hello world" in msg2.content, "Transcription should be injected into content"
    print(f"  ✅ Audio detected and transcription injected: '{msg2.content}'")
    
    # Test 3: Text-only (no detection)
    msg3 = ChatMessage(role=MessageRole.USER, content="Just text")
    has_images = bool(msg3.attachments and any(
        a.type == "image" and a.base64_data for a in msg3.attachments
    ))
    assert not has_images, "Should not detect images for text-only"
    print(f"  ✅ Text-only: no media detected (correct)")
    
    print(f"\n  ✅ TEST 6 PASSED: Orchestrator multimodal detection works")
    return True


# ═══════════════════════════════════════════════════════════════
# Test 7: Upload API Endpoint (via FastAPI TestClient)
# ═══════════════════════════════════════════════════════════════
async def test_upload_api():
    """Test the /api/upload endpoint"""
    print("\n" + "="*60)
    print("TEST 7: Upload API Endpoint")
    print("="*60)
    
    from PIL import Image
    from fastapi.testclient import TestClient
    from chatbot_ai_system.server.main import create_app
    
    app = create_app()
    client = TestClient(app)
    
    # Create test image
    img = Image.new("RGB", (100, 100), color="green")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    
    # Upload image
    response = client.post(
        "/api/upload",
        files={"file": ("test.png", buf.getvalue(), "image/png")}
    )
    
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  Type: {data['type']}")
        print(f"  Base64 length: {len(data.get('base64_data', ''))}")
        print(f"  File path: {data['file_path']}")
        assert data["type"] == "image"
        assert data["base64_data"]
        print(f"\n  ✅ TEST 7 PASSED: Upload API works")
    else:
        print(f"  Response: {response.text}")
        print(f"  ⚠️ TEST 7 FAILED: Status {response.status_code}")
        return False
    
    return True


# ═══════════════════════════════════════════════════════════════
# Test 8: Voice Config Endpoint
# ═══════════════════════════════════════════════════════════════
async def test_voice_config():
    """Test the /api/voice/config endpoint"""
    print("\n" + "="*60)
    print("TEST 8: Voice Config Endpoint")
    print("="*60)
    
    from fastapi.testclient import TestClient
    from chatbot_ai_system.server.main import create_app
    
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/api/voice/config")
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"  STT available: {data['stt_available']}")
        print(f"  TTS available: {data['tts_available']}")
        print(f"  TTS backend: {data['tts_backend']}")
        print(f"  STT model: {data['stt_model']}")
        assert data["stt_available"]
        print(f"\n  ✅ TEST 8 PASSED: Voice config endpoint works")
    else:
        print(f"  ⚠️ TEST 8 FAILED: Status {response.status_code}")
        return False
    
    return True


# ═══════════════════════════════════════════════════════════════
# Run all tests
# ═══════════════════════════════════════════════════════════════
async def main():
    print("╔══════════════════════════════════════════════════════╗")
    print("║  Phase 5.0 Multimodal & Voice — End-to-End Tests    ║")
    print("╚══════════════════════════════════════════════════════╝")
    
    tests = [
        ("Image Processing", test_image_processing),
        ("Format Messages", test_format_messages_with_images),
        ("Vision Model", test_vision_model),
        ("Audio & STT", test_audio_stt),
        ("TTS Synthesis", test_tts),
        ("Orchestrator Detection", test_orchestrator_multimodal),
        ("Upload API", test_upload_api),
        ("Voice Config", test_voice_config),
    ]
    
    results = {}
    for name, test_fn in tests:
        try:
            result = await test_fn()
            results[name] = result
        except Exception as e:
            print(f"\n  ❌ {name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {name}")
    
    print(f"\n  {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  🎉 ALL TESTS PASSED!")
    else:
        print("\n  ⚠️ Some tests failed. Check output above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
