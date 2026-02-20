import { useState, useEffect, useRef } from 'react';

export const useVoice = (onTranscription: (text: string) => void, onResponse: (text: string) => void) => {
    const [isRecording, setIsRecording] = useState(false);
    const [isPlaying, setIsPlaying] = useState(false);
    const mediaRecorder = useRef<MediaRecorder | null>(null);
    const ws = useRef<WebSocket | null>(null);
    const audioChunks = useRef<Blob[]>([]);

    useEffect(() => {
        return () => {
            stopRecording();
            if (ws.current) ws.current.close();
        };
    }, []);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            // Connect WS
            ws.current = new WebSocket('ws://localhost:8000/api/voice/stream');
            ws.current.binaryType = 'arraybuffer';

            ws.current.onopen = () => {
                console.log('Voice WS Connected');
                mediaRecorder.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });

                mediaRecorder.current.ondataavailable = (event) => {
                    if (event.data.size > 0 && ws.current?.readyState === WebSocket.OPEN) {
                        // Send binary audio chunks
                        // Note: Backend might expect raw PCM. If it fails, we might need conversion.
                        // But STT engines (ffmpeg) usually handle webm/opus.
                        // We send the blob converted to array buffer?
                        // WS send accepts Blob or ArrayBuffer.
                        ws.current.send(event.data);
                    }
                };

                mediaRecorder.current.start(250); // Send chunks every 250ms
                setIsRecording(true);
            };

            ws.current.onmessage = async (event) => {
                if (typeof event.data === 'string') {
                    const msg = JSON.parse(event.data);
                    if (msg.type === 'transcription') {
                        onTranscription(msg.text);
                    } else if (msg.type === 'response_text') {
                        onResponse(msg.text);
                    } else if (msg.type === 'response_start') {
                        setIsPlaying(true);
                        audioChunks.current = [];
                    } else if (msg.type === 'response_end') {
                        // Play accumulated audio
                        const audioBlob = new Blob(audioChunks.current, { type: 'audio/wav' });
                        const audioUrl = URL.createObjectURL(audioBlob);
                        const audio = new Audio(audioUrl);
                        audio.onended = () => setIsPlaying(false);
                        audio.play();
                    }
                } else {
                    // Binary audio response
                    audioChunks.current.push(event.data);
                }
            };

            ws.current.onerror = (e) => console.error('WS Error', e);

        } catch (err) {
            console.error('Microphone Error', err);
        }
    };

    const stopRecording = () => {
        if (mediaRecorder.current && isRecording) {
            mediaRecorder.current.stop();
            mediaRecorder.current.stream.getTracks().forEach(track => track.stop());
            setIsRecording(false);

            // Send end_turn signal
            if (ws.current?.readyState === WebSocket.OPEN) {
                ws.current.send(JSON.stringify({ type: 'end_turn' }));
            }
        }
    };

    const toggleVoice = () => {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    };

    return { isRecording, isPlaying, toggleVoice };
};
