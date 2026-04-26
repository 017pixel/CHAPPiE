import { Canvas, useFrame } from "@react-three/fiber";
import { useRef, useMemo } from "react";
import * as THREE from "three";
import type { Mesh, BufferGeometry, Points } from "three";

type EmotionState = {
  happiness: number;
  trust: number;
  energy: number;
  curiosity: number;
  frustration: number;
  motivation: number;
  sadness: number;
};

/* ─── helpers ─── */
function lerp(a: number, b: number, t: number) {
  return a + (b - a) * Math.min(1, Math.max(0, t));
}

function hslToRgb(h: number, s: number, l: number): [number, number, number] {
  const k = (n: number) => (n + h * 12) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  return [f(0), f(8), f(4)];
}

/* ─── 3D noise (FBM) ─── */
function noise3D(x: number, y: number, z: number): number {
  return (
    Math.sin(x * 1.2 + y * 0.7) *
    Math.cos(y * 0.9 - z * 1.1) *
    Math.sin(z * 1.3 + x * 0.5) *
    0.5 +
    Math.sin(x * 2.3 + z * 1.7) *
    Math.cos(y * 2.1 - x * 1.3) *
    0.25
  );
}

function fbm3D(x: number, y: number, z: number, octaves = 3): number {
  let v = 0;
  let amp = 0.5;
  let freq = 1;
  for (let i = 0; i < octaves; i++) {
    v += amp * noise3D(x * freq, y * freq, z * freq);
    amp *= 0.5;
    freq *= 2;
  }
  return v;
}

/* ─── Living Orb ─── */
function LivingOrb({ emotions }: { emotions: EmotionState }) {
  const meshRef = useRef<Mesh>(null);
  const basePositions = useRef<Float32Array | null>(null);

  const {
    happiness,
    trust,
    energy,
    curiosity,
    frustration,
    motivation,
    sadness,
  } = emotions;

  useFrame((state) => {
    if (!meshRef.current) return;
    const geom = meshRef.current.geometry;
    if (!geom) return;

    const posAttr = geom.attributes.position;
    const positions = posAttr.array as Float32Array;

    if (!basePositions.current) {
      basePositions.current = new Float32Array(positions);
    }

    const base = basePositions.current;
    const time = state.clock.elapsedTime;

    /* emotion-derived params */
    const surfaceAmp =
      0.04 + (frustration / 100) * 0.3 + (energy / 100) * 0.05;
    const surfaceFreq = 0.6 + (curiosity / 100) * 2.0;
    const surfaceSpeed = 0.15 + (energy / 100) * 1.2;
    const pulseAmp = 0.02 + (energy / 100) * 0.06;
    const baseFreq = 0.8 + (energy / 100) * 3.5;
    const pulseNoise = (frustration / 100) * 0.4;

    /* multi-band pulse */
    const pulse =
      1 +
      Math.sin(time * baseFreq) * pulseAmp +
      Math.sin(time * baseFreq * 1.7) *
        pulseAmp *
        0.5 *
        (frustration / 100) +
      (Math.random() - 0.5) * pulseNoise * 0.02;

    /* vertex displacement */
    for (let i = 0; i < positions.length; i += 3) {
      const bx = base[i];
      const by = base[i + 1];
      const bz = base[i + 2];

      const nx = bx * surfaceFreq + time * surfaceSpeed;
      const ny = by * surfaceFreq + time * surfaceSpeed * 0.7;
      const nz = bz * surfaceFreq + time * surfaceSpeed * 0.5;

      const displacement =
        fbm3D(nx, ny, nz, 3) * surfaceAmp +
        fbm3D(nx * 2.1 + 10, ny * 2.1 + 20, nz * 2.1 + 30, 2) *
          surfaceAmp *
          0.4;

      /* sadness creates sunken areas */
      const sadnessFactor =
        1 -
        (sadness / 100) *
          0.15 *
          Math.abs(fbm3D(nx * 0.5, ny * 0.5, nz * 0.5, 2));

      const scale = pulse * (1 + displacement) * sadnessFactor;

      positions[i] = bx * scale;
      positions[i + 1] = by * scale;
      positions[i + 2] = bz * scale;
    }

    posAttr.needsUpdate = true;

    /* rotation with emotional wobble */
    meshRef.current.rotation.y = time * (0.2 + energy / 500);
    meshRef.current.rotation.x =
      Math.sin(time * 0.3) * 0.1 * (happiness / 100);
    meshRef.current.rotation.z =
      Math.cos(time * 0.25) * 0.05 * (frustration / 100);
  });

  /* colour */
  const hue =
    0.35 +
    (frustration / 100) * -0.35 +
    (sadness / 100) * -0.1 +
    (motivation / 100) * 0.05;
  const saturation =
    0.4 + (happiness / 100) * 0.4 + (energy / 100) * 0.2;
  const lightness =
    0.35 + (energy / 100) * 0.25 - (sadness / 100) * 0.15;
  const [r, g, b] = hslToRgb(hue, saturation, lightness);

  const emissiveHue = hue + 0.05;
  const [er, eg, eb] = hslToRgb(
    emissiveHue,
    saturation * 0.8,
    lightness * 0.6
  );

  const roughness = 0.1 + (frustration / 100) * 0.7;
  const metalness = 0.1 + (trust / 100) * 0.4;
  const emissiveIntensity = 0.3 + (energy / 100) * 2.5;

  return (
    <mesh ref={meshRef}>
      <icosahedronGeometry args={[1.2, 3]} />
      <meshPhysicalMaterial
        color={new THREE.Color(r, g, b)}
        emissive={new THREE.Color(er, eg, eb)}
        emissiveIntensity={emissiveIntensity}
        metalness={metalness}
        roughness={roughness}
        flatShading={frustration > 35}
        transmission={0.05 + trust / 2000}
        thickness={0.5}
        ior={1.2 + happiness / 500}
        clearcoat={0.1 + trust / 500}
        clearcoatRoughness={Math.max(0, 0.4 - trust / 250)}
        toneMapped={false}
      />
    </mesh>
  );
}

