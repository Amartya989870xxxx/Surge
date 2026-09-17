import React, { Suspense, useState, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { HeroSignalField } from './HeroSignalField';
import { usePointerParallax } from '../../hooks/usePointerParallax';
import { useReducedMotion } from '../../hooks/useReducedMotion';

interface LandingCanvasProps {
  progress: number;
}

export const LandingCanvas: React.FC<LandingCanvasProps> = ({ progress }) => {
  const pointerRef = usePointerParallax();
  const reducedMotion = useReducedMotion();
  const [webglSupported, setWebglSupported] = useState(true);

  useEffect(() => {
    try {
      const canvas = document.createElement('canvas');
      const gl =
        canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      if (!gl) {
        setWebglSupported(false);
      }
    } catch {
      setWebglSupported(false);
    }
  }, []);

  if (!webglSupported) {
    return (
      <div className="w-full h-full flex items-center justify-center p-8 opacity-40">
        <svg viewBox="0 0 200 200" className="w-64 h-64">
          <circle
            cx="100"
            cy="100"
            r="80"
            stroke="#6366F1"
            strokeWidth="1"
            fill="none"
            strokeDasharray="4 4"
          />
          <circle
            cx="100"
            cy="100"
            r="55"
            stroke="#A1A1AA"
            strokeWidth="1"
            fill="none"
          />
          <polygon
            points="100,45 150,130 50,130"
            stroke="#818CF8"
            strokeWidth="1.5"
            fill="none"
          />
          <circle cx="100" cy="100" r="4" fill="#10B981" />
        </svg>
      </div>
    );
  }

  return (
    <div className="w-full h-full pointer-events-none">
      <Canvas
        camera={{ position: [0, 0, 6], fov: 45 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, alpha: true }}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 8, 5]} intensity={1.2} color="#F5F5F5" />
        <pointLight position={[-4, -4, -2]} intensity={0.5} color="#6366F1" />
        <Suspense fallback={null}>
          <HeroSignalField
            progress={progress}
            pointerRef={pointerRef}
            reducedMotion={reducedMotion}
          />
        </Suspense>
      </Canvas>
    </div>
  );
};
