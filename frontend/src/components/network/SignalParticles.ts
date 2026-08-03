import * as THREE from 'three';
import { NetworkGeometry } from './NetworkGeometry';
import type { OrbState } from '../../hooks/useOrbState';

interface SignalInstance {
  path: number[];
  pathIndex: number;
  t: number;
  active: boolean;
  speed: number;
}

export class SignalParticles {
  private geometry: THREE.BufferGeometry;
  private material: THREE.ShaderMaterial;
  private points: THREE.Points;
  private networkGeom: NetworkGeometry;
  private scene: THREE.Scene;

  private maxSignals = 150;
  private signals: SignalInstance[] = [];
  private lastSpawnTime = 0;

  private positionArray: Float32Array;
  private alphaArray: Float32Array;

  constructor(scene: THREE.Scene, networkGeom: NetworkGeometry) {
    this.scene = scene;
    this.networkGeom = networkGeom;

    this.geometry = new THREE.BufferGeometry();
    this.positionArray = new Float32Array(this.maxSignals * 3);
    this.alphaArray = new Float32Array(this.maxSignals);

    // Initialize all signals as inactive
    for (let i = 0; i < this.maxSignals; i++) {
      this.signals.push({
        path: [],
        pathIndex: 0,
        t: 0,
        active: false,
        speed: 0.5,
      });
      this.alphaArray[i] = 0.0;
    }

    this.geometry.setAttribute('position', new THREE.BufferAttribute(this.positionArray, 3));
    this.geometry.setAttribute('aAlpha', new THREE.BufferAttribute(this.alphaArray, 1));

    const vertexShader = `
      attribute float aAlpha;
      varying float vAlpha;

      void main() {
        vAlpha = aAlpha;
        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        // Slightly larger than nodes, crisp sparks
        gl_PointSize = 4.5 * (15.0 / -mvPosition.z);
        gl_Position = projectionMatrix * mvPosition;
      }
    `;

    const fragmentShader = `
      varying float vAlpha;

      void main() {
        vec2 center = gl_PointCoord - vec2(0.5);
        float dist = length(center);
        if (dist > 0.5) discard;

        float alpha = smoothstep(0.48, 0.40, dist);
        
        // Solid white-hot cores
        vec3 color = vec3(0.91, 0.98, 1.0);
        
        gl_FragColor = vec4(color, alpha * vAlpha);
      }
    `;

    this.material = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });

    this.points = new THREE.Points(this.geometry, this.material);
    this.scene.add(this.points);
  }

  public update(
    time: number,
    orbState: OrbState,
    amplitude: number,
    transitionIntensity: number,
    collapseActive: boolean,
    radiateActive: boolean
  ): void {
    const posAttr = this.geometry.getAttribute('position') as THREE.BufferAttribute;
    const alphaAttr = this.geometry.getAttribute('aAlpha') as THREE.BufferAttribute;

    // 1. Spawning controls
    let spawnInterval = 180; // ms
    let signalSpeed = 1.0;
    let maxToSpawn = 1;

    if (orbState === 'processing') {
      spawnInterval = 35;
      signalSpeed = 2.5;
      maxToSpawn = 2;
    } else if (orbState === 'listening') {
      spawnInterval = 80 - Math.min(amplitude * 60, 60);
      signalSpeed = 1.4;
    } else if (orbState === 'responding') {
      spawnInterval = 60;
      signalSpeed = 1.8;
    } else if (orbState === 'error') {
      spawnInterval = 300;
      signalSpeed = 0.5;
    }

    const now = performance.now();
    if (now - this.lastSpawnTime >= spawnInterval) {
      this.lastSpawnTime = now;

      // Try spawning new signal routes
      for (let k = 0; k < maxToSpawn; k++) {
        const path = this.networkGeom.getRandomPath();
        if (path.length > 1) {
          const inactiveIndex = this.signals.findIndex((s) => !s.active);
          if (inactiveIndex !== -1) {
            this.signals[inactiveIndex] = {
              path,
              pathIndex: 0,
              t: 0,
              active: true,
              speed: signalSpeed * (0.85 + Math.random() * 0.3),
            };
          }
        }
      }
    }

    // 2. Animate and position existing signals
    const dt = 0.016; // Fixed timestep slice approx 60fps
    const nodes = this.networkGeom.nodes;

    for (let i = 0; i < this.maxSignals; i++) {
      const sig = this.signals[i];

      if (!sig.active) {
        this.alphaArray[i] = 0.0;
        this.positionArray[i * 3] = 0;
        this.positionArray[i * 3 + 1] = 0;
        this.positionArray[i * 3 + 2] = 0;
        continue;
      }

      // Advance route percentage
      sig.t += sig.speed * dt;
      if (sig.t >= 1.0) {
        sig.t = 0;
        sig.pathIndex++;
        if (sig.pathIndex >= sig.path.length - 1) {
          sig.active = false;
          this.alphaArray[i] = 0.0;
          continue;
        }
      }

      // Find path nodes
      const fromNodeIdx = sig.path[sig.pathIndex];
      const toNodeIdx = sig.path[sig.pathIndex + 1];

      const fromNode = nodes[fromNodeIdx];
      const toNode = nodes[toNodeIdx];

      if (!fromNode || !toNode) {
        sig.active = false;
        this.alphaArray[i] = 0.0;
        continue;
      }

      // Interpolate position along the current segment path
      let x = THREE.MathUtils.lerp(fromNode.position.x, toNode.position.x, sig.t);
      let y = THREE.MathUtils.lerp(fromNode.position.y, toNode.position.y, sig.t);
      let z = THREE.MathUtils.lerp(fromNode.position.z, toNode.position.z, sig.t);

      // Transition effects
      if (collapseActive) {
        // Force signals to drop inwards toward the center geometry origin (0,0,0)
        const collapseScale = 1.0 - sig.t;
        x *= collapseScale;
        y *= collapseScale;
        z *= collapseScale;
      } else if (radiateActive) {
        // Accelerate outwards
        sig.speed = signalSpeed * 3.5;
      }

      this.positionArray[i * 3] = x;
      this.positionArray[i * 3 + 1] = y;
      this.positionArray[i * 3 + 2] = z;

      // Soft opacity falloff near path boundaries
      let alpha = 0.9;
      if (sig.pathIndex === 0 && sig.t < 0.2) {
        alpha = (sig.t / 0.2) * 0.9; // fade-in
      } else if (sig.pathIndex === sig.path.length - 2 && sig.t > 0.8) {
        alpha = ((1.0 - sig.t) / 0.2) * 0.9; // fade-out
      }

      this.alphaArray[i] = alpha * transitionIntensity;
    }

    posAttr.needsUpdate = true;
    alphaAttr.needsUpdate = true;
  }

  public dispose(): void {
    this.scene.remove(this.points);
    this.geometry.dispose();
    this.material.dispose();
  }
}
