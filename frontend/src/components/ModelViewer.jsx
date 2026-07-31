import { Suspense, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { Center, Environment, OrbitControls, useGLTF } from "@react-three/drei";

function Model({ url }) {
  const { scene } = useGLTF(url);
  return (
    <Center>
      <primitive object={scene.clone()} />
    </Center>
  );
}

export default function ModelViewer({ modelUrl, onClose }) {
  const [fullscreen, setFullscreen] = useState(false);

  if (!modelUrl) return null;

  const resolvedUrl = modelUrl.startsWith("http")
    ? modelUrl
    : `${window.location.origin}${modelUrl.startsWith("/") ? "" : "/"}${modelUrl}`;

  return (
    <div className={`model-viewer${fullscreen ? " fullscreen" : ""}`}>
      <div className="model-viewer-toolbar">
        <span>3D booth preview</span>
        <div className="model-viewer-actions">
          <button
            type="button"
            className="pressable"
            onClick={() => setFullscreen((value) => !value)}
          >
            {fullscreen ? "Exit fullscreen" : "Fullscreen"}
          </button>
          {onClose && (
            <button type="button" className="pressable" onClick={onClose}>
              Close
            </button>
          )}
        </div>
      </div>
      <div className="model-viewer-canvas">
        <Canvas camera={{ position: [2.5, 1.8, 2.5], fov: 45 }}>
          <color attach="background" args={["#1a1d24"]} />
          <ambientLight intensity={0.7} />
          <directionalLight position={[4, 6, 2]} intensity={1.1} />
          <Suspense fallback={null}>
            <Model url={resolvedUrl} />
            <Environment preset="city" />
          </Suspense>
          <OrbitControls makeDefault enableDamping />
        </Canvas>
      </div>
      <p className="model-viewer-hint">Drag to rotate · Scroll to zoom · Right-drag to pan</p>
    </div>
  );
}
