"""
Украдені скарби — Full 3D Hex Pillar Map (Three.js WebGL)

Real 3D with:
  - Extruded hex pillars with lighting & shadows
  - Green bottom = Hermitage, Blue top = SHM
  - Orbit controls (rotate, zoom, pan)
  - Animated intro camera fly-in
  - Ground plane with Ukraine boundary
  - Hover tooltips with raycasting
  - Fog, ambient occlusion, grid

Usage:
    python hex_map_3d_pro.py
    python hex_map_3d_pro.py combined_database_updated.csv
"""

import csv
import math
import json
import sys
from pathlib import Path


UKRAINE_BOUNDARY = [
    [22.15,48.40],[22.13,48.58],[22.56,49.08],[22.18,49.27],[22.47,49.47],
    [22.73,49.65],[23.17,50.10],[23.35,50.22],[23.50,50.40],[23.92,50.41],
    [24.03,50.61],[23.53,51.58],
    [24.01,51.62],[24.33,51.83],[25.07,51.59],[25.50,51.91],
    [26.10,51.85],[26.46,51.93],[27.14,51.75],[27.84,51.59],[28.60,51.43],
    [28.99,51.60],[29.25,51.37],[30.16,51.42],[30.56,51.32],[30.93,51.47],
    [31.22,51.75],[31.54,51.51],[31.79,52.10],[32.16,52.05],[32.41,52.29],
    [33.20,52.35],[33.75,52.34],[34.10,51.98],[34.39,51.77],[35.02,51.69],
    [35.38,51.04],[35.55,50.37],[36.12,50.37],[36.63,50.23],[37.42,50.41],
    [38.01,49.92],[38.59,49.93],[38.82,49.57],[39.29,49.06],[39.79,49.57],
    [40.08,49.31],[39.69,48.78],[39.96,48.29],[39.79,47.84],[39.17,47.45],
    [38.26,47.10],[37.80,46.62],[37.25,46.38],[36.74,46.39],[36.51,46.66],
    [35.83,46.62],[35.19,46.33],[35.40,46.10],
    [36.45,45.30],[36.20,45.35],[35.88,45.10],[35.50,45.40],
    [35.80,44.85],[35.47,44.60],
    [34.80,44.40],[34.20,44.45],[33.91,44.39],[33.70,44.40],
    [33.50,44.50],[33.35,44.51],[33.00,44.42],[32.50,44.45],
    [32.10,44.60],[31.80,44.70],[31.60,45.05],[31.90,45.30],
    [32.50,45.35],[33.00,45.50],[33.35,45.15],[33.55,45.10],
    [33.50,45.35],[33.35,45.55],[33.00,45.70],
    [32.60,45.80],[32.10,46.00],[31.50,46.10],[31.60,46.30],
    [31.90,46.40],[31.50,46.55],[31.10,46.50],
    [30.95,46.40],[30.50,46.10],[30.20,45.80],
    [30.02,45.32],[29.60,45.40],[29.15,45.46],[28.73,45.23],
    [28.24,45.47],[28.49,45.60],[28.95,46.05],[29.01,46.17],
    [28.83,46.43],[29.57,46.40],[29.90,46.72],[29.59,46.93],
    [29.56,47.37],[29.16,47.49],[29.21,47.74],[28.89,47.96],
    [28.53,48.10],[27.73,48.45],[26.64,48.26],[25.94,48.19],
    [25.21,47.89],[24.87,47.74],[24.45,47.96],[23.87,47.99],
    [24.01,48.22],[23.55,48.38],[23.41,48.18],[22.88,48.38],
    [22.15,48.40]
]


def read_artifacts(filepath):
    artifacts = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                raw_lat = float(row.get('lat', ''))
                raw_lng = float(row.get('lon', '') or row.get('lng', ''))
                museum = row.get('museum', '').strip().lower()
                if 22 < raw_lat < 41 and 44 < raw_lng < 53:
                    lat, lng = raw_lng, raw_lat
                else:
                    lat, lng = raw_lat, raw_lng
                if 22 < lng < 41 and 44 < lat < 53:
                    artifacts.append({'lng': lng, 'lat': lat, 'museum': museum})
            except (ValueError, TypeError):
                continue
    print(f"Loaded {len(artifacts)} artifacts")
    return artifacts


