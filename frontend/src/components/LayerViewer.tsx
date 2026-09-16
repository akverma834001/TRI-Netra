import React, { useState } from 'react';
import { EyeImage } from '../types';
import { api } from '../services/api';
import { ZoomIn, ZoomOut, RotateCcw, Layers, Sliders, Eye, Sun, Maximize2 } from 'lucide-react';

interface Props {
  image: EyeImage | undefined;
  eyeLabel: string;
}

export const LayerViewer: React.FC<Props> = ({ image, eyeLabel }) => {
  const [activeTab, setActiveTab] = useState<'enhanced' | 'raw' | 'vessels' | 'lesions' | 'gradcam' | 'compare'>('enhanced');
  const [zoom, setZoom] = useState(1);
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(100);
  
  // Layer Opacities for Composite Mode
  const [vesselOpacity, setVesselOpacity] = useState(0.85);
  const [lesionOpacity, setLesionOpacity] = useState(0.90);
  const [camOpacity, setCamOpacity] = useState(0.60);

  if (!image) {
    return (
      <div className="card" style={{ height: '480px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#050811', color: '#64748b' }}>
        <p>No retinal image loaded for {eyeLabel}</p>
      </div>
    );
  }

  const rawUrl = api.getImageUrl(image.original_path);
  const enhancedUrl = image.processed_path ? api.getImageUrl(image.processed_path) : rawUrl;
  const vesselUrl = api.getImageUrl(`masks/${image.id}_vessels.png`);
  const lesionUrl = api.getImageUrl(`masks/${image.id}_lesions.png`);
  const gradcamUrl = api.getImageUrl(`heatmaps/${image.id}_gradcam.jpg`);

  const resetControls = () => {
    setZoom(1);
    setBrightness(100);
    setContrast(100);
  };

  return (
    <div className="viewer-container" style={{ flexDirection: 'column' }}>
      {/* Top Controls Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #1e293b', paddingBottom: '12px', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', gap: '4px', background: '#0f172a', padding: '4px', borderRadius: 'var(--radius-sm)' }}>
          <button
            className={`btn btn-sm ${activeTab === 'enhanced' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('enhanced')}
            style={{ fontSize: '11px' }}
          >
            Enhanced
          </button>
          <button
            className={`btn btn-sm ${activeTab === 'raw' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('raw')}
            style={{ fontSize: '11px' }}
          >
            Raw RGB
          </button>
          <button
            className={`btn btn-sm ${activeTab === 'vessels' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('vessels')}
            style={{ fontSize: '11px' }}
          >
            Vessel Map
          </button>
          <button
            className={`btn btn-sm ${activeTab === 'lesions' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('lesions')}
            style={{ fontSize: '11px' }}
          >
            Lesion Mask
          </button>
          <button
            className={`btn btn-sm ${activeTab === 'gradcam' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('gradcam')}
            style={{ fontSize: '11px' }}
          >
            AI Attention (Grad-CAM)
          </button>
          <button
            className={`btn btn-sm ${activeTab === 'compare' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('compare')}
            style={{ fontSize: '11px' }}
          >
            Side-by-Side
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button className="btn btn-secondary btn-sm" onClick={() => setZoom(prev => Math.min(prev + 0.25, 3.0))} title="Zoom In">
            <ZoomIn size={14} />
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => setZoom(prev => Math.max(prev - 0.25, 0.75))} title="Zoom Out">
            <ZoomOut size={14} />
          </button>
          <button className="btn btn-secondary btn-sm" onClick={resetControls} title="Reset View">
            <RotateCcw size={14} />
          </button>
        </div>
      </div>

      {/* Main Canvas Area */}
      {activeTab === 'compare' ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', minHeight: '440px' }}>
          <div className="canvas-wrapper">
            <div style={{ position: 'absolute', top: '10px', left: '10px', zIndex: 10, background: 'rgba(0,0,0,0.6)', padding: '2px 8px', borderRadius: '4px', fontSize: '11px' }}>
              Raw Captured Image
            </div>
            <img src={rawUrl} alt="Raw Retinal Image" className="canvas-img" style={{ transform: `scale(${zoom})`, filter: `brightness(${brightness}%) contrast(${contrast}%)` }} />
          </div>
          <div className="canvas-wrapper">
            <div style={{ position: 'absolute', top: '10px', left: '10px', zIndex: 10, background: 'rgba(0,0,0,0.6)', padding: '2px 8px', borderRadius: '4px', fontSize: '11px' }}>
              Enhanced + Mask-Gated Grad-CAM
            </div>
            <img src={gradcamUrl} alt="Grad-CAM Attention" className="canvas-img" style={{ transform: `scale(${zoom})`, filter: `brightness(${brightness}%) contrast(${contrast}%)` }} />
          </div>
        </div>
      ) : (
        <div className="canvas-wrapper" style={{ minHeight: '460px' }}>
          {/* Base Layer */}
          <img
            src={activeTab === 'raw' ? rawUrl : enhancedUrl}
            alt="Retinal Fundus Workspace"
            className="canvas-img"
            style={{
              transform: `scale(${zoom})`,
              filter: `brightness(${brightness}%) contrast(${contrast}%)`
            }}
          />

          {/* Overlays according to tab */}
          {activeTab === 'vessels' && (
            <img
              src={vesselUrl}
              alt="Vessels Layer"
              className="canvas-layer"
              style={{
                opacity: vesselOpacity,
                mixBlendMode: 'screen',
                filter: 'drop-shadow(0 0 2px #38bdf8)'
              }}
            />
          )}

          {activeTab === 'lesions' && (
            <img
              src={lesionUrl}
              alt="Lesions Layer"
              className="canvas-layer"
              style={{
                opacity: lesionOpacity,
                mixBlendMode: 'screen',
                filter: 'drop-shadow(0 0 3px #f43f5e)'
              }}
            />
          )}

          {activeTab === 'gradcam' && (
            <img
              src={gradcamUrl}
              alt="Grad-CAM Layer"
              className="canvas-layer"
              style={{ opacity: camOpacity }}
            />
          )}
        </div>
      )}

      {/* Opacity & Filter Sliders Footer */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', background: '#0a0f1d', padding: '12px 16px', borderRadius: 'var(--radius-sm)', marginTop: '12px', fontSize: '12px' }}>
        <div>
          <label style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', marginBottom: '4px' }}>
            <span>Brightness</span>
            <span>{brightness}%</span>
          </label>
          <input
            type="range"
            min="60"
            max="160"
            value={brightness}
            onChange={(e) => setBrightness(Number(e.target.value))}
            style={{ width: '100%', accentColor: 'var(--brand-cyan)' }}
          />
        </div>

        <div>
          <label style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', marginBottom: '4px' }}>
            <span>Contrast</span>
            <span>{contrast}%</span>
          </label>
          <input
            type="range"
            min="60"
            max="160"
            value={contrast}
            onChange={(e) => setContrast(Number(e.target.value))}
            style={{ width: '100%', accentColor: 'var(--brand-cyan)' }}
          />
        </div>

        <div>
          <label style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', marginBottom: '4px' }}>
            <span>Vessel Overlay</span>
            <span>{Math.round(vesselOpacity * 100)}%</span>
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={vesselOpacity}
            onChange={(e) => setVesselOpacity(Number(e.target.value))}
            style={{ width: '100%', accentColor: 'var(--brand-cyan)' }}
          />
        </div>

        <div>
          <label style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', marginBottom: '4px' }}>
            <span>Grad-CAM Overlay</span>
            <span>{Math.round(camOpacity * 100)}%</span>
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={camOpacity}
            onChange={(e) => setCamOpacity(Number(e.target.value))}
            style={{ width: '100%', accentColor: 'var(--brand-cyan)' }}
          />
        </div>
      </div>
    </div>
  );
};
