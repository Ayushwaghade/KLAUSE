import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { NetworkGeometry } from './NetworkGeometry';
import { NodePoints } from './NodePoints';
import { EdgeLines } from './EdgeLines';
import { SignalParticles } from './SignalParticles';
import { orbTransitionEngine } from '../../hooks/useOrbState';
import type { OrbState } from '../../hooks/useOrbState';

interface NetworkBackgroundProps {
  orbState: OrbState;
  amplitude: number;
  isPanelOpen: boolean;
}

export const NetworkBackground: React.FC<NetworkBackgroundProps> = ({
  orbState,
  amplitude,
  isPanelOpen,
}) => {
  const canvasContainerRef = useRef<HTMLDivElement | null>(null);

  // Keep references to access within the rAF loop without triggering React re-renders
  const stateRef = useRef<OrbState>(orbState);
  const amplitudeRef = useRef<number>(amplitude);
  const panelOpenRef = useRef<boolean>(isPanelOpen);

  useEffect(() => {
    stateRef.current = orbState;
  }, [orbState]);

  useEffect(() => {
    amplitudeRef.current = amplitude;
  }, [amplitude]);

  useEffect(() => {
    panelOpenRef.current = isPanelOpen;
  }, [isPanelOpen]);

  useEffect(() => {
    const container = canvasContainerRef.current;
    if (!container) return;

    // --- Scene Setup ---
    const scene = new THREE.Scene();
    
    // Zoomed out slightly to frame the 15-radius network nicely (dolly: 11.0 base)
    const camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(0, 0, 11);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance',
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    // Main translation group
    const systemGroup = new THREE.Group();
    scene.add(systemGroup);

    // --- Instantiate Neural Network Layers ---
    const geometry = new NetworkGeometry();
    const nodePoints = new NodePoints(systemGroup, geometry);
    const edgeLines = new EdgeLines(systemGroup, geometry);
    const signals = new SignalParticles(systemGroup, geometry);

    // --- Resize handler ---
    const handleResize = () => {
      if (!container || !renderer || !camera) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    const resizeObserver = new ResizeObserver(() => handleResize());
    resizeObserver.observe(container);

    // --- Render Loop ---
    let animId: number;
    const clock = new THREE.Clock();
    let lastTime = 0;

    const render = () => {
      const state = stateRef.current;
      const amp = amplitudeRef.current;
      const panelOpen = panelOpenRef.current;

      // Smart Standby Throttling
      if (document.hidden) {
        animId = requestAnimationFrame(render);
        const curr = clock.getElapsedTime();
        if (curr - lastTime < 1 / 20) return;
        lastTime = curr;
      } else {
        animId = requestAnimationFrame(render);
      }

      const time = clock.getElapsedTime();

      // Update the FSM transition engine
      const transitionState = orbTransitionEngine.update();
      const visualState = orbTransitionEngine.currentVisualState;
      const intensity = orbTransitionEngine.visualIntensity;
      const collapse = orbTransitionEngine.collapseActive;
      const radiate = orbTransitionEngine.radiateActive;

      // Smooth horizontal offset translation when panel opens
      const targetX = panelOpen ? -2.5 : 0;
      systemGroup.position.x = THREE.MathUtils.lerp(systemGroup.position.x, targetX, 0.07);

      // Camera dolly zoom effect: dolly out when panel opens
      const targetZ = panelOpen ? 12.5 : 11.0;
      camera.position.z = THREE.MathUtils.lerp(camera.position.z, targetZ, 0.07);

      // Update network children
      nodePoints.update(time, visualState, amp, intensity);
      edgeLines.update(visualState, intensity);
      signals.update(time, visualState, amp, intensity, collapse, radiate);

      renderer.render(scene, camera);
    };

    render();

    // --- Cleanup ---
    return () => {
      cancelAnimationFrame(animId);
      resizeObserver.disconnect();

      // Dispose resources
      nodePoints.dispose();
      edgeLines.dispose();
      signals.dispose();

      renderer.dispose();
      if (container && renderer.domElement) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div
      ref={canvasContainerRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: 0,
        pointerEvents: 'none',
        overflow: 'hidden',
      }}
    />
  );
};
export type { OrbState };