def point_in_polygon(x, y, polygon):
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def generate_hex_data(artifacts, hex_size=0.4):
    w = hex_size * 1.5
    h = hex_size * math.sqrt(3)
    hex_counts = {}

    def nearest_hex_center(lng, lat):
        """Find the nearest hex center using candidate testing."""
        # Get approximate column
        col_approx = lng / w
        row_approx = lat / h

        best_dist = float('inf')
        best_key = None
        best_cx = None
        best_cy = None

        # Test nearby candidate hex centers
        for dc in range(-1, 2):
            c = round(col_approx) + dc
            for dr in range(-1, 2):
                if c % 2:
                    # Odd columns are offset by half a row
                    r = round(row_approx - 0.5) + 0.5 + dr
                else:
                    r = round(row_approx) + dr

                cx = c * w
                cy = r * h
                dist = (lng - cx) ** 2 + (lat - cy) ** 2

                if dist < best_dist:
                    best_dist = dist
                    best_key = f"{c},{r}"
                    best_cx = cx
                    best_cy = cy

        return best_key, best_cx, best_cy

    for art in artifacts:
        lng, lat = art['lng'], art['lat']
        museum = art['museum']

        key, cx, cy = nearest_hex_center(lng, lat)

        if key not in hex_counts:
            hex_counts[key] = {'cx': cx, 'cy': cy, 'hermitage': 0, 'shm': 0, 'total': 0}
        if museum == 'shm':
            hex_counts[key]['shm'] += 1
        else:
            hex_counts[key]['hermitage'] += 1
        hex_counts[key]['total'] += 1

    result = list(hex_counts.values())

    # Add empty hexes within boundary
    existing = set((round(d['cx'], 2), round(d['cy'], 2)) for d in result)
    col_v = 22.0
    col_idx = 0
    while col_v <= 40.5:
        row_v = 44.0 + (h * 0.5 if col_idx % 2 else 0)
        while row_v <= 52.8:
            key = (round(col_v, 2), round(row_v, 2))
            if key not in existing and point_in_polygon(col_v, row_v, UKRAINE_BOUNDARY):
                result.append({'cx': col_v, 'cy': row_v, 'hermitage': 0, 'shm': 0, 'total': 0})
            row_v += h
        col_v += w
        col_idx += 1

    total_in = sum(d['total'] for d in result)
    print(f"Generated {len(result)} hexagons ({sum(1 for r in result if r['total'] > 0)} with artifacts)")
    print(f"Artifacts in hexes: {total_in:,}")

    # Show top hexes
    top = sorted(result, key=lambda x: x['total'], reverse=True)[:5]
    print(f"\nTop 5 hexes:")
    for i, t in enumerate(top):
        print(f"  {i+1}. {t['total']:,} artifacts (H:{t['hermitage']:,} S:{t['shm']:,}) at ({t['cx']:.2f}, {t['cy']:.2f})")
    return result