/* ─── Inner Core ─── */
function InnerCore({ emotions }: { emotions: EmotionState }) {
  const meshRef = useRef<Mesh>(null);
  const { energy, frustration, happiness } = emotions;

  useFrame((state) => {
    if (!meshRef.current) return;
    const time = state.clock.elapsedTime;
    const freq = 1.2 + energy / 30;
    const pulse = 1 + Math.sin(time * freq) * (0.08 + energy / 1000);
    meshRef.current.scale.setScalar(pulse);
    meshRef.current.rotation.y = time * (0.5 + energy / 100);
    meshRef.current.rotation.x = time * 0.3;
  });

  const hue = 0.35 + (frustration / 100) * -0.25;
  const [r, g, b] = hslToRgb(hue, 0.7, 0.5 + happiness / 200);
  const emissiveInt = 0.5 + energy / 50;

  return (
    <mesh ref={meshRef}>
      <icosahedronGeometry args={[0.35, 2]} />
      <meshStandardMaterial
        color={new THREE.Color(r, g, b)}
        emissive={new THREE.Color(r * 1.3, g * 1.3, b * 1.3)}
        emissiveIntensity={emissiveInt}
        transparent
        opacity={0.35 + energy / 200}
        toneMapped={false}
      />
    </mesh>
  );
}

