import * as THREE from 'three';

export interface NodeDef {
  position: THREE.Vector3;
  basePosition: THREE.Vector3;
  layer: number;
  phaseX: number;
  phaseY: number;
  phaseZ: number;
  speed: number;
}

export interface EdgeDef {
  from: number;
  to: number;
}

export class NetworkGeometry {
  public nodes: NodeDef[] = [];
  public edges: EdgeDef[] = [];
  public totalNodes: number = 0;
  
  // Keep track of which node indices belong to which layers
  private layerIndices: number[][] = [[], [], [], [], []];
  
  // Forward routing lookup: node index -> array of next layer node indices
  private forwardAdjacency: number[][] = [];

  constructor() {
    // 5 concentric layers: 40, 80, 120, 160, 100 nodes = 500 total
    const layers = [
      { count: 40, radius: 1.2, layer: 0 },
      { count: 80, radius: 2.5, layer: 1 },
      { count: 120, radius: 4.0, layer: 2 },
      { count: 160, radius: 5.8, layer: 3 },
      { count: 100, radius: 7.5, layer: 4 },
    ];

    let globalIndex = 0;
    layers.forEach((layerDef) => {
      const layerNodes = this.distributeOnSphere(layerDef.count, layerDef.radius);
      layerNodes.forEach((pos) => {
        this.nodes.push({
          position: pos.clone(),
          basePosition: pos.clone(),
          layer: layerDef.layer,
          phaseX: Math.random() * Math.PI * 2,
          phaseY: Math.random() * Math.PI * 2,
          phaseZ: Math.random() * Math.PI * 2,
          speed: 0.15 + Math.random() * 0.2, // Base speed factor
        });
        this.layerIndices[layerDef.layer].push(globalIndex);
        globalIndex++;
      });
    });

    this.totalNodes = this.nodes.length;
    this.forwardAdjacency = Array.from({ length: this.totalNodes }, () => []);

    // Create connections
    this.buildConnections();
  }

  /**
   * Distribute points evenly on a sphere using Fibonacci spiral / Golden ratio distribution
   */
  private distributeOnSphere(count: number, radius: number): THREE.Vector3[] {
    const points: THREE.Vector3[] = [];
    const phi = Math.PI * (3 - Math.sqrt(5)); // Golden angle

    for (let i = 0; i < count; i++) {
      const y = 1 - (i / (count - 1)) * 2; // y goes from 1 to -1
      const radiusAtY = Math.sqrt(1 - y * y); // radius at y

      const theta = phi * i; // Golden angle increment

      const x = Math.cos(theta) * radiusAtY;
      const z = Math.sin(theta) * radiusAtY;

      points.push(new THREE.Vector3(x * radius, y * radius, z * radius));
    }
    return points;
  }

  /**
   * Build both inter-layer (outward routing) and intra-layer (geodesic cage) linkages
   */
  private buildConnections(): void {
    const edgeSet = new Set<string>();

    const addEdge = (from: number, to: number) => {
      const key = from < to ? `${from}-${to}` : `${to}-${from}`;
      if (!edgeSet.has(key)) {
        edgeSet.add(key);
        this.edges.push({ from, to });
      }
    };

    // 1. Inter-layer outward connections: layer L -> layer L+1
    for (let l = 0; l < 4; l++) {
      const currentIndices = this.layerIndices[l];
      const nextIndices = this.layerIndices[l + 1];

      currentIndices.forEach((fromIdx) => {
        const fromNode = this.nodes[fromIdx];
        
        // Find nearest neighbors in the next layer
        const candidates = nextIndices.map((toIdx) => {
          const dist = fromNode.basePosition.distanceTo(this.nodes[toIdx].basePosition);
          return { toIdx, dist };
        });

        // Sort by distance ascending
        candidates.sort((a, b) => a.dist - b.dist);

        // Connect to 2 to 4 nearest neighbors randomly
        const connCount = 2 + Math.floor(Math.random() * 3); // 2, 3, or 4
        for (let i = 0; i < Math.min(connCount, candidates.length); i++) {
          const targetIdx = candidates[i].toIdx;
          addEdge(fromIdx, targetIdx);
          this.forwardAdjacency[fromIdx].push(targetIdx);
        }
      });
    }

    // 2. Intra-layer lateral connections: within the same layer for geodesic shell visual structure
    for (let l = 0; l < 5; l++) {
      const indices = this.layerIndices[l];
      indices.forEach((fromIdx) => {
        const fromNode = this.nodes[fromIdx];

        const candidates = indices
          .filter((idx) => idx !== fromIdx)
          .map((toIdx) => {
            const dist = fromNode.basePosition.distanceTo(this.nodes[toIdx].basePosition);
            return { toIdx, dist };
          });

        candidates.sort((a, b) => a.dist - b.dist);

        // Connect to 2 closest neighbors within the same layer
        for (let i = 0; i < Math.min(2, candidates.length); i++) {
          addEdge(fromIdx, candidates[i].toIdx);
        }
      });
    }
  }

  /**
   * Generates a random outward path from layer 0 to layer 4
   */
  public getRandomPath(): number[] {
    const path: number[] = [];
    
    // Pick random node in layer 0
    const l0 = this.layerIndices[0];
    if (l0.length === 0) return path;
    
    let currentIdx = l0[Math.floor(Math.random() * l0.length)];
    path.push(currentIdx);

    // Step outward layer by layer
    for (let l = 0; l < 4; l++) {
      const nextOptions = this.forwardAdjacency[currentIdx];
      if (!nextOptions || nextOptions.length === 0) {
        // Fallback: pick any close neighbor in next layer if path is broken
        const nextLayerIndices = this.layerIndices[l + 1];
        if (nextLayerIndices.length === 0) break;
        currentIdx = nextLayerIndices[Math.floor(Math.random() * nextLayerIndices.length)];
      } else {
        currentIdx = nextOptions[Math.floor(Math.random() * nextOptions.length)];
      }
      path.push(currentIdx);
    }

    return path;
  }
}
