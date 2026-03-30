import { Canvas, useFrame } from "@react-three/fiber";
import { useRef } from "react";
import type { Mesh } from "three";

type VisualizerCanvasProps = {
  happiness: number;
  energy: number;
  frustration: number;
};

function Orb({ happiness, energy, frustration }: VisualizerCanvasProps) {
  const meshRef = useRef<Mesh>(null);

  useFrame((state) => {
    if (!meshRef.current) return;
    meshRef.current.rotation.y = state.clock.elapsedTime * 0.35;
    meshRef.current.rotation.x = state.clock.elapsedTime * 0.12;
    const pulse = 1 + Math.sin(state.clock.elapsedTime * 1.5) * (0.02 + energy / 5000);
    meshRef.current.scale.setScalar(pulse);
  });

  return (
    <mesh ref={meshRef}>
      <icosahedronGeometry args={[1.25, 4]} />
      <meshStandardMaterial
        color={`rgb(${120 + happiness}, ${80 + energy}, ${90 + frustration})`}
        emissive={`rgb(${happiness}, ${40 + energy / 2}, ${60 + frustration / 2})`}
        metalness={0.15}
        roughness={0.25}
      />
    </mesh>
  );
}

export function VisualizerCanvas({ happiness, energy, frustration }: VisualizerCanvasProps) {
  return (
    <div className="h-[26rem] overflow-hidden rounded-[2rem] bg-[#111111]">
      <Canvas camera={{ position: [0, 0, 4.5] }}>
        <ambientLight intensity={1.1} />
        <pointLight position={[2, 2, 4]} intensity={25} color="#f26a1b" />
        <pointLight position={[-3, -2, 1]} intensity={12} color="#d7efe8" />
        <Orb happiness={happiness} energy={energy} frustration={frustration} />
      </Canvas>
    </div>
  );
}
