# TTS (Text-to-Speech) Module

**Alpha Implementation - Separate from Main Application**

This module provides streaming text-to-speech functionality for the Stouffville By-laws AI Demo application. It's designed as a standalone module to keep the experimental TTS features separate from the core application code.

## Files

### Frontend Files
- `static/tts.js` - Main TTS functionality module
- `static/tts.css` - TTS-specific styles and button states

### Backend Files
- `gemini_tts_handler.py` - Flask blueprint for TTS streaming endpoint
- `TTS_README.md` - This documentation file

## Features

### Frontend Features
- **Streaming Audio**: Real-time audio streaming using Web Audio API
- **Smart Text Extraction**: Automatically extracts answer content, excluding source references
- **Button State Management**: Visual feedback for loading, playing, and error states
- **Audio Session Control**: Stop/start functionality with proper cleanup
- **Cross-browser Compatibility**: Uses Web Audio API with fallbacks

### Backend Features
- **Gemini Live API Integration**: Direct integration with Google's Gemini Live API for TTS
- **Streaming Response**: Real-time audio streaming to frontend without buffering
- **PCM Audio Processing**: Handles raw 16-bit PCM audio data from Gemini
- **Async Processing**: Non-blocking audio generation using asyncio and threading
- **Error Handling**: Robust error handling for API failures and stream interruptions

## Usage

### Automatic Initialization

The TTS module automatically initializes when the DOM is ready. No manual setup required.

### HTML Structure

Add TTS buttons to any answer container:

```html
<div class="answer-container">
    <h3>Answer Title</h3>
    <div>Answer content goes here...</div>
    <button type="button" class="tts-button">Speak aloud</button>
</div>
```

### Manual Control

If you need to control TTS programmatically:

```javascript
// Stop all active TTS sessions
TTSModule.stopAll();

// Reinitialize after adding dynamic content
TTSModule.reinitialize();
```

## Button States

The TTS button automatically changes appearance based on state:

- **Default**: Green "Speak aloud" button
- **Loading**: Yellow "Loading..." button (disabled)
- **Playing**: Red "Stop" button
- **Error**: Returns to default state

## Technical Details

### Frontend Audio Processing

- **Source Sample Rate**: 24kHz (Gemini TTS output)
- **Target Sample Rate**: Browser's audio context rate (typically 44.1kHz)
- **Buffer Size**: 4096 samples
- **Resampling**: Linear interpolation for sample rate conversion

### Backend TTS Processing

- **API Model**: `models/gemini-2.5-flash-preview-native-audio-dialog`
- **Voice Configuration**: Iapetus voice with medium media resolution
- **Audio Format**: 16-bit PCM, 24kHz, mono channel
- **Threading Model**: Background asyncio processing with Flask streaming
- **Queue Management**: Python queue for thread-safe audio chunk handling

### Stream Format

The `/tts-stream` endpoint provides:
- **HTTP Method**: GET with `?text=` parameter or POST with JSON body
- **Response Format**: `application/octet-stream`
- **Header**: JSON metadata (first line) with format information
- **Body**: Raw 16-bit PCM audio data, little-endian byte order

### Memory Management

- **Frontend**: Automatic cleanup of old audio data to prevent memory growth
- **Frontend**: Proper disconnection of Web Audio nodes and session controllers
- **Backend**: Streaming response prevents memory accumulation on server
- **Backend**: Automatic cleanup of asyncio tasks and audio queues

## Browser Support

- **Chrome/Edge**: Full support
- **Firefox**: Full support
- **Safari**: Full support (with user gesture requirement)
- **Mobile**: Supported with autoplay policy considerations

## Error Handling

- Network errors are caught and displayed to user
- Audio context issues are handled gracefully
- Stream interruptions don't crash the application
- Failed sessions clean up automatically

## Development Notes

This is an **alpha implementation** designed to be:
- **Modular**: Completely separate from main application code
- **Self-contained**: No dependencies on main application functions
- **Easy to remove**: Can be disabled by simply not including the files
- **Extensible**: Clean API for future enhancements

### Backend Implementation Notes

The current backend implementation (`gemini_tts_handler.py`) is also **alpha-level** and uses:
- Direct Gemini Live API calls with custom asyncio/threading integration
- Manual PCM audio processing and streaming
- Custom queue management for real-time audio delivery

**Future Migration Plan**: Once LangChain adds native support for Gemini TTS streaming, this implementation should be migrated to use LangChain's standardized TTS interface for better maintainability and consistency with the rest of the application.

## Future Enhancements

### Frontend Enhancements
- Volume control
- Playback speed adjustment
- Audio visualization
- Better mobile experience
- Offline TTS support

### Backend Enhancements
- **LangChain Integration**: Migrate to LangChain TTS interface when available
- Voice selection and configuration options
- Audio format options (MP3, WAV, etc.)
- Caching for frequently requested text
- Rate limiting and usage monitoring
- Support for multiple TTS providers

## Troubleshooting

### TTS Not Working
1. Check browser console for errors
2. Ensure `/tts-stream` endpoint is available
3. Verify user has interacted with page (autoplay policy)
4. Check network connectivity
5. Verify `GOOGLE_API_KEY` environment variable is set
6. Check server logs for Gemini API errors

### Audio Quality Issues
1. Verify server is sending 24kHz 16-bit PCM
2. Check for network interruptions
3. Monitor browser audio context state
4. Check Gemini Live API response format

### Performance Issues
1. Monitor memory usage in browser dev tools
2. Check for multiple simultaneous sessions
3. Verify audio buffer cleanup is working
4. Monitor server memory usage during streaming
5. Check for asyncio task leaks in server logs

### Backend Issues
1. **Gemini API Errors**: Check API key validity and quota limits
2. **Threading Issues**: Monitor for deadlocks in asyncio/threading integration
3. **Memory Leaks**: Watch for accumulating audio queues or unclosed sessions
4. **Stream Interruptions**: Check network stability and client disconnections

## API Reference

### Frontend API (TTSModule)

#### TTSModule.init()
Initialize the TTS module (called automatically)

#### TTSModule.reinitialize()
Re-scan for new TTS buttons after dynamic content changes

#### TTSModule.stopAll()
Stop all active TTS sessions and reset button states

### Backend API

#### GET/POST `/tts-stream`
Stream TTS audio for given text

**Parameters:**
- `text` (string): Text to convert to speech

**Response:**
- Content-Type: `application/octet-stream`
- Body: JSON header + raw PCM audio data

**Example:**
```bash
curl "http://localhost:5000/tts-stream?text=Hello%20world"
```

---

*This module is part of the Stouffville By-laws AI Demo application and is provided as-is for experimental use.* 