/* ─── Orb Glow (simulated bloom) ─── */
function OrbGlow({ emotions }: { emotions: EmotionState }) {
  const meshRef = useRef<Mesh>(null);
  const { energy, happiness, frustration, sadness } = emotions;

  useFrame((state) => {
    if (!meshRef.current) return;
    const time = state.clock.elapsedTime;
    const pulse =
      1 +
      Math.sin(time * (0.8 + energy / 100)) * (0.05 + energy / 500);
    meshRef.current.scale.setScalar(pulse);
  });

  const hue = 0.35 + (frustration / 100) * -0.35 + (sadness / 100) * -0.1;
  const [r, g, b] = hslToRgb(hue, 0.5, 0.5);
  const intensity = 0.2 + energy / 200 + happiness / 300;

  return (
    <mesh ref={meshRef}>
      <icosahedronGeometry args={[1.4, 2]} />
      <meshBasicMaterial
        color={new THREE.Color(r, g, b)}
        transparent
        opacity={intensity * 0.12}
        side={THREE.BackSide}
        toneMapped={false}
        depthWrite={false}
      />
    </mesh>
  );
}

/* ─── Particle Field ─── */
function ParticleField({ emotions }: { emotions: EmotionState }) {
  const pointsRef = useRef<Points>(null);
  const count = 100;

  const { energy, frustration, happiness } = emotions;

  const [positions] = useMemo(() => {
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 2 + Math.random() * 2;
      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = r * Math.cos(phi);
    }
    return [pos];
  }, []);

  useFrame((state) => {
    if (!pointsRef.current) return;
    const posAttr = pointsRef.current.geometry.attributes.position;
    const pos = posAttr.array as Float32Array;
    const time = state.clock.elapsedTime;

    const chaos = frustration / 100;
    const speed = 0.002 + energy / 8000;

    for (let i = 0; i < count; i++) {
      const i3 = i * 3;

      pos[i3] +=
        Math.sin(time * 0.5 + i) * speed * (1 + chaos * 4);
      pos[i3 + 1] +=
        Math.cos(time * 0.3 + i * 1.3) * speed * (1 + chaos * 4);
      pos[i3 + 2] +=
        Math.sin(time * 0.7 + i * 0.7) * speed * (1 + chaos * 4);

      const dist = Math.sqrt(
        pos[i3] ** 2 + pos[i3 + 1] ** 2 + pos[i3 + 2] ** 2
      );
      const targetR = 2.5 + Math.sin(time * 0.2 + i) * 0.6;
      if (dist < 1.8 || dist > 4.5) {
        const scale = targetR / dist;
        pos[i3] *= scale;
        pos[i3 + 1] *= scale;
        pos[i3 + 2] *= scale;
      }
    }

    posAttr.needsUpdate = true;
  });

  const color = useMemo(() => {
    const hue = 0.35 + (frustration / 100) * -0.35;
    const [r, g, b] = hslToRgb(hue, 0.6, 0.7);
    return new THREE.Color(r, g, b);
  }, [frustration]);

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.035}
        color={color}
        transparent
        opacity={0.5 + energy / 200}
        sizeAttenuation
        toneMapped={false}
      />
    </points>
  );
}

/* ─── Scene composition ─── */
function Scene({ emotions }: { emotions: EmotionState }) {
  return (
    <>
      <ambientLight intensity={0.4} />
      <pointLight position={[3, 3, 4]} intensity={15} color="#f4efe6" />
      <pointLight position={[-3, -2, 2]} intensity={8} color="#6a8d73" />
      <pointLight position={[0, -3, -2]} intensity={5} color="#3d5a44" />

      <LivingOrb emotions={emotions} />
      <InnerCore emotions={emotions} />
      <OrbGlow emotions={emotions} />
      <ParticleField emotions={emotions} />
    </>
  );
}

/* ─── Export ─── */
export function VisualizerCanvas({ emotions }: { emotions: EmotionState }) {
  return (
    <div className="h-[26rem] overflow-hidden rounded-[2rem] bg-[#0a0a0a]">
      <Canvas camera={{ position: [0, 0, 4.8], fov: 50 }} dpr={[1, 2]}>
        <Scene emotions={emotions} />
      </Canvas>
    </div>
  );
}
