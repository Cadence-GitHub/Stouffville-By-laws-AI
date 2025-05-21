from flask import Blueprint, Response, request, stream_with_context
import subprocess
import os
import time
import sys
import logging
import threading
import asyncio
import queue
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
    """Stream TTS audio using Gemini Live API"""
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

    logger.info(f"Received TTS request - text length: {len(text)} chars - first 50 chars: {text[:50]}...")
    
    # Use a standard Python queue to avoid asyncio complexities in Flask context
    audio_queue = queue.Queue()
    end_event = threading.Event()
    request_start_time = time.time() # Capture start time for overall request
    
    # Function to process text with Live API in a background thread
    def process_live_tts():
        try:
            start_time = time.time()
            logger.info("Starting Live API TTS session")
            
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
                                # Filter out JSON metadata frames (e.g. setupComplete)
                                # These start with '{' when encoded
                                if isinstance(data, (bytes, bytearray)) and data.lstrip().startswith(b'{'):
                                    continue
                                # Treat as raw PCM audio
                                chunk_count += 1
                                chunk_size = len(data)
                                total_bytes += chunk_size
                                logger.info(f"Received audio chunk #{chunk_count}: {chunk_size} bytes (total: {total_bytes} bytes)")
                                audio_queue.put(data)
                        
                        logger.info(f"TTS generation complete - received {chunk_count} chunks, {total_bytes} bytes in {time.time() - start_time:.2f}s")
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
    
    # Spawn ffmpeg to transcode raw PCM to MP3
    ffmpeg_proc = subprocess.Popen(
        [
            "ffmpeg",
            "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", "pipe:0",
            "-f", "mp3", "-b:a", "64k", "pipe:1"
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE  # Capture stderr
    )

    # Thread to log ffmpeg stderr
    def log_ffmpeg_stderr():
        try:
            for line in iter(ffmpeg_proc.stderr.readline, b''):
                logger.error(f"ffmpeg stderr: {line.decode().strip()}")
        except Exception as e:
            logger.error(f"Error reading ffmpeg stderr: {str(e)}")

    ffmpeg_stderr_thread = threading.Thread(target=log_ffmpeg_stderr)
    ffmpeg_stderr_thread.daemon = True
    ffmpeg_stderr_thread.start()
    
    # Stream the audio data through ffmpeg to the client
    @stream_with_context
    def generate_stream_internal():
        stream_start_time = time.time()
        logger.info("Starting to send MP3 data to client (threaded stdout)")
        output_chunks = 0
        output_bytes = 0
        
        mp3_output_queue = queue.Queue()
        ffmpeg_stdout_reader_finished_event = threading.Event()

        def ffmpeg_stdout_reader():
            try:
                while True:
                    if not ffmpeg_proc or ffmpeg_proc.poll() is not None:
                        logger.info("ffmpeg_stdout_reader: ffmpeg process appears to have exited.")
                        break
                    if not ffmpeg_proc.stdout or ffmpeg_proc.stdout.closed:
                        logger.info("ffmpeg_stdout_reader: ffmpeg stdout pipe closed.")
                        break
                    
                    try:
                        chunk = ffmpeg_proc.stdout.read(1024) # This can block
                        if not chunk: # EOF
                            logger.info("ffmpeg_stdout_reader: Received EOF from ffmpeg stdout.")
                            break
                        mp3_output_queue.put(chunk)
                    except BrokenPipeError:
                        logger.info("ffmpeg_stdout_reader: Broken pipe reading ffmpeg stdout (ffmpeg likely exited).")
                        break
                    except ValueError: # Can happen if reading from an already closed pipe
                        logger.info("ffmpeg_stdout_reader: ValueError reading from ffmpeg stdout (pipe likely closed).")
                        break
                    except Exception as e:
                        logger.error(f"ffmpeg_stdout_reader: Unexpected error reading ffmpeg stdout: {str(e)}")
                        break
            finally:
                logger.info("ffmpeg_stdout_reader: Exiting and setting finished event.")
                ffmpeg_stdout_reader_finished_event.set()

        stdout_reader_thread = threading.Thread(target=ffmpeg_stdout_reader)
        stdout_reader_thread.daemon = True
        stdout_reader_thread.start()

        try:
            yield b'' # Start the response

            input_to_ffmpeg_closed = False
            
            while True:
                # 1. Feed PCM to ffmpeg if its stdin is open and there's data
                if not input_to_ffmpeg_closed:
                    try:
                        pcm_chunk = audio_queue.get(block=False) # Non-blocking
                        if ffmpeg_proc.stdin and not ffmpeg_proc.stdin.closed:
                            ffmpeg_proc.stdin.write(pcm_chunk)
                            ffmpeg_proc.stdin.flush()
                        else:
                            logger.warning("generate_stream_internal: ffmpeg stdin found closed/unavailable while trying to write PCM.")
                            input_to_ffmpeg_closed = True
                    except queue.Empty:
                        # PCM queue is empty for now. If Gemini is also done, close ffmpeg's stdin.
                        if end_event.is_set():
                            if ffmpeg_proc.stdin and not ffmpeg_proc.stdin.closed:
                                logger.info("generate_stream_internal: Gemini done, PCM queue empty. Closing ffmpeg stdin.")
                                ffmpeg_proc.stdin.close()
                            input_to_ffmpeg_closed = True
                    except (BrokenPipeError, Exception) as e_write:
                        logger.error(f"generate_stream_internal: Error writing to ffmpeg stdin: {str(e_write)}. Marking input as closed.")
                        if ffmpeg_proc.stdin and not ffmpeg_proc.stdin.closed:
                            try: ffmpeg_proc.stdin.close()
                            except Exception as e_close: logger.error(f"Error closing ffmpeg stdin after write error: {e_close}")
                        input_to_ffmpeg_closed = True
                
                # 2. Yield MP3 data from the mp3_output_queue
                mp3_data_yielded_this_iteration = False
                try:
                    mp3_chunk = mp3_output_queue.get(timeout=0.01) # Short timeout
                    yield mp3_chunk
                    output_chunks += 1
                    output_bytes += len(mp3_chunk)
                    mp3_data_yielded_this_iteration = True
                except queue.Empty:
                    pass # No MP3 data in queue right now

                # 3. Check for exit conditions
                # ffmpeg process died, and stdout reader has also finished
                if ffmpeg_proc and ffmpeg_proc.poll() is not None and ffmpeg_stdout_reader_finished_event.is_set():
                    logger.info(f"ffmpeg process exited (code: {ffmpeg_proc.returncode}) and stdout reader finished. Draining MP3 queue.")
                    break 
                
                # Normal exit: input to ffmpeg is closed, stdout reader has finished, and mp3 queue is empty
                if input_to_ffmpeg_closed and ffmpeg_stdout_reader_finished_event.is_set() and mp3_output_queue.empty():
                    logger.info("generate_stream_internal: All conditions met for exiting main loop (input closed, stdout processed, mp3 queue empty).")
                    break

                # If nothing happened and we are just waiting for threads/events, short sleep to be nice to CPU
                if not input_to_ffmpeg_closed and audio_queue.empty() and not end_event.is_set() and not mp3_data_yielded_this_iteration:
                    time.sleep(0.01)


            logger.info("generate_stream_internal: Main stream loop finished.")
            
            # Drain any final data from mp3_output_queue
            while not mp3_output_queue.empty():
                try:
                    mp3_chunk = mp3_output_queue.get(block=False)
                    yield mp3_chunk
                    output_chunks += 1
                    output_bytes += len(mp3_chunk)
                    logger.info(f"generate_stream_internal: Yielded final MP3 chunk from drain: {len(mp3_chunk)} bytes")
                except queue.Empty:
                    break
            logger.info(f"End of MP3 stream - sent {output_chunks} chunks, {output_bytes} bytes in {time.time() - stream_start_time:.2f}s")

        except Exception as e_outer:
            logger.error(f"Outer error in generate_stream_internal: {str(e_outer)}")
        
        finally:
            logger.info("generate_stream_internal: Entering finally block.")

            # Ensure ffmpeg stdin is closed if it hasn't been (and process exists)
            if ffmpeg_proc and ffmpeg_proc.stdin and not ffmpeg_proc.stdin.closed:
                logger.info("generate_stream_internal (finally): Ensuring ffmpeg stdin is closed.")
                try: ffmpeg_proc.stdin.close()
                except Exception: pass # Ignore errors on close

            # Wait for the stdout reader thread to finish
            if stdout_reader_thread.is_alive():
                logger.info("generate_stream_internal (finally): Waiting for stdout_reader_thread to join.")
                stdout_reader_thread.join(timeout=2.0) # Shorter timeout as it should exit quickly if ffmpeg is done
                if stdout_reader_thread.is_alive():
                    logger.warning("generate_stream_internal (finally): ffmpeg stdout_reader_thread did not join in time.")
            
            # Terminate ffmpeg process
            if ffmpeg_proc:
                if ffmpeg_proc.poll() is None: # Check if process is still running
                    logger.info("generate_stream_internal (finally): Terminating ffmpeg process.")
                    ffmpeg_proc.terminate()
                    try:
                        ffmpeg_proc.wait(timeout=2) # Wait for termination
                        logger.info(f"generate_stream_internal (finally): ffmpeg process terminated with code {ffmpeg_proc.returncode}.")
                    except subprocess.TimeoutExpired:
                        logger.warning("generate_stream_internal (finally): ffmpeg process did not terminate in time, killing.")
                        ffmpeg_proc.kill()
                        ffmpeg_proc.wait() # Wait for kill
                        logger.info("generate_stream_internal (finally): ffmpeg process killed.")
                else:
                    logger.info(f"generate_stream_internal (finally): ffmpeg process already exited with code {ffmpeg_proc.returncode}.")
                
                # Ensure stderr is fully read and closed
                if ffmpeg_proc.stderr:
                    try: 
                        # Drain remaining stderr
                        for line in iter(ffmpeg_proc.stderr.readline, b''): logger.error(f"ffmpeg stderr (finally drain): {line.decode().strip()}")
                        ffmpeg_proc.stderr.close()
                    except Exception as e_close_stderr:
                        logger.error(f"generate_stream_internal (finally): Error closing/draining ffmpeg stderr pipe: {str(e_close_stderr)}")
            
            if ffmpeg_stderr_thread.is_alive():
                ffmpeg_stderr_thread.join(timeout=1) 
                if ffmpeg_stderr_thread.is_alive():
                    logger.warning("generate_stream_internal (finally): ffmpeg stderr logging thread did not join.")
            
            logger.info(f"TTS stream processing completed in {time.time() - stream_start_time:.2f}s. Final status: {output_chunks} MP3 chunks, {output_bytes} bytes.")

    return Response(generate_stream_internal(), mimetype="audio/mpeg") 