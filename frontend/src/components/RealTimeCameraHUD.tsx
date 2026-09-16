import React, { useRef, useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import { Language, translations } from '../i18n/translations';
import { OpticalMode, RealTimeFrameScore } from '../types';
import {
  Camera, Eye, Focus, Sun, AlertTriangle, CheckCircle2,
  RefreshCw, Sliders, Zap, X, ShieldAlert, Sparkles, Layers
} from 'lucide-react';

interface Props {
  screeningId: string;
  eye: 'OD' | 'OS';
  lang: Language;
  onCaptureCompleted: (captureData: any) => void;
  onCancel: () => void;
}

export const RealTimeCameraHUD: React.FC<Props> = ({
  screeningId,
  eye,
  lang,
  onCaptureCompleted,
  onCancel
}) => {
  const t = translations[lang];

  // Video & Canvas Refs
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animFrameId = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const prevFrameData = useRef<Uint8ClampedArray | null>(null);

  // Optical Mode & Configurations
  const [opticalMode, setOpticalMode] = useState<OpticalMode>('MODE_2_PASSIVE_OPTIC');
  const [lensPower, setLensPower] = useState('+20D');
  const [lensDistanceMm, setLensDistanceMm] = useState(50.0);
  const [phoneToLensMm, setPhoneToLensMm] = useState(15.0);
  const [digitalZoom, setDigitalZoom] = useState(1.0);
  const [torchEnabled, setTorchEnabled] = useState(false);
  const [showResearchSettings, setShowResearchSettings] = useState(false);

  // Camera State & Hardware Detection
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [isSimulatedFeed, setIsSimulatedFeed] = useState<boolean>(false);
  const [simulationTick, setSimulationTick] = useState<number>(0);

  // Live Real-Time Frame Metrics (Updated ~20-30 FPS)
  const [frameScore, setFrameScore] = useState<number>(0);
  const [qualityPct, setQualityPct] = useState<number>(0);
  const [retinalStatus, setRetinalStatus] = useState<string>('SEARCHING');
  const [alignmentStatus, setAlignmentStatus] = useState<'CENTERED' | 'LEFT' | 'RIGHT' | 'UP' | 'DOWN' | 'TOO_CLOSE' | 'TOO_FAR'>('CENTERED');
  const [focusScore, setFocusScore] = useState<number>(0);
  const [glareScore, setGlareScore] = useState<number>(0);
  const [motionScore, setMotionScore] = useState<number>(0);
  const [guidanceMessage, setGuidanceMessage] = useState<string>('Position the camera toward the eye');
  const [passedGate, setPassedGate] = useState<boolean>(false);

  // Autonomous Capture State
  const [isCapturing, setIsCapturing] = useState<boolean>(false);
  const [capturedAnimation, setCapturedAnimation] = useState<boolean>(false);
  const consecutiveGoodFrames = useRef<number>(0);
  const framesEvaluatedCount = useRef<number>(0);
  const startTimeRef = useRef<number>(Date.now());
  const forensicTimeline = useRef<any[]>([]);

  // 1. Initialize Available Cameras
  useEffect(() => {
    const getCameras = async () => {
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
          setIsSimulatedFeed(true);
          return;
        }
        const devList = await navigator.mediaDevices.enumerateDevices();
        const videoInputs = devList.filter(d => d.kind === 'videoinput');
        setDevices(videoInputs);
        // Prefer rear / back camera for fundus imaging
        const backCamera = videoInputs.find(d =>
          d.label.toLowerCase().includes('back') ||
          d.label.toLowerCase().includes('rear') ||
          d.label.toLowerCase().includes('environment')
        );
        if (backCamera) {
          setSelectedDeviceId(backCamera.deviceId);
        } else if (videoInputs.length > 0) {
          setSelectedDeviceId(videoInputs[0].deviceId);
        }
      } catch (err) {
        console.warn("Camera enumeration error, falling back to simulated stream:", err);
        setIsSimulatedFeed(true);
      }
    };
    getCameras();
  }, []);

  // 2. Start Live Camera Stream
  const startCamera = useCallback(async () => {
    if (isSimulatedFeed) return;
    try {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      const constraints: MediaStreamConstraints = {
        video: selectedDeviceId
          ? { deviceId: { exact: selectedDeviceId }, width: { ideal: 1280 }, height: { ideal: 720 } }
          : { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      setCameraError(null);
    } catch (err: any) {
      console.warn("getUserMedia error, enabling simulation stream mode:", err);
      setCameraError(err.message || "Camera permission denied or camera unavailable");
      setIsSimulatedFeed(true);
    }
  }, [selectedDeviceId, isSimulatedFeed]);

  useEffect(() => {
    startCamera();
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (animFrameId.current) {
        cancelAnimationFrame(animFrameId.current);
      }
    };
  }, [startCamera]);

  // 3. Toggle Torch / LED Flash if supported
  const toggleTorch = async () => {
    if (!streamRef.current) return;
    const track = streamRef.current.getVideoTracks()[0];
    if (!track) return;
    try {
      const caps = (track as any).getCapabilities ? (track as any).getCapabilities() : {};
      if (caps.torch) {
        await (track as any).applyConstraints({
          advanced: [{ torch: !torchEnabled }]
        });
        setTorchEnabled(!torchEnabled);
      } else {
        alert("Hardware torch control is not supported on this device/browser.");
      }
    } catch (e) {
      console.warn("Torch toggle error:", e);
    }
  };

  // 4. Autonomous Trigger Execution
  const triggerAutoCapture = useCallback(async (canvas: HTMLCanvasElement) => {
    if (isCapturing) return;
    setIsCapturing(true);
    setCapturedAnimation(true);

    canvas.toBlob(async (blob) => {
      if (!blob) {
        setIsCapturing(false);
        return;
      }
      try {
        const formData = new FormData();
        formData.append("screening_id", screeningId);
        formData.append("eye", eye);
        formData.append("optical_mode", opticalMode);
        formData.append("lens_power", lensPower);
        formData.append("lens_distance_mm", lensDistanceMm.toString());
        formData.append("camera_lens_distance_mm", phoneToLensMm.toString());
        formData.append("device_model", "Smartphone Camera (Passive Optic)");
        formData.append("camera_id", selectedDeviceId || "rear_camera_0");
        formData.append("capture_method", "AUTONOMOUS_BEST_FRAME");
        formData.append("frames_evaluated", framesEvaluatedCount.current.toString());
        formData.append("duration_seconds", ((Date.now() - startTimeRef.current) / 1000).toFixed(1));
        formData.append("timeline_json", JSON.stringify(forensicTimeline.current.slice(-40)));
        formData.append("file", blob, `AUTOCAPTURE_${screeningId}_${eye}.jpg`);

        const result = await api.autoCapture(formData);
        setTimeout(() => {
          onCaptureCompleted(result);
        }, 800);
      } catch (err: any) {
        alert("Capture submission error: " + err.message);
        setIsCapturing(false);
        setCapturedAnimation(false);
      }
    }, "image/jpeg", 0.95);
  }, [isCapturing, screeningId, eye, opticalMode, lensPower, lensDistanceMm, phoneToLensMm, selectedDeviceId, onCaptureCompleted]);

  // 5. Real-Time Client-Side Processing Loop
  useEffect(() => {
    let tick = 0;
    const processFrame = () => {
      tick++;
      framesEvaluatedCount.current++;
      const canvas = canvasRef.current;
      if (!canvas) {
        animFrameId.current = requestAnimationFrame(processFrame);
        return;
      }
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        animFrameId.current = requestAnimationFrame(processFrame);
        return;
      }

      const cw = canvas.width;
      const ch = canvas.height;

      if (!isSimulatedFeed && videoRef.current && videoRef.current.readyState >= 2) {
        // Draw incoming video frame to analysis canvas
        ctx.drawImage(videoRef.current, 0, 0, cw, ch);
      } else {
        // Render Procedural Optical Alignment Simulation
        // Simulates approach: searching -> lens alignment -> red-reflex -> focused fundus -> autonomous trigger
        const tSec = tick * 0.04;
        ctx.fillStyle = '#060a12';
        ctx.fillRect(0, 0, cw, ch);

        // Simulation progression:
        // Phase 1 (0-1.5s): Approach and alignment
        // Phase 2 (1.5s-3.0s): Red reflex aperture centering
        // Phase 3 (3.0s+): Crisp fundus vascular aerial image
        const cx = cw / 2 + Math.sin(tSec * 1.5) * Math.max(0, 45 - tSec * 12);
        const cy = ch / 2 + Math.cos(tSec * 1.2) * Math.max(0, 35 - tSec * 10);
        const radius = Math.min(130, 75 + tSec * 14);

        if (tSec < 1.0) {
          // Dark pupil search
          ctx.beginPath();
          ctx.arc(cx, cy, 35, 0, Math.PI * 2);
          ctx.fillStyle = '#111827';
          ctx.fill();
        } else {
          // Fundus red reflex disc
          const grad = ctx.createRadialGradient(cx, cy, 10, cx, cy, radius);
          grad.addColorStop(0, '#c2410c'); // orange-red
          grad.addColorStop(0.65, '#991b1b'); // deep retinal red
          grad.addColorStop(0.92, '#450a0a'); // fundus boundary
          grad.addColorStop(1, '#05070c');

          ctx.beginPath();
          ctx.arc(cx, cy, radius, 0, Math.PI * 2);
          ctx.fillStyle = grad;
          ctx.fill();

          // Optic disc
          const odX = cx + (eye === 'OD' ? -radius * 0.45 : radius * 0.45);
          const odY = cy;
          ctx.beginPath();
          ctx.arc(odX, odY, radius * 0.18, 0, Math.PI * 2);
          ctx.fillStyle = '#fef08a';
          ctx.fill();

          // Retinal blood vessels
          ctx.lineWidth = 2.5;
          ctx.strokeStyle = '#450a0a';
          ctx.beginPath();
          ctx.moveTo(odX, odY);
          ctx.bezierCurveTo(cx, cy - radius * 0.5, cx + radius * 0.3, cy - radius * 0.7, cx + radius * 0.6, cy - radius * 0.8);
          ctx.moveTo(odX, odY);
          ctx.bezierCurveTo(cx, cy + radius * 0.5, cx + radius * 0.3, cy + radius * 0.7, cx + radius * 0.6, cy + radius * 0.8);
          ctx.stroke();

          // Glare reflection (fades out as operator aligns)
          if (tSec < 2.5) {
            ctx.beginPath();
            ctx.arc(cx + 25, cy - 25, 12, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
            ctx.fill();
          }
        }
      }

      // Fast Client-Side Image Analysis on central ROI
      try {
        const frameData = ctx.getImageData(0, 0, cw, ch);
        const data = frameData.data;

        // Sample central pixels to check retinal red dominance and specular glare
        let totalR = 0, totalG = 0, totalB = 0;
        let glareCount = 0;
        let sampleCount = 0;
        const cX = Math.floor(cw / 2);
        const cY = Math.floor(ch / 2);
        const sampleRadius = Math.floor(cw * 0.22);

        for (let y = cY - sampleRadius; y <= cY + sampleRadius; y += 4) {
          for (let x = cX - sampleRadius; x <= cX + sampleRadius; x += 4) {
            const idx = (y * cw + x) * 4;
            const r = data[idx];
            const g = data[idx + 1];
            const b = data[idx + 2];
            totalR += r;
            totalG += g;
            totalB += b;
            sampleCount++;

            // Specular reflection detection (pure saturated highlight)
            if (r > 240 && g > 240 && b > 235) {
              glareCount++;
            }
          }
        }

        const avgR = totalR / Math.max(1, sampleCount);
        const avgG = totalG / Math.max(1, sampleCount);
        const avgB = totalB / Math.max(1, sampleCount);

        const currentGlareScore = Math.min(100, Math.round((glareCount / Math.max(1, sampleCount)) * 100 * 3));
        setGlareScore(currentGlareScore);

        // Retinal View Hue Check
        const redRatio = avgR / (avgG + 1);
        const isRetina = redRatio > 1.35 && avgB < (avgG * 0.85);

        // Focus proxy (variance of adjacent pixels)
        let diffSum = 0;
        for (let i = 0; i < data.length - 16; i += 16) {
          diffSum += Math.abs(data[i] - data[i + 4]);
        }
        const currentFocus = Math.min(180, Math.round(diffSum / (data.length / 32) * 12));
        setFocusScore(currentFocus);

        // Motion proxy (frame-to-frame diff)
        let currentMotion = 0;
        if (prevFrameData.current) {
          let mDiff = 0;
          const pData = prevFrameData.current;
          for (let i = 0; i < data.length; i += 64) {
            mDiff += Math.abs(data[i] - pData[i]);
          }
          currentMotion = Math.round(mDiff / (data.length / 64));
        }
        prevFrameData.current = new Uint8ClampedArray(data);
        setMotionScore(currentMotion);

        // Frame Score Formula
        // FrameScore = 0.3*retina + 0.25*focus + 0.2*illum - 0.2*glare - 0.18*motion
        let rScore = isRetina ? 88 : 25;
        if (isRetina) {
          setRetinalStatus("RETINAL_VIEW");
        } else {
          setRetinalStatus(avgR > 70 ? "PARTIAL_VIEW" : "NO_RETINA");
        }

        let fNorm = Math.min(100, (currentFocus / 110) * 100);
        let gPenalty = Math.min(45, currentGlareScore * 2.5);
        let mPenalty = Math.min(40, currentMotion * 3.5);

        let compositeScore = Math.max(10, Math.min(98, Math.round(0.35 * rScore + 0.3 * fNorm + 20 - gPenalty - mPenalty)));
        setFrameScore(compositeScore);
        setQualityPct(compositeScore);

        // Live Guidance Logic
        if (currentMotion > 10) {
          setGuidanceMessage(lang === 'hi' ? "फ़ोन को स्थिर पकड़ें" : "Hold the phone steady");
        } else if (currentGlareScore > 12) {
          setGuidanceMessage(lang === 'hi' ? "चमक परावर्तन — फ़ोन का कोण थोड़ा बदलें" : "Reflection detected — adjust angle slightly");
        } else if (!isRetina) {
          setGuidanceMessage(lang === 'hi' ? "कैमरे को पुतली के केंद्र में रखें" : "Position the camera toward the eye");
        } else if (currentFocus < 75) {
          setGuidanceMessage(lang === 'hi' ? "फ़ोकस हो रहा है... स्थिर रखें" : "Focusing... hold steady");
        } else if (compositeScore >= 72) {
          setGuidanceMessage(lang === 'hi' ? "उत्कृष्ट छवि — कैप्चर हो रही है" : "Good image — capturing");
        } else {
          setGuidanceMessage(lang === 'hi' ? "स्थिर रखें" : "Hold steady");
        }

        // Check if frame satisfies acquisition threshold
        const isGood = compositeScore >= 72 && currentGlareScore <= 14 && currentMotion <= 9 && isRetina;
        setPassedGate(isGood);

        // Forensic point logging (every ~100ms)
        if (tick % 3 === 0) {
          forensicTimeline.current.push({
            frame_index: tick,
            timestamp_sec: (tick * 0.04).toFixed(2),
            focus_score: currentFocus,
            glare_score: currentGlareScore,
            motion_score: currentMotion,
            retinal_score: rScore,
            frame_score: compositeScore,
            alignment_status: 'CENTERED',
            is_candidate: compositeScore >= 65,
            is_selected_frame: false
          });
        }

        // Autonomous Capture Gate: Requires 2-3 consecutive stable frames
        if (isGood) {
          consecutiveGoodFrames.current += 1;
          if (consecutiveGoodFrames.current >= 3 && !isCapturing) {
            triggerAutoCapture(canvas);
          }
        } else {
          consecutiveGoodFrames.current = 0;
        }

      } catch (err) {
        // Continue loop
      }

      animFrameId.current = requestAnimationFrame(processFrame);
    };

    animFrameId.current = requestAnimationFrame(processFrame);
    return () => {
      if (animFrameId.current) cancelAnimationFrame(animFrameId.current);
    };
  }, [isSimulatedFeed, isCapturing, lang, eye, triggerAutoCapture]);

  // Manual Shutter Fallback
  const handleManualCapture = () => {
    if (canvasRef.current) {
      triggerAutoCapture(canvasRef.current);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      backgroundColor: '#030712',
      zIndex: 9999,
      display: 'flex',
      flexDirection: 'column',
      color: '#f9fafb',
      fontFamily: 'Inter, system-ui, sans-serif'
    }}>
      {/* Hidden processing video & canvas */}
      <video ref={videoRef} playsInline muted style={{ display: 'none' }} />

      {/* Top Navigation & Optical Mode Bar */}
      <div style={{
        padding: '12px 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(15, 23, 42, 0.85)',
        backdropFilter: 'blur(8px)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.1)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            background: 'var(--brand-cyan)',
            color: '#04131f',
            padding: '4px 10px',
            borderRadius: '4px',
            fontSize: '12px',
            fontWeight: 800,
            letterSpacing: '0.05em'
          }}>
            TRINETRA LIVE HUD
          </div>
          <span style={{ fontSize: '15px', fontWeight: 700 }}>
            {eye === 'OD' ? 'Right Eye (OD — Oculus Dexter)' : 'Left Eye (OS — Oculus Sinister)'}
          </span>
          <span className="badge badge-emerald" style={{ fontSize: '11px' }}>
            {t.hud_scanning}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Mode Selector */}
          <select
            value={opticalMode}
            onChange={(e) => setOpticalMode(e.target.value as OpticalMode)}
            style={{
              background: 'rgba(30, 41, 59, 0.9)',
              color: '#38bdf8',
              border: '1px solid rgba(56, 189, 248, 0.4)',
              borderRadius: '6px',
              padding: '6px 10px',
              fontSize: '12px',
              fontWeight: 600
            }}
          >
            <option value="MODE_2_PASSIVE_OPTIC">{t.mode_2_label}</option>
            <option value="MODE_1_BARE_PHONE">{t.mode_1_label}</option>
            <option value="MODE_3_RESEARCH">{t.mode_3_label}</option>
          </select>

          {/* Torch Button */}
          <button
            onClick={toggleTorch}
            className="btn btn-secondary"
            style={{ padding: '6px 12px', fontSize: '12px' }}
            title="Toggle Smartphone Torch"
          >
            <Zap size={14} color={torchEnabled ? '#f59e0b' : '#94a3b8'} />
            <span>Torch</span>
          </button>

          {/* Research Settings Toggle */}
          <button
            onClick={() => setShowResearchSettings(!showResearchSettings)}
            className="btn btn-secondary"
            style={{ padding: '6px 12px', fontSize: '12px' }}
          >
            <Sliders size={14} />
            <span>Optics Config</span>
          </button>

          {/* Close HUD */}
          <button
            onClick={onCancel}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: '6px'
            }}
          >
            <X size={20} />
          </button>
        </div>
      </div>

      {/* Optical Mode Disclaimer Notice */}
      {opticalMode === 'MODE_1_BARE_PHONE' && (
        <div style={{
          background: 'rgba(234, 88, 12, 0.15)',
          borderBottom: '1px solid rgba(234, 88, 12, 0.3)',
          color: '#fb923c',
          padding: '6px 16px',
          fontSize: '12px',
          textAlign: 'center',
          fontWeight: 600
        }}>
          ⚠️ {t.mode_1_desc}
        </div>
      )}

      {/* Main Viewport Container */}
      <div style={{
        flex: 1,
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden'
      }}>
        {/* Render Canvas */}
        <canvas
          ref={canvasRef}
          width={640}
          height={480}
          style={{
            maxWidth: '100%',
            maxHeight: '100%',
            borderRadius: '12px',
            boxShadow: '0 0 40px rgba(0,0,0,0.8)',
            border: passedGate ? '3px solid #10b981' : '3px solid rgba(56, 189, 248, 0.4)'
          }}
        />

        {/* Reticle Overlay */}
        <div style={{
          position: 'absolute',
          width: '280px',
          height: '280px',
          borderRadius: '50%',
          border: `2px dashed ${passedGate ? '#10b981' : glareScore > 12 ? '#f43f5e' : '#38bdf8'}`,
          boxShadow: passedGate ? '0 0 25px rgba(16, 185, 129, 0.3)' : 'none',
          pointerEvents: 'none',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.2s ease'
        }}>
          <div style={{
            fontSize: '10px',
            fontWeight: 800,
            letterSpacing: '0.1em',
            color: passedGate ? '#10b981' : '#38bdf8',
            background: 'rgba(3, 7, 18, 0.7)',
            padding: '2px 8px',
            borderRadius: '4px'
          }}>
            {t.hud_reticle_guide}
          </div>
          <div style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: passedGate ? '#10b981' : '#38bdf8',
            marginTop: '8px'
          }} />
        </div>

        {/* Real-Time Live Guidance Banner (Bottom-Center of Viewport) */}
        <div style={{
          position: 'absolute',
          bottom: '24px',
          padding: '10px 24px',
          background: passedGate ? 'rgba(6, 78, 59, 0.95)' : glareScore > 12 ? 'rgba(159, 18, 57, 0.95)' : 'rgba(15, 23, 42, 0.9)',
          backdropFilter: 'blur(6px)',
          border: `1px solid ${passedGate ? '#10b981' : glareScore > 12 ? '#f43f5e' : 'rgba(255,255,255,0.15)'}`,
          borderRadius: '24px',
          fontSize: '14px',
          fontWeight: 700,
          color: '#ffffff',
          boxShadow: '0 8px 30px rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          {passedGate ? <CheckCircle2 size={18} color="#10b981" /> : glareScore > 12 ? <AlertTriangle size={18} color="#f43f5e" /> : <Eye size={18} color="#38bdf8" />}
          <span>{guidanceMessage}</span>
        </div>

        {/* Shutter Capture Animation */}
        {capturedAnimation && (
          <div style={{
            position: 'absolute',
            inset: 0,
            backgroundColor: '#ffffff',
            opacity: 0.9,
            transition: 'opacity 0.5s ease',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10
          }}>
            <div style={{
              color: '#064e3b',
              fontSize: '22px',
              fontWeight: 900,
              background: '#ffffff',
              padding: '16px 32px',
              borderRadius: '8px',
              boxShadow: '0 10px 35px rgba(0,0,0,0.2)'
            }}>
              {t.hud_auto_captured}
            </div>
          </div>
        )}
      </div>

      {/* Bottom HUD Telemetry & Autonomous Controls */}
      <div style={{
        padding: '16px 24px',
        background: 'rgba(15, 23, 42, 0.95)',
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        display: 'grid',
        gridTemplateColumns: '2fr 3fr 2fr',
        alignItems: 'center',
        gap: '20px'
      }}>
        {/* Quality Progress Meter */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
            <span style={{ color: '#94a3b8' }}>Image Quality</span>
            <span style={{ color: qualityPct >= 72 ? '#10b981' : '#38bdf8', fontWeight: 800 }}>{qualityPct}%</span>
          </div>
          <div style={{ width: '100%', height: '8px', backgroundColor: '#1e293b', borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{
              width: `${qualityPct}%`,
              height: '100%',
              backgroundColor: qualityPct >= 72 ? '#10b981' : qualityPct >= 50 ? '#38bdf8' : '#f59e0b',
              transition: 'width 0.15s ease'
            }} />
          </div>
          <div style={{ fontSize: '10px', color: '#64748b', marginTop: '4px' }}>
            Autonomous Threshold: ≥ 72%
          </div>
        </div>

        {/* Real-time Metric Indicators */}
        <div style={{ display: 'flex', justifyContent: 'space-around', textAlign: 'center' }}>
          <div style={{ padding: '4px 8px' }}>
            <div style={{ fontSize: '10px', color: '#94a3b8' }}>Focus (Φ)</div>
            <div style={{ fontSize: '15px', fontWeight: 700, color: focusScore >= 75 ? '#10b981' : '#f43f5e' }}>{focusScore}</div>
          </div>
          <div style={{ padding: '4px 8px' }}>
            <div style={{ fontSize: '10px', color: '#94a3b8' }}>Glare</div>
            <div style={{ fontSize: '15px', fontWeight: 700, color: glareScore <= 12 ? '#10b981' : '#f43f5e' }}>{glareScore}%</div>
          </div>
          <div style={{ padding: '4px 8px' }}>
            <div style={{ fontSize: '10px', color: '#94a3b8' }}>Motion</div>
            <div style={{ fontSize: '15px', fontWeight: 700, color: motionScore <= 9 ? '#10b981' : '#f59e0b' }}>{motionScore}</div>
          </div>
          <div style={{ padding: '4px 8px' }}>
            <div style={{ fontSize: '10px', color: '#94a3b8' }}>Retinal View</div>
            <div style={{ fontSize: '13px', fontWeight: 700, color: retinalStatus === 'RETINAL_VIEW' ? '#10b981' : '#f59e0b' }}>
              {retinalStatus === 'RETINAL_VIEW' ? 'DETECTED' : 'ALIGNING'}
            </div>
          </div>
        </div>

        {/* Actions & Manual Shutter Fallback */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', alignItems: 'center' }}>
          {isSimulatedFeed && (
            <span style={{ fontSize: '11px', color: '#f59e0b', background: 'rgba(245, 158, 11, 0.1)', padding: '4px 8px', borderRadius: '4px' }}>
              Simulated Stream
            </span>
          )}

          <button
            onClick={handleManualCapture}
            className="btn btn-primary"
            style={{
              padding: '10px 18px',
              fontSize: '13px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Camera size={16} />
            <span>{t.btn_manual_capture}</span>
          </button>
        </div>
      </div>

      {/* Research Geometry Configuration Modal */}
      {showResearchSettings && (
        <div style={{
          position: 'absolute',
          top: '60px',
          right: '20px',
          width: '320px',
          background: 'rgba(15, 23, 42, 0.95)',
          backdropFilter: 'blur(12px)',
          border: '1px solid rgba(56, 189, 248, 0.3)',
          borderRadius: '8px',
          padding: '16px',
          boxShadow: '0 12px 35px rgba(0,0,0,0.6)',
          zIndex: 100
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h4 style={{ margin: 0, fontSize: '14px', color: '#38bdf8' }}>Research Optical Geometry</h4>
            <button onClick={() => setShowResearchSettings(false)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
              <X size={16} />
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '12px' }}>
            <div>
              <label style={{ display: 'block', color: '#94a3b8', marginBottom: '4px' }}>Condensing Lens Power:</label>
              <select
                className="form-select"
                value={lensPower}
                onChange={e => setLensPower(e.target.value)}
                style={{ width: '100%', fontSize: '12px', padding: '6px' }}
              >
                <option value="+20D">+20D (3.0x magnification, 50mm working dist)</option>
                <option value="+28D">+28D (2.1x magnification, wider FOV)</option>
                <option value="+30D">+30D (High-speed screening lens)</option>
                <option value="Custom">Custom Optical Element</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', color: '#94a3b8', marginBottom: '4px' }}>
                Lens-to-Eye Distance: {lensDistanceMm} mm
              </label>
              <input
                type="range"
                min="35"
                max="75"
                value={lensDistanceMm}
                onChange={e => setLensDistanceMm(Number(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', color: '#94a3b8', marginBottom: '4px' }}>
                Phone-to-Lens Distance: {phoneToLensMm} mm
              </label>
              <input
                type="range"
                min="5"
                max="40"
                value={phoneToLensMm}
                onChange={e => setPhoneToLensMm(Number(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', color: '#94a3b8', marginBottom: '4px' }}>
                Camera Source:
              </label>
              <select
                className="form-select"
                value={selectedDeviceId}
                onChange={e => {
                  setSelectedDeviceId(e.target.value);
                  setIsSimulatedFeed(false);
                }}
                style={{ width: '100%', fontSize: '12px', padding: '6px' }}
              >
                {devices.map(d => (
                  <option key={d.deviceId} value={d.deviceId}>
                    {d.label || `Camera ${d.deviceId.slice(0, 6)}`}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setIsSimulatedFeed(!isSimulatedFeed)}
                style={{ width: '100%', fontSize: '11px', padding: '6px' }}
              >
                {isSimulatedFeed ? "Switch to Real Camera" : "Switch to Simulated Feed"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
