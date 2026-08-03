import { useState, useEffect, useRef } from 'react';
import { useStore } from '../store/useStore';

export function useVoiceAmplitude() {
  const [amplitude, setAmplitudeState] = useState<number>(0);
  const globalSetAmplitude = useStore(state => state.setAmplitude);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const smoothedRef = useRef<number>(0);
  
  // Audio samples buffer
  const samplesRef = useRef<number[]>([]);

  const startListening = async () => {
    try {
      samplesRef.current = [];
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 16000 // Force 16kHz capturing to match STT models preference
      });
      audioContextRef.current = audioContext;

      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;

      const source = audioContext.createMediaStreamSource(stream);
      sourceRef.current = source;

      // ScriptProcessorNode collects PCM samples in real time
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const channelData = e.inputBuffer.getChannelData(0);
        // Push a copy of samples to buffer
        samplesRef.current.push(...Array.from(channelData));
      };

      // Connect nodes
      source.connect(analyser);
      analyser.connect(processor);
      processor.connect(audioContext.destination);

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const updateAmplitude = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);

        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const average = sum / bufferLength;
        const normalized = Math.min(1.0, average / 128.0);
        smoothedRef.current = smoothedRef.current * 0.8 + normalized * 0.2;
        setAmplitudeState(smoothedRef.current);
        globalSetAmplitude(smoothedRef.current);

        animationFrameRef.current = requestAnimationFrame(updateAmplitude);
      };

      updateAmplitude();
    } catch (err) {
      console.error("useVoiceAmplitude: Microphone access denied or failed:", err);
    }
  };

  const stopListening = (): Blob | null => {
    // Stop animation frames
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    // Stop and disconnect processor node
    if (processorRef.current) {
      processorRef.current.onaudioprocess = null;
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    // Stop microphone recording
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    if (sourceRef.current) {
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }

    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    analyserRef.current = null;
    smoothedRef.current = 0;
    setAmplitudeState(0);
    globalSetAmplitude(0);

    const samples = samplesRef.current;
    if (samples.length === 0) {
      return null;
    }

    // Encode float32 samples to standard 16-bit PCM WAV container
    const sampleRate = 16000;
    const wavBlob = encodeWAV(samples, sampleRate);
    samplesRef.current = [];
    return wavBlob;
  };

  // Helper function to build RIFF WAV header and pack PCM samples
  const encodeWAV = (samples: number[], sampleRate: number): Blob => {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    const writeString = (view: DataView, offset: number, string: string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };

    /* RIFF identifier */
    writeString(view, 0, 'RIFF');
    /* file length */
    view.setUint32(4, 36 + samples.length * 2, true);
    /* RIFF type */
    writeString(view, 8, 'WAVE');
    /* format chunk identifier */
    writeString(view, 12, 'fmt ');
    /* format chunk length */
    view.setUint32(16, 16, true);
    /* sample format (PCM = 1) */
    view.setUint16(20, 1, true);
    /* channel count (Mono = 1) */
    view.setUint16(22, 1, true);
    /* sample rate */
    view.setUint32(24, sampleRate, true);
    /* byte rate (sample rate * block align) */
    view.setUint32(28, sampleRate * 2, true);
    /* block align (channels * bytes per sample) */
    view.setUint16(32, 2, true);
    /* bits per sample */
    view.setUint16(34, 16, true);
    /* data chunk identifier */
    writeString(view, 36, 'data');
    /* data chunk length */
    view.setUint32(40, samples.length * 2, true);

    // Write PCM float32 samples converted to 16-bit signed PCM integers
    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }

    return new Blob([view], { type: 'audio/wav' });
  };

  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (processorRef.current) {
        processorRef.current.disconnect();
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  return {
    amplitude,
    startListening,
    stopListening
  };
}
