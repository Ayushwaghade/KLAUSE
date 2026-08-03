import * as THREE from 'three';
import { NetworkGeometry } from './NetworkGeometry';
import type { OrbState } from '../../hooks/useOrbState';

export class EdgeLines {
  private geometry: THREE.BufferGeometry;
  private material: THREE.LineBasicMaterial;
  private lineSegments: THREE.LineSegments;
  private networkGeom: NetworkGeometry;
  private scene: THREE.Scene;

  constructor(scene: THREE.Scene, networkGeom: NetworkGeometry) {
    this.scene = scene;
    this.networkGeom = networkGeom;

    this.geometry = new THREE.BufferGeometry();

    const edgeCount = this.networkGeom.edges.length;
    // 2 endpoints per edge, 3 floats per coordinate
    const positions = new Float32Array(edgeCount * 2 * 3);

    this.geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    // Base materials specs: Ice cyan
    this.material = new THREE.LineBasicMaterial({
      color: 0x4fc3f7,
      opacity: 0.12,
      transparent: true,
      depthWrite: false,
    });

    this.lineSegments = new THREE.LineSegments(this.geometry, this.material);
    this.scene.add(this.lineSegments);
  }

  public update(orbState: OrbState, transitionIntensity: number): void {
    const posAttr = this.geometry.getAttribute('position') as THREE.BufferAttribute;
    const edgeCount = this.networkGeom.edges.length;

    // Direct read endpoints from the animated node coordinate vectors
    for (let i = 0; i < edgeCount; i++) {
      const edge = this.networkGeom.edges[i];
      const fromNode = this.networkGeom.nodes[edge.from];
      const toNode = this.networkGeom.nodes[edge.to];

      posAttr.setXYZ(i * 2, fromNode.position.x, fromNode.position.y, fromNode.position.z);
      posAttr.setXYZ(i * 2 + 1, toNode.position.x, toNode.position.y, toNode.position.z);
    }

    posAttr.needsUpdate = true;

    // Set segment transparency according to FSM
    let targetOpacity = 0.12;
    if (orbState === 'processing') {
      targetOpacity = 0.22;
    } else if (orbState === 'listening') {
      targetOpacity = 0.16;
    } else if (orbState === 'responding') {
      targetOpacity = 0.14;
    } else if (orbState === 'error') {
      targetOpacity = 0.05;
    }

    this.material.opacity = targetOpacity * transitionIntensity;
  }

  public dispose(): void {
    this.scene.remove(this.lineSegments);
    this.geometry.dispose();
    this.material.dispose();
  }
}