def generate_html(hex_data, hex_size=0.4):
    max_total = max(h['total'] for h in hex_data) if hex_data else 1
    total_all = sum(h['total'] for h in hex_data)
    total_herm = sum(h['hermitage'] for h in hex_data)
    total_shm = sum(h['shm'] for h in hex_data)

    hex_json = json.dumps(hex_data)
    boundary_json = json.dumps(UKRAINE_BOUNDARY)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Украдені скарби — 3D Hex Pillar Map</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #000;
    color: #e6edf3;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    overflow: hidden;
    height: 100vh;
  }}
  canvas {{ display: block; }}

  #overlay {{
    position: absolute;
    top: 0; left: 0; right: 0;
    pointer-events: none;
    z-index: 10;
  }}

  #header {{
    padding: 16px 24px;
    background: linear-gradient(180deg, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 100%);
    pointer-events: auto;
  }}
  #header h1 {{
    font-size: 26px;
    color: #ffd500;
    text-shadow: 0 2px 8px rgba(0,0,0,0.8);
    letter-spacing: 1px;
  }}
  #header h2 {{
    font-size: 14px;
    color: #8b949e;
    font-weight: 400;
    margin-top: 4px;
  }}

  #controls {{
    position: absolute;
    top: 80px;
    right: 20px;
    background: rgba(13, 17, 23, 0.9);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 16px;
    pointer-events: auto;
    backdrop-filter: blur(12px);
    width: 220px;
  }}
  .ctrl-title {{
    font-size: 11px;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 12px;
  }}
  .ctrl-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }}
  .ctrl-row label {{
    font-size: 12px;
    color: #c9d1d9;
    min-width: 60px;
  }}
  .ctrl-row input[type="range"] {{
    -webkit-appearance: none;
    appearance: none;
    flex: 1;
    height: 8px;
    background: #30363d;
    border-radius: 4px;
    margin: 0 8px;
    cursor: pointer;
  }}
  .ctrl-row input[type="range"]::-webkit-slider-thumb {{
    -webkit-appearance: none;
    width: 22px; height: 22px;
    border-radius: 50%;
    background: #ffd500;
    border: 2px solid #fff;
    box-shadow: 0 0 8px rgba(255,213,0,0.5);
    cursor: pointer;
  }}
  .ctrl-row input[type="range"]::-moz-range-thumb {{
    width: 22px; height: 22px;
    border-radius: 50%;
    background: #ffd500;
    border: 2px solid #fff;
    box-shadow: 0 0 8px rgba(255,213,0,0.5);
    cursor: pointer;
  }}
  .ctrl-val {{
    color: #ffd500;
    font-weight: 700;
    font-size: 13px;
    min-width: 32px;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }}

  .ctrl-btn {{
    width: 100%;
    padding: 8px;
    margin-top: 4px;
    border: 1px solid #30363d;
    border-radius: 8px;
    background: #161b22;
    color: #c9d1d9;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
    text-align: center;
  }}
  .ctrl-btn:hover {{ background: #21262d; color: #ffd500; border-color: #ffd500; }}

  #legend {{
    position: absolute;
    bottom: 20px;
    left: 20px;
    background: rgba(13, 17, 23, 0.9);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 16px;
    pointer-events: auto;
    backdrop-filter: blur(12px);
    font-size: 13px;
  }}
  .leg-title {{ font-weight: 600; margin-bottom: 10px; font-size: 14px; }}
  .leg-row {{ display: flex; align-items: center; gap: 8px; margin: 6px 0; }}
  .leg-swatch {{ width: 18px; height: 18px; border-radius: 4px; }}

  #stats {{
    position: absolute;
    bottom: 20px;
    right: 20px;
    background: rgba(13, 17, 23, 0.9);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 16px;
    pointer-events: auto;
    backdrop-filter: blur(12px);
    font-size: 13px;
    text-align: right;
  }}
  .stat-row {{ margin: 4px 0; }}
  .stat-val {{ font-weight: 700; font-variant-numeric: tabular-nums; }}
  .stat-gold {{ color: #ffd500; }}
  .stat-green {{ color: #4ade80; }}
  .stat-blue {{ color: #60a5fa; }}

  #tooltip {{
    position: fixed;
    background: rgba(13, 17, 23, 0.95);
    border: 1px solid #ffd500;
    border-radius: 10px;
    padding: 12px 16px;
    pointer-events: none;
    display: none;
    z-index: 100;
    box-shadow: 0 8px 32px rgba(0,0,0,0.6), 0 0 16px rgba(255,213,0,0.15);
    line-height: 1.7;
    font-size: 13px;
    min-width: 180px;
  }}
  .tt-total {{ font-size: 22px; font-weight: 800; color: #ffd500; }}
  .tt-bar {{ height: 6px; border-radius: 3px; margin: 8px 0; display: flex; overflow: hidden; }}
  .tt-bar-herm {{ background: #4ade80; }}
  .tt-bar-shm {{ background: #60a5fa; }}
  .tt-label {{ color: #8b949e; }}

  #loading {{
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    z-index: 50;
  }}
  #loading h2 {{ color: #ffd500; font-size: 24px; margin-bottom: 10px; }}
  #loading p {{ color: #8b949e; }}
  .spinner {{
    width: 40px; height: 40px;
    border: 4px solid #30363d;
    border-top: 4px solid #ffd500;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 16px auto;
  }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
</style>
</head>
<body>

<div id="loading">
  <h2>Украдені скарби</h2>
  <div class="spinner"></div>
  <p>Building 3D scene...</p>
</div>

<div id="overlay">
  <div id="header">
    <h1>Украдені скарби — Stolen Treasures</h1>
    <h2>3D visualization of {total_all:,} Ukrainian artifacts in Russian museums</h2>
  </div>

  <div id="controls">
    <div class="ctrl-title">View Controls</div>
    <div class="ctrl-row">
      <label>Height</label>
      <input type="range" id="heightSlider" min="0.2" max="5" value="1" step="0.1">
      <span class="ctrl-val" id="heightVal">1.0</span>
    </div>
    <div class="ctrl-row">
      <label>Spacing</label>
      <input type="range" id="gapSlider" min="0.5" max="1.0" value="0.88" step="0.02">
      <span class="ctrl-val" id="gapVal">0.88</span>
    </div>
    <div class="ctrl-row">
      <label>Fog</label>
      <input type="range" id="fogSlider" min="20" max="100" value="50" step="1">
      <span class="ctrl-val" id="fogVal">50</span>
    </div>
    <button class="ctrl-btn" id="btnTop">Top View</button>
    <button class="ctrl-btn" id="btnAngle">Angle View</button>
    <button class="ctrl-btn" id="btnSide">Side View</button>
    <button class="ctrl-btn" id="btnSpin">Auto Spin</button>
  </div>

  <div id="legend">
    <div class="leg-title">Museum</div>
    <div class="leg-row"><div class="leg-swatch" style="background:#4ade80"></div> Hermitage (bottom)</div>
    <div class="leg-row"><div class="leg-swatch" style="background:#60a5fa"></div> State Historical Museum (top)</div>
    <div class="leg-row" style="margin-top:10px"><div class="leg-swatch" style="background:#1a2332;border:1px solid #333"></div> No artifacts</div>
  </div>

  <div id="stats">
    <div class="stat-row">Total: <span class="stat-val stat-gold">{total_all:,}</span></div>
    <div class="stat-row">Hermitage: <span class="stat-val stat-green">{total_herm:,}</span></div>
    <div class="stat-row">SHM: <span class="stat-val stat-blue">{total_shm:,}</span></div>
    <div class="stat-row">Max/hex: <span class="stat-val stat-gold">{max_total:,}</span></div>
  </div>
</div>

<div id="tooltip"></div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
// === DATA ===
const hexData = {hex_json};
const boundary = {boundary_json};
const HEX_SIZE = {hex_size};
const MAX_TOTAL = {max_total};

// === COORDINATE TRANSFORM ===
const CENTER_LNG = 31.2;
const CENTER_LAT = 48.4;
const SCALE = 3.0;

function geoTo3D(lng, lat) {{
  return [
    (lng - CENTER_LNG) * SCALE,
    (lat - CENTER_LAT) * SCALE
  ];
}}

// === THREE.JS SETUP ===
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0a0e17);
scene.fog = new THREE.FogExp2(0x0a0e17, 0.025);

const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 200);
camera.position.set(0, 30, 25);
camera.lookAt(0, 0, 0);

const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: false }});
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.2;
document.body.insertBefore(renderer.domElement, document.getElementById('overlay'));

// === LIGHTS ===
const ambient = new THREE.AmbientLight(0x334466, 0.6);
scene.add(ambient);

const hemiLight = new THREE.HemisphereLight(0x8899bb, 0x223344, 0.4);
scene.add(hemiLight);

const dirLight = new THREE.DirectionalLight(0xffeedd, 1.2);
dirLight.position.set(15, 30, 10);
dirLight.castShadow = true;
dirLight.shadow.mapSize.width = 2048;
dirLight.shadow.mapSize.height = 2048;
dirLight.shadow.camera.near = 0.5;
dirLight.shadow.camera.far = 80;
dirLight.shadow.camera.left = -30;
dirLight.shadow.camera.right = 30;
dirLight.shadow.camera.top = 30;
dirLight.shadow.camera.bottom = -30;
scene.add(dirLight);

const rimLight = new THREE.DirectionalLight(0x4488ff, 0.3);
rimLight.position.set(-10, 15, -10);
scene.add(rimLight);

// === GROUND PLANE ===
const groundGeo = new THREE.PlaneGeometry(80, 80);
const groundMat = new THREE.MeshStandardMaterial({{
  color: 0x0d1220,
  roughness: 0.9,
  metalness: 0.1,
}});
const ground = new THREE.Mesh(groundGeo, groundMat);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.05;
ground.receiveShadow = true;
scene.add(ground);

// === GRID HELPER ===
const grid = new THREE.GridHelper(60, 60, 0x1a2233, 0x111822);
grid.position.y = -0.04;
scene.add(grid);

// === UKRAINE BOUNDARY LINE ===
const boundaryPts = boundary.map(p => {{
  const [x, z] = geoTo3D(p[0], p[1]);
  return new THREE.Vector3(x, 0.02, -z);
}});
const boundaryGeo = new THREE.BufferGeometry().setFromPoints(boundaryPts);
const boundaryLine = new THREE.Line(boundaryGeo, new THREE.LineBasicMaterial({{
  color: 0xffd500, linewidth: 2, transparent: true, opacity: 0.6
}}));
scene.add(boundaryLine);

// === MATERIALS ===
const hermMat = new THREE.MeshStandardMaterial({{
  color: 0x22c55e, roughness: 0.4, metalness: 0.3,
}});
const shmMat = new THREE.MeshStandardMaterial({{
  color: 0x3b82f6, roughness: 0.4, metalness: 0.3,
}});
const emptyMat = new THREE.MeshStandardMaterial({{
  color: 0x1a2332, roughness: 0.8, metalness: 0.1,
  transparent: true, opacity: 0.4,
}});
const topHermMat = new THREE.MeshStandardMaterial({{
  color: 0x4ade80, roughness: 0.3, metalness: 0.4,
  emissive: 0x114422, emissiveIntensity: 0.15,
}});
const topShmMat = new THREE.MeshStandardMaterial({{
  color: 0x60a5fa, roughness: 0.3, metalness: 0.4,
  emissive: 0x112244, emissiveIntensity: 0.15,
}});

// === BUILD HEX GEOMETRY ===
function createHexShape(size) {{
  const shape = new THREE.Shape();
  for (let i = 0; i < 6; i++) {{
    const angle = (Math.PI / 3) * i - Math.PI / 6;
    const x = size * Math.cos(angle);
    const y = size * Math.sin(angle);
    if (i === 0) shape.moveTo(x, y);
    else shape.lineTo(x, y);
  }}
  shape.closePath();
  return shape;
}}

const hexShape = createHexShape(HEX_SIZE * SCALE * 0.88);

let heightMultiplier = 1.0;
let hexMeshes = [];
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

function getHeight(total) {{
  if (total === 0) return 0.06;
  // sqrt scale — proportional but tames extremes
  return Math.sqrt(total / MAX_TOTAL) * 12 * heightMultiplier;
}}

function buildPillars() {{
  // Remove old
  hexMeshes.forEach(m => {{
    if (m.group) scene.remove(m.group);
  }});
  hexMeshes = [];

  const gapVal = parseFloat(document.getElementById('gapSlider').value);
  const radius = HEX_SIZE * SCALE * gapVal;

  hexData.forEach(d => {{
    const [x, z] = geoTo3D(d.cx, d.cy);
    const group = new THREE.Group();
    group.position.set(x, 0, -z);
    const entry = {{ data: d, group: group }};

    if (d.total === 0) {{
      // Flat empty hex
      const geo = new THREE.CylinderGeometry(radius, radius, 0.06, 6);
      const mesh = new THREE.Mesh(geo, emptyMat);
      mesh.position.y = 0.03;
      mesh.userData = d;
      group.add(mesh);
    }} else {{
      const totalH = getHeight(d.total);
      const hermH = d.total > 0 ? (d.hermitage / d.total) * totalH : 0;
      const shmH = totalH - hermH;

      // Hermitage (green, bottom section)
      if (hermH > 0.01) {{
        const geo = new THREE.CylinderGeometry(radius, radius, hermH, 6);
        const mesh = new THREE.Mesh(geo, hermMat);
        mesh.position.y = hermH / 2;  // CylinderGeometry is centered
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        mesh.userData = d;
        group.add(mesh);

        // Bright cap at Hermitage/SHM boundary
        if (shmH > 0.01) {{
          const capGeo = new THREE.CylinderGeometry(radius * 1.01, radius * 1.01, 0.04, 6);
          const capMesh = new THREE.Mesh(capGeo, topHermMat);
          capMesh.position.y = hermH;
          capMesh.userData = d;
          group.add(capMesh);
        }}
      }}

      // SHM (blue, top section)
      if (shmH > 0.01) {{
        const geo = new THREE.CylinderGeometry(radius, radius, shmH, 6);
        const mesh = new THREE.Mesh(geo, shmMat);
        mesh.position.y = hermH + shmH / 2;  // sits on top of Hermitage
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        mesh.userData = d;
        group.add(mesh);
      }}

      // Top cap (glowing)
      const topCapGeo = new THREE.CylinderGeometry(radius * 1.01, radius * 1.01, 0.04, 6);
      const topCapMat = d.shm > d.hermitage ? topShmMat : topHermMat;
      const topCap = new THREE.Mesh(topCapGeo, topCapMat);
      topCap.position.y = totalH;
      topCap.userData = d;
      group.add(topCap);
    }}

    scene.add(group);
    hexMeshes.push(entry);
  }});
}}

buildPillars();

// === ORBIT CONTROLS (manual) ===
let orbitAngle = 0.8;
let orbitPitch = 0.7;
let orbitDist = 35;
let targetX = 0, targetZ = 0;
let isDragging = false;
let lastMouse = {{ x: 0, y: 0 }};
let autoSpin = false;

function updateCamera() {{
  const x = targetX + orbitDist * Math.sin(orbitAngle) * Math.cos(orbitPitch);
  const y = orbitDist * Math.sin(orbitPitch);
  const z = targetZ + orbitDist * Math.cos(orbitAngle) * Math.cos(orbitPitch);
  camera.position.set(x, Math.max(y, 1), z);
  camera.lookAt(targetX, 2, targetZ);
}}

renderer.domElement.addEventListener('pointerdown', e => {{
  isDragging = true;
  lastMouse = {{ x: e.clientX, y: e.clientY }};
  autoSpin = false;
}});

renderer.domElement.addEventListener('pointermove', e => {{
  if (isDragging) {{
    const dx = e.clientX - lastMouse.x;
    const dy = e.clientY - lastMouse.y;
    orbitAngle -= dx * 0.005;
    orbitPitch = Math.max(0.05, Math.min(1.5, orbitPitch + dy * 0.005));
    lastMouse = {{ x: e.clientX, y: e.clientY }};
    updateCamera();
  }}

  // Raycasting for tooltip
  mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
  mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
}});

renderer.domElement.addEventListener('pointerup', () => {{ isDragging = false; }});

renderer.domElement.addEventListener('wheel', e => {{
  orbitDist = Math.max(8, Math.min(60, orbitDist + e.deltaY * 0.02));
  updateCamera();
}});

// Right-click pan
renderer.domElement.addEventListener('contextmenu', e => e.preventDefault());
let isPanning = false;
renderer.domElement.addEventListener('pointerdown', e => {{
  if (e.button === 2) {{ isPanning = true; lastMouse = {{ x: e.clientX, y: e.clientY }}; }}
}});
renderer.domElement.addEventListener('pointermove', e => {{
  if (isPanning) {{
    const dx = e.clientX - lastMouse.x;
    const dy = e.clientY - lastMouse.y;
    targetX -= dx * 0.03;
    targetZ -= dy * 0.03;
    lastMouse = {{ x: e.clientX, y: e.clientY }};
    updateCamera();
  }}
}});
renderer.domElement.addEventListener('pointerup', e => {{
  if (e.button === 2) isPanning = false;
}});

updateCamera();

// === TOOLTIP ===
let hoveredData = null;

function updateTooltip(e) {{
  raycaster.setFromCamera(mouse, camera);
  const allMeshes = [];
  hexMeshes.forEach(h => {{
    if (h.group) {{
      h.group.children.forEach(child => allMeshes.push(child));
    }}
  }});

  const intersects = raycaster.intersectObjects(allMeshes);
  const tt = document.getElementById('tooltip');

  if (intersects.length > 0) {{
    const d = intersects[0].object.userData;
    if (d && d.total !== undefined) {{
      const pctH = d.total > 0 ? ((d.hermitage / d.total) * 100).toFixed(0) : 0;
      const pctS = d.total > 0 ? ((d.shm / d.total) * 100).toFixed(0) : 0;
      const barW = 150;
      const hermW = d.total > 0 ? (d.hermitage / d.total) * barW : 0;

      tt.innerHTML = `
        <div class="tt-total">${{d.total.toLocaleString()}} artifacts</div>
        <div class="tt-bar">
          <div class="tt-bar-herm" style="width:${{hermW}}px"></div>
          <div class="tt-bar-shm" style="flex:1"></div>
        </div>
        <div><span style="color:#4ade80">■</span> Hermitage: ${{d.hermitage.toLocaleString()}} (${{pctH}}%)</div>
        <div><span style="color:#60a5fa">■</span> SHM: ${{d.shm.toLocaleString()}} (${{pctS}}%)</div>
      `;
      tt.style.display = 'block';
      tt.style.left = (e.clientX + 20) + 'px';
      tt.style.top = (e.clientY - 20) + 'px';
      return;
    }}
  }}
  tt.style.display = 'none';
}}

renderer.domElement.addEventListener('pointermove', updateTooltip);

// === CONTROLS ===
document.getElementById('heightSlider').addEventListener('input', function() {{
  heightMultiplier = parseFloat(this.value);
  document.getElementById('heightVal').textContent = this.value;
  hexMeshes.forEach(m => {{ if (m.group) scene.remove(m.group); }});
  buildPillars();
}});

document.getElementById('gapSlider').addEventListener('input', function() {{
  document.getElementById('gapVal').textContent = this.value;
  hexMeshes.forEach(m => {{ if (m.group) scene.remove(m.group); }});
  buildPillars();
}});

document.getElementById('fogSlider').addEventListener('input', function() {{
  const v = parseInt(this.value);
  document.getElementById('fogVal').textContent = v;
  scene.fog.density = (100 - v) * 0.001 + 0.005;
}});

document.getElementById('btnTop').addEventListener('click', () => {{
  orbitPitch = 1.45; orbitDist = 30; orbitAngle = 0; autoSpin = false;
  updateCamera();
}});
document.getElementById('btnAngle').addEventListener('click', () => {{
  orbitPitch = 0.7; orbitDist = 35; orbitAngle = 0.8; autoSpin = false;
  updateCamera();
}});
document.getElementById('btnSide').addEventListener('click', () => {{
  orbitPitch = 0.15; orbitDist = 40; orbitAngle = 0.5; autoSpin = false;
  updateCamera();
}});
document.getElementById('btnSpin').addEventListener('click', function() {{
  autoSpin = !autoSpin;
  this.textContent = autoSpin ? 'Stop Spin' : 'Auto Spin';
  this.style.borderColor = autoSpin ? '#ffd500' : '#30363d';
  this.style.color = autoSpin ? '#ffd500' : '#c9d1d9';
}});

// === ANIMATION LOOP ===
function animate() {{
  requestAnimationFrame(animate);

  if (autoSpin) {{
    orbitAngle += 0.003;
    updateCamera();
  }}

  renderer.render(scene, camera);
}}

// === INTRO ANIMATION ===
let introT = 0;
const introStart = {{ angle: 3.0, pitch: 0.2, dist: 55 }};
const introEnd = {{ angle: 0.8, pitch: 0.7, dist: 35 }};

function introAnimate() {{
  introT += 0.008;
  const t = Math.min(introT, 1);
  const ease = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

  orbitAngle = introStart.angle + (introEnd.angle - introStart.angle) * ease;
  orbitPitch = introStart.pitch + (introEnd.pitch - introStart.pitch) * ease;
  orbitDist = introStart.dist + (introEnd.dist - introStart.dist) * ease;
  updateCamera();
  renderer.render(scene, camera);

  if (t < 1) {{
    requestAnimationFrame(introAnimate);
  }} else {{
    document.getElementById('loading').style.display = 'none';
    animate();
  }}
}}

// === RESIZE ===
window.addEventListener('resize', () => {{
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}});

// === START ===
setTimeout(() => {{
  introAnimate();
}}, 100);

</script>
</body>
</html>"""

    return html


def main():
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    elif Path('combined_database_updated.csv').exists():
        input_file = 'combined_database_updated.csv'
    elif Path('combined_database.csv').exists():
        input_file = 'combined_database.csv'
    else:
        print("Error: No CSV file found.")
        sys.exit(1)

    print(f"Reading: {input_file}")
    artifacts = read_artifacts(input_file)
    if not artifacts:
        print("No artifacts found!")
        sys.exit(1)

    print("Generating hex grid...")
    hex_data = generate_hex_data(artifacts, hex_size=0.4)

    print("Building 3D visualization...")
    html = generate_html(hex_data, hex_size=0.4)

    output_file = 'ukraine_hex_3d.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\nSaved: {output_file}")
    print("Open in a browser to explore!")


if __name__ == '__main__':
    main()
