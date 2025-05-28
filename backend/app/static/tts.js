/**
 * TTS (Text-to-Speech) Functionality
 * Alpha implementation - separate from main application
 * 
 * This module provides streaming TTS functionality using Web Audio API
 * for smooth real-time audio playback from server-generated speech.
 */

// TTS Module - Encapsulated functionality
const TTSModule = (function() {
    'use strict';

    // Private variables
    let isInitialized = false;

    /**
     * Initialize TTS functionality
     * Sets up event listeners for all TTS buttons on the page
     */
    function init() {
        if (isInitialized) {
            console.warn('TTS Module already initialized');
            return;
        }

        setupTTSButtons();
        isInitialized = true;
        console.log('TTS Module initialized');
    }

    /**
     * Set up event listeners for all TTS buttons
     */
    function setupTTSButtons() {
        const ttsButtons = document.querySelectorAll('.tts-button');
        ttsButtons.forEach(button => {
            button.addEventListener('click', handleTTSButtonClick);
        });
    }

    /**
     * Handle TTS button click events
     * @param {Event} event - The click event
     */
    function handleTTSButtonClick(event) {
        const button = event.target;
        const answerContainer = button.closest('.answer-container');
        
        if (!answerContainer) {
            console.error('TTS: Could not find answer container');
            return;
        }

        // Check if already playing
        if (answerContainer.currentTTS) {
            stopTTS(answerContainer, button);
            return;
        }

        // Extract text content
        const text = extractTextContent(answerContainer);
        if (!text) {
            console.error('TTS: No text content found');
            return;
        }

        // Start TTS playback
        startTTS(text, answerContainer, button);
    }

    /**
     * Extract text content from answer container
     * @param {HTMLElement} answerContainer - The container element
     * @returns {string} - The extracted text
     */
    function extractTextContent(answerContainer) {
        const contentDiv = answerContainer.querySelector('div');
        if (!contentDiv) return '';

        // Extract only the actual answer text (everything before "Source: ChromaDB")
        let text = contentDiv.textContent.trim();
        const sourceIndex = text.indexOf('Source: ChromaDB');
        if (sourceIndex > -1) {
            text = text.substring(0, sourceIndex).trim();
        }

        return text;
    }

    /**
     * Start TTS playback
     * @param {string} text - Text to speak
     * @param {HTMLElement} answerContainer - Container element
     * @param {HTMLElement} button - TTS button element
     */
    function startTTS(text, answerContainer, button) {
        // Update button state
        updateButtonState(button, 'loading');
        
        // Start playback
        playTTSWebAudio(text, answerContainer, button)
            .catch(error => {
                console.error('TTS playback failed:', error);
                updateButtonState(button, 'error');
                alert('TTS playback failed. Please try again.');
            });
    }

    /**
     * Stop TTS playback
     * @param {HTMLElement} answerContainer - Container element
     * @param {HTMLElement} button - TTS button element
     */
    function stopTTS(answerContainer, button) {
        if (answerContainer.currentTTS) {
            answerContainer.currentTTS.stop();
            answerContainer.currentTTS = null;
        }
        updateButtonState(button, 'default');
    }

    /**
     * Update TTS button visual state
     * @param {HTMLElement} button - TTS button element
     * @param {string} state - Button state: 'default', 'loading', 'playing', 'error'
     */
    function updateButtonState(button, state) {
        // Remove all state classes
        button.classList.remove('loading', 'playing');
        
        switch (state) {
            case 'loading':
                button.classList.add('loading');
                button.textContent = 'Loading...';
                button.disabled = true;
                break;
            case 'playing':
                button.classList.add('playing');
                button.textContent = 'Stop';
                button.disabled = false;
                break;
            case 'default':
                button.textContent = 'Speak aloud';
                button.disabled = false;
                break;
            case 'error':
                button.textContent = 'Speak aloud';
                button.disabled = false;
                break;
        }
    }

    /**
     * Web Audio API based TTS player for smooth streaming
     * @param {string} text - Text to convert to speech
     * @param {HTMLElement} answerContainer - Container element
     * @param {HTMLElement} button - TTS button element
     */
    async function playTTSWebAudio(text, answerContainer, button) {
        try {
            // Initialize Web Audio Context
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            // Ensure context is running - handle autoplay policy
            if (audioContext.state === 'suspended') {
                await audioContext.resume();
            }
            
            const sourceSampleRate = 24000; // Gemini's sample rate
            const targetSampleRate = audioContext.sampleRate; // Usually 44100
            
            let headerParsed = false;
            let audioQueue = [];
            let isPlaying = false;
            let processingNode = null;
            let gainNode = null;
            let currentSampleIndex = 0;
            let streamCompleted = false;
            let playbackStarted = false;
            
            // Create a controller to manage the TTS session
            const ttsController = {
                stop: () => {
                    isPlaying = false;
                    if (processingNode) {
                        try {
                            processingNode.disconnect();
                        } catch (e) {
                            // Ignore disconnect errors
                        }
                        processingNode = null;
                    }
                    if (gainNode) {
                        try {
                            gainNode.disconnect();
                        } catch (e) {
                            // Ignore disconnect errors
                        }
                        gainNode = null;
                    }
                    audioQueue = [];
                    updateButtonState(button, 'default');
                }
            };
            
            // Store the controller for later cleanup
            answerContainer.currentTTS = ttsController;
            
            // Create gain node for volume control
            gainNode = audioContext.createGain();
            gainNode.gain.value = 0.8;
            gainNode.connect(audioContext.destination);
            
            // Use ScriptProcessorNode for audio processing
            const bufferSize = 4096;
            processingNode = audioContext.createScriptProcessor(bufferSize, 0, 1);
            processingNode.connect(gainNode);
            
            processingNode.onaudioprocess = function(event) {
                const outputData = event.outputBuffer.getChannelData(0);
                
                if (!isPlaying) {
                    outputData.fill(0);
                    return;
                }
                
                // Fill output buffer with queued audio data
                for (let i = 0; i < bufferSize; i++) {
                    if (currentSampleIndex < audioQueue.length) {
                        outputData[i] = audioQueue[currentSampleIndex];
                        currentSampleIndex++;
                    } else {
                        outputData[i] = 0;
                    }
                }
                
                // Clean up old audio data to prevent memory growth
                if (currentSampleIndex > targetSampleRate * 3) {
                    const keepSamples = targetSampleRate;
                    const removeCount = currentSampleIndex - keepSamples;
                    audioQueue.splice(0, removeCount);
                    currentSampleIndex = keepSamples;
                }
            };
            
            // Simple linear interpolation resampler
            function resampleAudio(inputSamples, inputRate, outputRate) {
                if (inputRate === outputRate) {
                    return inputSamples;
                }
                
                const ratio = inputRate / outputRate;
                const outputLength = Math.floor(inputSamples.length / ratio);
                const output = new Float32Array(outputLength);
                
                for (let i = 0; i < outputLength; i++) {
                    const sourceIndex = i * ratio;
                    const index = Math.floor(sourceIndex);
                    const fraction = sourceIndex - index;
                    
                    if (index + 1 < inputSamples.length) {
                        output[i] = inputSamples[index] * (1 - fraction) + inputSamples[index + 1] * fraction;
                    } else if (index < inputSamples.length) {
                        output[i] = inputSamples[index];
                    } else {
                        output[i] = 0;
                    }
                }
                
                return output;
            }
            
            // Fetch and process the audio stream
            try {
                const response = await fetch(`/tts-stream?text=${encodeURIComponent(text)}`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                // Update button state to playing
                updateButtonState(button, 'playing');
                
                const reader = response.body.getReader();
                let bytesBuffer = new Uint8Array(0);
                
                // Read stream chunks
                while (true) {
                    const { done, value } = await reader.read();
                    
                    if (done) {
                        streamCompleted = true;
                        break;
                    }
                    if (!isPlaying && !processingNode) break;
                    
                    // Append new data to buffer
                    const newBuffer = new Uint8Array(bytesBuffer.length + value.length);
                    newBuffer.set(bytesBuffer);
                    newBuffer.set(value, bytesBuffer.length);
                    bytesBuffer = newBuffer;
                    
                    // Parse header if not done yet
                    if (!headerParsed) {
                        const headerEnd = bytesBuffer.indexOf(10);
                        if (headerEnd !== -1) {
                            const headerBytes = bytesBuffer.slice(0, headerEnd);
                            const headerText = new TextDecoder().decode(headerBytes);
                            try {
                                JSON.parse(headerText); // Validate header format
                                headerParsed = true;
                                bytesBuffer = bytesBuffer.slice(headerEnd + 1);
                            } catch (e) {
                                headerParsed = true;
                            }
                        } else {
                            continue;
                        }
                    }
                    
                    // Convert bytes to audio samples and add to queue
                    if (bytesBuffer.length >= 2) {
                        const samplesCount = Math.floor(bytesBuffer.length / 2);
                        
                        // Create Int16Array from the bytes
                        const int16Data = new Int16Array(samplesCount);
                        const dataView = new DataView(bytesBuffer.buffer, bytesBuffer.byteOffset, samplesCount * 2);
                        
                        for (let i = 0; i < samplesCount; i++) {
                            int16Data[i] = dataView.getInt16(i * 2, true);
                        }
                        
                        // Convert to Float32Array
                        const float32Samples = new Float32Array(int16Data.length);
                        for (let i = 0; i < int16Data.length; i++) {
                            float32Samples[i] = int16Data[i] / 32768.0;
                        }
                        
                        // Resample if necessary
                        const resampledSamples = resampleAudio(float32Samples, sourceSampleRate, targetSampleRate);
                        
                        // Add resampled samples to queue
                        for (let i = 0; i < resampledSamples.length; i++) {
                            audioQueue.push(resampledSamples[i]);
                        }
                        
                        // Start playback when we have enough data
                        if (!isPlaying && audioQueue.length >= targetSampleRate * 0.1) {
                            isPlaying = true;
                            playbackStarted = true;
                            
                            if (audioContext.state === 'suspended') {
                                await audioContext.resume();
                            }
                        }
                        
                        // Update buffer to remaining bytes
                        const remainingBytes = bytesBuffer.length % 2;
                        if (remainingBytes > 0) {
                            bytesBuffer = bytesBuffer.slice(samplesCount * 2);
                        } else {
                            bytesBuffer = new Uint8Array(0);
                        }
                    }
                }
                
                // Start playback if we haven't already
                if (!isPlaying && audioQueue.length > 0) {
                    isPlaying = true;
                    playbackStarted = true;
                    
                    if (audioContext.state === 'suspended') {
                        await audioContext.resume();
                    }
                }
                
            } catch (streamError) {
                // Only show error if playback never started or if it's a real error (not just stream completion)
                if (!playbackStarted) {
                    throw streamError; // Re-throw if playback never started
                }
                // If playback started, just mark stream as completed and let audio finish
                streamCompleted = true;
            }
            
            // Wait for playback to finish
            const checkPlaybackFinished = () => {
                if (!isPlaying) return;
                
                // Only stop if stream is complete AND we've played all queued audio
                if (streamCompleted && currentSampleIndex >= audioQueue.length && audioQueue.length > 0) {
                    ttsController.stop();
                    answerContainer.currentTTS = null;
                } else {
                    setTimeout(checkPlaybackFinished, 500);
                }
            };
            
            setTimeout(checkPlaybackFinished, 500);
            
        } catch (error) {
            console.error('TTS playback failed:', error);
            updateButtonState(button, 'error');
            // Only show error popup for actual failures, not stream completion issues
            throw error;
        }
    }

    /**
     * Reinitialize TTS for dynamically added content
     * Call this after adding new content with TTS buttons
     */
    function reinitialize() {
        setupTTSButtons();
    }

    /**
     * Stop all active TTS sessions
     */
    function stopAll() {
        const containers = document.querySelectorAll('.answer-container');
        containers.forEach(container => {
            if (container.currentTTS) {
                container.currentTTS.stop();
                container.currentTTS = null;
            }
        });

        // Reset all button states
        const buttons = document.querySelectorAll('.tts-button');
        buttons.forEach(button => {
            updateButtonState(button, 'default');
        });
    }

    // Public API
    return {
        init: init,
        reinitialize: reinitialize,
        stopAll: stopAll
    };
})();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', TTSModule.init);
} else {
    TTSModule.init();
}

// Export for global access if needed
window.TTSModule = TTSModule; 