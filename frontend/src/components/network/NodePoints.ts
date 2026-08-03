import * as THREE from 'three';
import { NetworkGeometry } from './NetworkGeometry';
import type { OrbState } from '../../hooks/useOrbState';

export class NodePoints {
  private geometry: THREE.BufferGeometry;
  private material: THREE.ShaderMaterial;
  private points: THREE.Points;
  private networkGeom: NetworkGeometry;
  private scene: THREE.Scene;

  private sizeArray: Float32Array;
  private opacityArray: Float32Array;

  constructor(scene: THREE.Scene, networkGeom: NetworkGeometry) {
    this.scene = scene;
    this.networkGeom = networkGeom;

    const count = this.networkGeom.totalNodes;
    this.geometry = new THREE.BufferGeometry();

    const positions = new Float32Array(count * 3);
    this.sizeArray = new Float32Array(count);
    this.opacityArray = new Float32Array(count);

    // Initial position transfer
    for (let i = 0; i < count; i++) {
      const node = this.networkGeom.nodes[i];
      positions[i * 3] = node.position.x;
      positions[i * 3 + 1] = node.position.y;
      positions[i * 3 + 2] = node.position.z;

      // Small inner nodes, larger outer nodes
      this.sizeArray[i] = node.layer === 0 ? 1.5 : (node.layer === 4 ? 3.0 : 2.2);
      this.opacityArray[i] = 0.65;
    }

    this.geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    this.geometry.setAttribute('aSize', new THREE.BufferAttribute(this.sizeArray, 1));
    this.geometry.setAttribute('aOpacity', new THREE.BufferAttribute(this.opacityArray, 1));

    // Custom vertex shader for perspective-scaling
    const vertexShader = `
      attribute float aSize;
      attribute float aOpacity;
      varying float vOpacity;

      void main() {
        vOpacity = aOpacity;
        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        // Scale size by perspective distance (standard formula)
        gl_PointSize = aSize * (24.0 / -mvPosition.z);
        gl_Position = projectionMatrix * mvPosition;
      }
    `;

    // Custom fragment shader for crisp circles
    const fragmentShader = `
      varying float vOpacity;

      void main() {
        vec2 center = gl_PointCoord - vec2(0.5);
        float dist = length(center);
        if (dist > 0.5) discard;
        
        // Smooth circle edge
        float alpha = smoothstep(0.48, 0.40, dist);
        
        // Pure bright ice-white color
        vec3 color = vec3(0.91, 0.98, 1.0);
        
        gl_FragColor = vec4(color, alpha * vOpacity);
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

  public update(time: number, orbState: OrbState, amplitude: number, transitionIntensity: number): void {
    const count = this.networkGeom.totalNodes;
    const posAttr = this.geometry.getAttribute('position') as THREE.BufferAttribute;
    const opacAttr = this.geometry.getAttribute('aOpacity') as THREE.BufferAttribute;

    // Adjust parameters based on state
    let driftFactor = 0.12;
    let speedMult = 1.0;
    let baseOpacity = 0.65;

    if (orbState === 'processing') {
      driftFactor = 0.22;
      speedMult = 2.4;
      baseOpacity = 0.85;
    } else if (orbState === 'listening') {
      driftFactor = 0.12 + amplitude * 0.4;
      speedMult = 1.0 + amplitude * 1.5;
      baseOpacity = 0.7 + amplitude * 0.3;
    } else if (orbState === 'responding') {
      driftFactor = 0.15;
      speedMult = 1.2;
      baseOpacity = 0.75;
    } else if (orbState === 'error') {
      driftFactor = 0.05;
      speedMult = 0.3;
      baseOpacity = 0.4;
    }

    // Apply smooth visual intensity scale from the transition engine
    baseOpacity *= transitionIntensity;

    for (let i = 0; i < count; i++) {
      const node = this.networkGeom.nodes[i];
      const speed = node.speed * speedMult;

      // Clean 3D sinusoidal coordinate drift
      node.position.x = node.basePosition.x + Math.sin(time * speed + node.phaseX) * driftFactor;
      node.position.y = node.basePosition.y + Math.cos(time * speed + node.phaseY) * driftFactor;
      node.position.z = node.basePosition.z + Math.sin(time * speed + node.phaseZ) * driftFactor;

      posAttr.setXYZ(i, node.position.x, node.position.y, node.position.z);

      // Procedural wave pattern if processing, else steady base opacity
      if (orbState === 'processing') {
        const wave = Math.sin(time * 6.0 - node.layer * 1.2 + node.phaseX) * 0.25 + 0.65;
        this.opacityArray[i] = wave * transitionIntensity;
      } else {
        this.opacityArray[i] = baseOpacity;
      }
    }

    posAttr.needsUpdate = true;
    opacAttr.needsUpdate = true;
  }

  public dispose(): void {
    this.scene.remove(this.points);
    this.geometry.dispose();
    this.material.dispose();
  }
}
