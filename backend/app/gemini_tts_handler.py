"""
TTS (Text-to-Speech) Handler - ALPHA IMPLEMENTATION

This module provides streaming TTS functionality using Google's Gemini Live API.
This is an ALPHA-level implementation with custom asyncio/threading integration.

FUTURE MIGRATION PLAN:
Once LangChain adds native support for Gemini TTS streaming, this implementation
should be migrated to use LangChain's standardized TTS interface for better
maintainability and consistency with the rest of the application.

Current implementation uses:
- Direct Gemini Live API calls
- Custom asyncio/threading bridge for Flask compatibility
- Manual PCM audio processing and streaming
- Custom queue management for real-time delivery

This approach was necessary due to the lack of LangChain TTS support for Gemini
at the time of implementation.
"""

from flask import Blueprint, Response, request, stream_with_context
import os
import sys
import logging
import threading
import asyncio
import queue
import json
from google import genai
from google.genai import types

# Blueprint for text-to-speech streaming
tts_bp = Blueprint('tts', __name__)

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO, 
                    format='%(asctime)s [TTS] %(message)s')
logger = logging.getLogger('tts_handler')

# Initialize Gemini client
client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key=os.environ.get("GOOGLE_API_KEY"),
)

# Voice configuration for Live API
LIVE_CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    media_resolution="MEDIA_RESOLUTION_MEDIUM",
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Iapetus")
        )
    ),
)

# The Live API model
LIVE_MODEL = "models/gemini-2.5-flash-preview-native-audio-dialog"

@tts_bp.route('/tts-stream', methods=['GET', 'POST'])
def tts_stream():
    """
    Stream TTS audio using Gemini Live API
    
    ALPHA IMPLEMENTATION NOTE:
    This endpoint uses a custom asyncio/threading bridge to integrate
    Gemini's async Live API with Flask's synchronous request handling.
    This should be replaced with LangChain TTS integration when available.
    """
    # Support both GET (query param) and POST (JSON body) for 'text'
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        text = data.get('text')
    else:
        text = request.args.get('text')
    if not text:
        return "Missing ?text= param", 400

    # Add prefix to provide context for TTS
    text = "Read aloud the following response to a question about town's bylaws: " + text

    logger.info(f"TTS request - text length: {len(text)} chars")
    
    # Use a standard Python queue to avoid asyncio complexities in Flask context
    audio_queue = queue.Queue()
    end_event = threading.Event()
    
    # Function to process text with Live API in a background thread
    def process_live_tts():
        """
        ALPHA IMPLEMENTATION: Custom asyncio/threading bridge
        
        This function runs the async Gemini Live API in a separate thread
        with its own event loop, then communicates with the main Flask thread
        via a queue. This is a workaround for Flask's synchronous nature.
        
        TODO: Replace with LangChain TTS when available.
        """
        try:
            # Run asyncio event loop for Live API
            async def run_live_api():
                try:
                    async with client.aio.live.connect(model=LIVE_MODEL, config=LIVE_CONFIG) as session:
                        # Send the text to the model
                        await session.send(input=text, end_of_turn=True)
                        
                        # Receive audio chunks
                        chunk_count = 0
                        total_bytes = 0
                        
                        turn = session.receive()
                        async for response in turn:
                            if data := response.data:
                                # Filter out JSON metadata frames
                                if isinstance(data, (bytes, bytearray)) and data.lstrip().startswith(b'{'):
                                    continue
                                # Treat as raw PCM audio
                                chunk_count += 1
                                total_bytes += len(data)
                                audio_queue.put(data)
                        
                        logger.info(f"TTS generation complete - {chunk_count} chunks, {total_bytes} bytes")
                except Exception as e:
                    logger.error(f"Live API error: {str(e)}")
                finally:
                    # Signal end of stream
                    end_event.set()
            
            # Run asyncio event loop
            asyncio.run(run_live_api())
        except Exception as e:
            logger.error(f"Error in TTS thread: {str(e)}")
            end_event.set()
    
    # Start the TTS processing in a background thread
    tts_thread = threading.Thread(target=process_live_tts)
    tts_thread.daemon = True
    tts_thread.start()
    
    # Stream raw PCM data directly to client
    @stream_with_context
    def generate_stream_internal():
        """
        ALPHA IMPLEMENTATION: Custom streaming generator
        
        This generator function bridges the asyncio-based audio generation
        with Flask's streaming response. It manually handles PCM audio
        formatting and real-time delivery.
        
        TODO: Replace with LangChain streaming interface when available.
        """
        output_chunks = 0
        output_bytes = 0
        
        try:
            # Send audio format info as first chunk (JSON header)
            format_info = {
                "format": "pcm",
                "sampleRate": 24000,
                "channels": 1,
                "bitsPerSample": 16
            }
            header = json.dumps(format_info).encode('utf-8') + b'\n'
            yield header
            
            while True:
                try:
                    # Try to get PCM chunk from queue
                    pcm_chunk = audio_queue.get(timeout=0.05)
                    yield pcm_chunk
                    output_chunks += 1
                    output_bytes += len(pcm_chunk)
                except queue.Empty:
                    # Check if we're done
                    if end_event.is_set():
                        # Drain any remaining chunks
                        while not audio_queue.empty():
                            try:
                                pcm_chunk = audio_queue.get(block=False)
                                yield pcm_chunk
                                output_chunks += 1
                                output_bytes += len(pcm_chunk)
                            except queue.Empty:
                                break
                        break
                    # Continue waiting if not done yet
                    continue

        except Exception as e:
            logger.error(f"Error in stream generation: {str(e)}")
        
        logger.info(f"TTS stream complete - {output_chunks} chunks, {output_bytes} bytes")

    return Response(generate_stream_internal(), mimetype="application/octet-stream") 