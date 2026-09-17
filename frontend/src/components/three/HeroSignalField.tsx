import React, { useRef, useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

interface HeroSignalFieldProps {
  progress: number;
  pointerRef: React.MutableRefObject<{ x: number; y: number }>;
  reducedMotion?: boolean;
}

export const HeroSignalField: React.FC<HeroSignalFieldProps> = ({
  progress,
  pointerRef,
  reducedMotion = false,
}) => {
  const { camera } = useThree();
  const groupRef = useRef<THREE.Group>(null);
  const coreRef = useRef<THREE.Mesh>(null);
  const ring1Ref = useRef<THREE.Mesh>(null);
  const ring2Ref = useRef<THREE.Mesh>(null);
  const ring3Ref = useRef<THREE.Mesh>(null);
  const branchesRef = useRef<THREE.Group>(null);

  // Particles for subtle ambient evidence field
  const particleCount = reducedMotion ? 30 : 90;
  const [particlesPos, particleColors] = useMemo(() => {
    const pos = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount; i++) {
      const radius = 2.5 + Math.random() * 4.5;
      const theta = Math.random() * Math.PI * 2;
      const phi = (Math.random() - 0.5) * Math.PI;

      pos[i * 3] = radius * Math.cos(theta) * Math.cos(phi);
      pos[i * 3 + 1] = radius * Math.sin(phi);
      pos[i * 3 + 2] = radius * Math.sin(theta) * Math.cos(phi);

      // Color scheme: mostly subtle cool slate with occasional green / amber / violet accents
      const r = Math.random();
      if (r < 0.2) {
        // Emerald
        colors[i * 3] = 0.06;
        colors[i * 3 + 1] = 0.72;
        colors[i * 3 + 2] = 0.5;
      } else if (r < 0.4) {
        // Amber
        colors[i * 3] = 0.96;
        colors[i * 3 + 1] = 0.62;
        colors[i * 3 + 2] = 0.04;
      } else if (r < 0.6) {
        // Violet / Indigo
        colors[i * 3] = 0.39;
        colors[i * 3 + 1] = 0.4;
        colors[i * 3 + 2] = 0.95;
      } else {
        // Graphite
        colors[i * 3] = 0.35;
        colors[i * 3 + 1] = 0.35;
        colors[i * 3 + 2] = 0.4;
      }
    }
    return [pos, colors];
  }, [particleCount, reducedMotion]);

  // Procedural branch lines for competing hypotheses (Hypothesis A vs B vs C)
  const [branch1Geo, branch2Geo, counterGeo] = useMemo(() => {
    // Branch 1: Checkout regression (primary, bends right)
    const pts1 = [
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(0.8, 0.4, 0.4),
      new THREE.Vector3(1.8, 0.7, 0.6),
      new THREE.Vector3(2.8, 0.9, 0.5),
    ];
    const b1 = new THREE.BufferGeometry().setFromPoints(pts1);

    // Branch 2: Tracking failure (alternative, bends left)
    const pts2 = [
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(-0.8, -0.3, 0.3),
      new THREE.Vector3(-1.7, -0.5, 0.7),
      new THREE.Vector3(-2.6, -0.8, 1.0),
    ];
    const b2 = new THREE.BufferGeometry().setFromPoints(pts2);

    // Counter-evidence ray intersecting branch 1
    const ptsCounter = [
      new THREE.Vector3(3.2, -1.2, -0.5),
      new THREE.Vector3(2.3, -0.2, 0.2),
      new THREE.Vector3(1.8, 0.7, 0.6), // Intersects branch 1
    ];
    const bCounter = new THREE.BufferGeometry().setFromPoints(ptsCounter);

    return [b1, b2, bCounter];
  }, []);

  useFrame((_, delta) => {
    // 1. Subtle camera interpolation along z & y based on scroll progress
    const targetCameraZ = 6.0 + progress * 3.5;
    const targetCameraY = (progress - 0.5) * 1.5;
    const targetCameraX = Math.sin(progress * Math.PI) * 0.8;

    // Pointer parallax (damped)
    const px = pointerRef.current.x * 0.3;
    const py = pointerRef.current.y * 0.2;

    camera.position.z += (targetCameraZ - camera.position.z) * 0.05;
    camera.position.y += (targetCameraY + py - camera.position.y) * 0.05;
    camera.position.x += (targetCameraX + px - camera.position.x) * 0.05;
    camera.lookAt(0, 0, 0);

    if (reducedMotion) return;

    // 2. Continuous slow rotation of the core signal object
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.15;
      groupRef.current.rotation.x = Math.sin(progress * Math.PI * 2) * 0.25;
    }

    if (ring1Ref.current) {
      ring1Ref.current.rotation.x += delta * 0.2;
      ring1Ref.current.rotation.y += delta * 0.1;
    }
    if (ring2Ref.current) {
      ring2Ref.current.rotation.y -= delta * 0.25;
      ring2Ref.current.rotation.z += delta * 0.15;
    }
    if (ring3Ref.current) {
      ring3Ref.current.rotation.z += delta * 0.18;
    }

    // 3. Morph core scale and pulse based on phase
    if (coreRef.current) {
      const pulse = 1 + Math.sin(Date.now() * 0.003) * 0.05;
      const phaseScale = 1 + Math.sin(progress * Math.PI) * 0.4;
      coreRef.current.scale.setScalar(pulse * phaseScale);
    }

    // 4. Update branch position based on progress
    if (branchesRef.current) {
      branchesRef.current.position.y = Math.sin(progress * Math.PI) * 0.2;
    }
  });

  // Calculate phase-specific opacities
  const showAnomaly = progress >= 0.12 && progress < 0.38;
  const showHypotheses = progress >= 0.35 && progress < 0.8;
  const showCounterEvidence = progress >= 0.52 && progress < 0.75;
  const showVerification = progress >= 0.82;

  return (
    <group ref={groupRef}>
      {/* Central Engineered Signal Core */}
      <mesh ref={coreRef}>
        <icosahedronGeometry args={[1.1, 2]} />
        <meshStandardMaterial
          color={showAnomaly ? '#EF4444' : showVerification ? '#10B981' : '#6366F1'}
          wireframe
          wireframeLinewidth={1.5}
          emissive={showAnomaly ? '#7F1D1D' : showVerification ? '#064E3B' : '#312E81'}
          emissiveIntensity={0.6}
          roughness={0.2}
          metalness={0.8}
        />
      </mesh>

      {/* Thin Orbit Rings */}
      <mesh ref={ring1Ref}>
        <torusGeometry args={[1.8, 0.015, 16, 64]} />
        <meshBasicMaterial color="#4338CA" transparent opacity={0.6} />
      </mesh>

      <mesh ref={ring2Ref}>
        <torusGeometry args={[2.3, 0.012, 16, 64]} />
        <meshBasicMaterial
          color={showCounterEvidence ? '#F59E0B' : '#4B5563'}
          transparent
          opacity={0.5}
        />
      </mesh>

      <mesh ref={ring3Ref}>
        <torusGeometry args={[2.9, 0.01, 16, 64]} />
        <meshBasicMaterial
          color={showVerification ? '#10B981' : '#374151'}
          transparent
          opacity={showVerification ? 0.8 : 0.35}
        />
      </mesh>

      {/* Orbiting Evidence Particles */}
      <points>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[particlesPos, 3]}
          />
          <bufferAttribute
            attach="attributes-color"
            args={[particleColors, 3]}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.06}
          vertexColors
          transparent
          opacity={0.75}
          sizeAttenuation
        />
      </points>

      {/* Competing Hypothesis Branches (Visible in investigation & challenge phases) */}
      <group ref={branchesRef} visible={showHypotheses}>
        {/* Branch 1: Checkout Regression (initial leader) */}
        {/* Line 1 dims when counter evidence is introduced */}
        {/* @ts-ignore line */}
        <primitive object={new THREE.Line(branch1Geo, new THREE.LineBasicMaterial({
          color: showCounterEvidence ? '#4B5563' : '#6366F1',
          linewidth: showCounterEvidence ? 1 : 2,
          transparent: true,
          opacity: showCounterEvidence ? 0.3 : 0.9,
        }))} />

        {/* Branch 2: Tracking Failure (rises after counter evidence) */}
        {/* @ts-ignore line */}
        <primitive object={new THREE.Line(branch2Geo, new THREE.LineBasicMaterial({
          color: showCounterEvidence ? '#10B981' : '#4B5563',
          linewidth: showCounterEvidence ? 2.5 : 1,
          transparent: true,
          opacity: showCounterEvidence ? 0.95 : 0.4,
        }))} />

        {/* Counter Evidence Ray */}
        {showCounterEvidence && (
          // @ts-ignore line
          <primitive object={new THREE.Line(counterGeo, new THREE.LineBasicMaterial({
            color: '#EF4444',
            linewidth: 2,
            transparent: true,
            opacity: 0.9,
          }))} />
        )}
      </group>

      {/* Verification Closed Loop (Active at 85%+) */}
      {showVerification && (
        <group rotation={[Math.PI / 4, 0, 0]}>
          <mesh>
            <torusGeometry args={[1.5, 0.03, 16, 80]} />
            <meshBasicMaterial color="#10B981" transparent opacity={0.85} />
          </mesh>
        </group>
      )}
    </group>
  );
};
