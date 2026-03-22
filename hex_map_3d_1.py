"""
Generate an interactive 3D hex pillar map using D3.js

Each hexagon is a 3D column:
  - Bottom (green): Hermitage artifacts
  - Top (blue): State Historical Museum artifacts
  - Height proportional to total count

Usage:
    python hex_map_3d.py
    python hex_map_3d.py combined_database_updated.csv

Output:
    ukraine_hex_3d.html
"""

import csv
import math
import json
import sys
from pathlib import Path


def read_artifacts(filepath):
    """Read artifact locations from CSV."""
    artifacts = []

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                raw_lat = float(row.get('lat', ''))
                raw_lng = float(row.get('lon', '') or row.get('lng', ''))
                museum = row.get('museum', '').strip().lower()

                # Auto-detect swap
                if 22 < raw_lat < 41 and 44 < raw_lng < 53:
                    lat, lng = raw_lng, raw_lat
                else:
                    lat, lng = raw_lat, raw_lng

                if 22 < lng < 41 and 44 < lat < 53:
                    artifacts.append({
                        'lng': lng,
                        'lat': lat,
                        'museum': museum
                    })
            except (ValueError, TypeError):
                continue

    print(f"Loaded {len(artifacts)} artifacts")
    return artifacts


# Simplified Ukraine boundary
UKRAINE_BOUNDARY = [
    [22.15,48.40],[22.71,48.90],[22.56,49.08],[22.18,49.27],[22.47,49.47],
    [22.73,49.65],[23.35,50.22],[23.50,50.40],[23.92,50.41],[24.03,50.61],
    [23.53,51.58],[24.01,51.62],[24.33,51.83],[25.07,51.59],[25.50,51.91],
    [26.10,51.85],[26.46,51.93],[27.14,51.75],[27.84,51.59],[28.60,51.43],
    [28.99,51.60],[29.25,51.37],[30.16,51.42],[30.56,51.32],[30.93,51.47],
    [31.22,51.75],[31.54,51.51],[31.79,52.10],[32.16,52.05],[32.41,52.29],
    [33.20,52.35],[33.75,52.34],[34.10,51.98],[34.39,51.77],[35.02,51.69],
    [35.38,51.04],[35.55,50.37],[36.12,50.37],[36.63,50.23],[37.42,50.41],
    [38.01,49.92],[38.59,49.93],[38.82,49.57],[39.29,49.06],[39.79,49.57],
    [40.08,49.31],[39.69,48.78],[39.96,48.29],[39.79,47.84],[39.17,47.45],
    [38.26,47.10],[37.80,46.62],[37.25,46.38],[36.74,46.39],[36.51,46.66],
    [35.83,46.62],[35.19,46.33],[35.06,45.65],[35.50,45.46],[35.88,45.07],
    [35.47,44.60],[34.41,44.52],[33.91,44.39],[33.45,44.55],[33.55,45.10],
    [33.24,44.70],[32.51,44.48],[31.75,44.35],[30.95,44.60],[30.02,45.32],
    [29.60,45.40],[29.15,45.46],[28.73,45.23],[28.24,45.47],[28.49,45.60],
    [28.95,46.05],[29.01,46.17],[28.83,46.43],[29.57,46.40],[29.90,46.72],
    [29.59,46.93],[29.56,47.37],[29.16,47.49],[29.21,47.74],[28.89,47.96],
    [28.53,48.10],[27.73,48.45],[26.64,48.26],[25.94,48.19],[25.21,47.89],
    [24.87,47.74],[24.45,47.96],[23.87,47.99],[24.01,48.22],[23.55,48.38],
    [23.41,48.18],[22.88,48.38],[22.15,48.40]
]


def point_in_polygon(x, y, polygon):
    """Ray casting algorithm."""
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
    """Generate hex grid and count artifacts."""
    w = hex_size * 1.5
    h = hex_size * math.sqrt(3)

    # Assign artifacts to hex cells
    hex_counts = {}

    for art in artifacts:
        lng, lat = art['lng'], art['lat']
        museum = art['museum']

        # Hex grid coordinates
        col = lng / w
        row = lat / h

        col_round = round(col)
        row_round = round(row)

        # Offset for odd columns
        if col_round % 2:
            row_round = round(row - 0.5) + 0.5

        cx = col_round * w
        cy = row_round * h

        key = f"{col_round},{row_round}"

        if key not in hex_counts:
            hex_counts[key] = {
                'cx': cx, 'cy': cy,
                'hermitage': 0, 'shm': 0, 'total': 0
            }

        if museum == 'shm':
            hex_counts[key]['shm'] += 1
        else:
            hex_counts[key]['hermitage'] += 1
        hex_counts[key]['total'] += 1

    # Filter to hexes within Ukraine
    result = []
    for key, data in hex_counts.items():
        if point_in_polygon(data['cx'], data['cy'], UKRAINE_BOUNDARY):
            result.append(data)

    # Also add empty hexes for the full grid
    min_lng, max_lng = 22.0, 40.5
    min_lat, max_lat = 44.0, 52.5

    existing = set((round(d['cx'], 2), round(d['cy'], 2)) for d in result)

    col = min_lng
    col_idx = 0
    while col <= max_lng:
        row = min_lat + (h * 0.5 if col_idx % 2 else 0)
        while row <= max_lat:
            key = (round(col, 2), round(row, 2))
            if key not in existing and point_in_polygon(col, row, UKRAINE_BOUNDARY):
                result.append({
                    'cx': col, 'cy': row,
                    'hermitage': 0, 'shm': 0, 'total': 0
                })
            row += h
        col += w
        col_idx += 1

    print(f"Generated {len(result)} hexagons ({sum(1 for r in result if r['total'] > 0)} with artifacts)")
    return result


def generate_html(hex_data, hex_size=0.4):
    """Generate the interactive 3D D3.js visualization."""

    max_total = max(h['total'] for h in hex_data) if hex_data else 1
    hex_json = json.dumps(hex_data)
    boundary_json = json.dumps(UKRAINE_BOUNDARY)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Украдені скарби — 3D Hex Pillar Map</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #0d1117;
    color: #e6edf3;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    overflow: hidden;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }}

  header {{
    padding: 16px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(13, 17, 23, 0.95);
    border-bottom: 1px solid #21262d;
    z-index: 10;
  }}

  .title-block h1 {{
    font-size: 22px;
    color: #ffd500;
    letter-spacing: 0.5px;
  }}
  .title-block h2 {{
    font-size: 13px;
    color: #8b949e;
    font-weight: 400;
    margin-top: 2px;
  }}

  .controls {{
    display: flex;
    gap: 8px;
    align-items: center;
    font-size: 13px;
  }}

  .control-group {{
    display: flex;
    align-items: center;
    gap: 8px;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 8px 14px;
  }}
  .control-group label {{
    color: #c9d1d9;
    font-size: 12px;
    font-weight: 600;
    min-width: 52px;
  }}

  .control-group input[type="range"] {{
    -webkit-appearance: none;
    appearance: none;
    width: 140px;
    height: 10px;
    background: linear-gradient(to right, #30363d, #58606b);
    border-radius: 5px;
    outline: none;
    cursor: pointer;
  }}
  .control-group input[type="range"]::-webkit-slider-thumb {{
    -webkit-appearance: none;
    appearance: none;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: #ffd500;
    cursor: pointer;
    border: 3px solid #fff;
    box-shadow: 0 0 10px rgba(255, 213, 0, 0.6), 0 2px 6px rgba(0,0,0,0.5);
  }}
  .control-group input[type="range"]::-moz-range-thumb {{
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: #ffd500;
    cursor: pointer;
    border: 3px solid #fff;
    box-shadow: 0 0 10px rgba(255, 213, 0, 0.6), 0 2px 6px rgba(0,0,0,0.5);
  }}
  .control-group input[type="range"]::-moz-range-track {{
    height: 10px;
    background: linear-gradient(to right, #30363d, #58606b);
    border-radius: 5px;
  }}

  .control-val {{
    color: #ffd500;
    font-weight: 700;
    font-size: 15px;
    min-width: 36px;
    text-align: center;
    font-variant-numeric: tabular-nums;
  }}

  #map-container {{
    flex: 1;
    position: relative;
    cursor: grab;
  }}
  #map-container:active {{ cursor: grabbing; }}

  svg {{
    width: 100%;
    height: 100%;
  }}

  .legend {{
    position: absolute;
    bottom: 20px;
    left: 20px;
    background: rgba(22, 27, 34, 0.92);
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 14px 18px;
    font-size: 13px;
    z-index: 10;
  }}
  .legend-title {{
    font-weight: 600;
    margin-bottom: 8px;
    color: #e6edf3;
  }}
  .legend-item {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 5px 0;
  }}
  .legend-swatch {{
    width: 16px;
    height: 16px;
    border-radius: 3px;
  }}

  .stats {{
    position: absolute;
    bottom: 20px;
    right: 20px;
    background: rgba(22, 27, 34, 0.92);
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 14px 18px;
    font-size: 13px;
    z-index: 10;
  }}
  .stats div {{ margin: 3px 0; }}
  .stats .val {{ color: #ffd500; font-weight: 600; }}

  #tooltip {{
    position: fixed;
    background: rgba(22, 27, 34, 0.96);
    border: 1px solid #444c56;
    color: #e6edf3;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 13px;
    pointer-events: none;
    display: none;
    z-index: 100;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    line-height: 1.6;
  }}
  #tooltip .tt-total {{ font-size: 18px; font-weight: 700; color: #ffd500; }}
  #tooltip .tt-herm {{ color: #4ade80; }}
  #tooltip .tt-shm {{ color: #60a5fa; }}
</style>
</head>
<body>

<header>
  <div class="title-block">
    <h1>Украдені скарби — 3D Hex Map</h1>
    <h2>Ukrainian artifacts in Russian museums · Hermitage & State Historical Museum</h2>
  </div>
  <div class="controls">
    <div class="control-group">
      <label>Tilt</label>
      <input type="range" id="tiltSlider" min="0" max="70" value="45">
      <span class="control-val" id="tiltVal">45°</span>
    </div>

    <div class="control-group">
      <label>Rotation</label>
      <input type="range" id="rotSlider" min="-30" max="30" value="0">
      <span class="control-val" id="rotVal">0°</span>
    </div>

    <div class="control-group">
      <label>Height</label>
      <input type="range" id="heightSlider" min="20" max="300" value="120">
      <span class="control-val" id="heightVal">120</span>
    </div>
  </div>
</header>

<div id="map-container">
  <svg id="map"></svg>
</div>

<div class="legend">
  <div class="legend-title">Museum</div>
  <div class="legend-item">
    <div class="legend-swatch" style="background:#4ade80"></div>
    Hermitage (bottom)
  </div>
  <div class="legend-item">
    <div class="legend-swatch" style="background:#60a5fa"></div>
    State Historical Museum (top)
  </div>
  <div class="legend-item" style="margin-top: 10px;">
    <div class="legend-swatch" style="background:#21262d; border:1px solid #444"></div>
    No artifacts
  </div>
</div>

<div class="stats">
  <div>Total artifacts: <span class="val" id="statTotal"></span></div>
  <div>Hermitage: <span class="val" style="color:#4ade80" id="statHerm"></span></div>
  <div>SHM: <span class="val" style="color:#60a5fa" id="statShm"></span></div>
  <div>Max per hex: <span class="val" id="statMax"></span></div>
</div>

<div id="tooltip"></div>

<script>
const hexData = {hex_json};
const boundary = {boundary_json};
const hexSize = {hex_size};
const maxTotal = {max_total};

// Stats
const totalAll = hexData.reduce((s, d) => s + d.total, 0);
const totalHerm = hexData.reduce((s, d) => s + d.hermitage, 0);
const totalShm = hexData.reduce((s, d) => s + d.shm, 0);
document.getElementById('statTotal').textContent = totalAll.toLocaleString();
document.getElementById('statHerm').textContent = totalHerm.toLocaleString();
document.getElementById('statShm').textContent = totalShm.toLocaleString();
document.getElementById('statMax').textContent = maxTotal.toLocaleString();

const container = document.getElementById('map-container');
const svg = d3.select('#map');
const g = svg.append('g');

// Hex vertices (flat-top)
function hexVertices(cx, cy, size) {{
  const verts = [];
  for (let i = 0; i < 6; i++) {{
    const angle = Math.PI / 180 * (60 * i + 30);
    verts.push([
      cx + size * Math.cos(angle),
      cy + size * Math.sin(angle)
    ]);
  }}
  return verts;
}}

// 3D projection
let tiltDeg = 45, rotDeg = 0, heightScale = 120;

function project(lng, lat, z = 0) {{
  // Normalize to screen coords
  const x0 = (lng - 22) / (40.5 - 22) * 900 + 100;
  const y0 = (52.5 - lat) / (52.5 - 44) * 650 + 50;

  const rotRad = rotDeg * Math.PI / 180;
  const tiltRad = tiltDeg * Math.PI / 180;

  // Rotate around center
  const centerX = 550, centerY = 400;
  const dx = x0 - centerX;
  const dy = y0 - centerY;
  const rx = dx * Math.cos(rotRad) - dy * Math.sin(rotRad) + centerX;
  const ry = dx * Math.sin(rotRad) + dy * Math.cos(rotRad) + centerY;

  // Apply tilt (compress Y and shift by Z)
  const finalX = rx;
  const finalY = ry * Math.cos(tiltRad) - z * Math.sin(tiltRad) * 0.8;

  return [finalX, finalY];
}}

function depthSort(a, b) {{
  // Sort back-to-front for proper occlusion
  const rotRad = rotDeg * Math.PI / 180;
  const depthA = -a.cy * Math.cos(rotRad) + a.cx * Math.sin(rotRad);
  const depthB = -b.cy * Math.cos(rotRad) + b.cx * Math.sin(rotRad);
  return depthA - depthB;
}}

function getHeight(d) {{
  if (d.total === 0) return 2;
  return (Math.log(d.total + 1) / Math.log(maxTotal + 1)) * heightScale;
}}

function render() {{
  g.selectAll('*').remove();

  // Draw boundary
  const boundaryPath = boundary.map((p, i) => {{
    const [sx, sy] = project(p[0], p[1], 0);
    return (i === 0 ? 'M' : 'L') + sx.toFixed(1) + ',' + sy.toFixed(1);
  }}).join(' ') + 'Z';

  g.append('path')
    .attr('d', boundaryPath)
    .attr('fill', 'rgba(30, 40, 55, 0.3)')
    .attr('stroke', '#444c56')
    .attr('stroke-width', 1.5);

  // Sort hexes for depth
  const sorted = [...hexData].sort(depthSort);

  sorted.forEach(d => {{
    const h = getHeight(d);
    const hermH = d.total > 0 ? (d.hermitage / d.total) * h : 0;
    const shmH = h - hermH;
    const verts = hexVertices(d.cx, d.cy, hexSize * 0.92);

    // Project top and bottom vertices
    const botVerts = verts.map(v => project(v[0], v[1], 0));
    const hermTopVerts = verts.map(v => project(v[0], v[1], hermH));
    const topVerts = verts.map(v => project(v[0], v[1], h));

    const hexGroup = g.append('g')
      .attr('class', 'hex-pillar')
      .attr('data-total', d.total)
      .attr('data-hermitage', d.hermitage)
      .attr('data-shm', d.shm);

    if (d.total === 0) {{
      // Empty hex — just draw flat
      const pts = botVerts.map(v => v.join(',')).join(' ');
      hexGroup.append('polygon')
        .attr('points', pts)
        .attr('fill', '#161b22')
        .attr('stroke', '#21262d')
        .attr('stroke-width', 0.5)
        .attr('opacity', 0.5);
      return;
    }}

    // --- Draw 3D pillar ---

    // Side faces (Hermitage - bottom section)
    for (let i = 0; i < 6; i++) {{
      const j = (i + 1) % 6;
      // Only draw faces that face "forward" (toward viewer)
      const midY = (botVerts[i][1] + botVerts[j][1]) / 2;
      const midTopY = (hermTopVerts[i][1] + hermTopVerts[j][1]) / 2;

      const facePts = [
        botVerts[i], botVerts[j],
        hermTopVerts[j], hermTopVerts[i]
      ].map(v => v.join(',')).join(' ');

      const shade = 0.6 + 0.4 * (i / 6);
      hexGroup.append('polygon')
        .attr('points', facePts)
        .attr('fill', d3.color('#4ade80').darker(1.2 - shade * 0.8))
        .attr('stroke', '#2d5a3e')
        .attr('stroke-width', 0.3);
    }}

    // Side faces (SHM - top section)
    if (shmH > 0.5) {{
      for (let i = 0; i < 6; i++) {{
        const j = (i + 1) % 6;
        const facePts = [
          hermTopVerts[i], hermTopVerts[j],
          topVerts[j], topVerts[i]
        ].map(v => v.join(',')).join(' ');

        const shade = 0.6 + 0.4 * (i / 6);
        hexGroup.append('polygon')
          .attr('points', facePts)
          .attr('fill', d3.color('#60a5fa').darker(1.2 - shade * 0.8))
          .attr('stroke', '#2d4a6e')
          .attr('stroke-width', 0.3);
      }}
    }}

    // Top face
    const topPts = topVerts.map(v => v.join(',')).join(' ');
    const topColor = d.shm > 0 ? '#93c5fd' : '#86efac';
    hexGroup.append('polygon')
      .attr('points', topPts)
      .attr('fill', topColor)
      .attr('stroke', d.shm > 0 ? '#3b82f6' : '#22c55e')
      .attr('stroke-width', 0.5);

    // Hermitage/SHM divider line on top face if both present
    if (hermH > 0 && shmH > 0.5) {{
      const divPts = hermTopVerts.map(v => v.join(',')).join(' ');
      hexGroup.append('polygon')
        .attr('points', divPts)
        .attr('fill', 'none')
        .attr('stroke', '#ffd500')
        .attr('stroke-width', 0.8)
        .attr('stroke-dasharray', '3,2')
        .attr('opacity', 0.6);
    }}

    // Invisible hover target
    hexGroup.append('polygon')
      .attr('points', topPts)
      .attr('fill', 'transparent')
      .attr('stroke', 'none')
      .style('cursor', 'pointer')
      .on('mousemove', function(event) {{
        const tt = document.getElementById('tooltip');
        const pct_h = d.total > 0 ? ((d.hermitage / d.total) * 100).toFixed(0) : 0;
        const pct_s = d.total > 0 ? ((d.shm / d.total) * 100).toFixed(0) : 0;
        tt.innerHTML = `
          <div class="tt-total">${{d.total.toLocaleString()}} artifacts</div>
          <div class="tt-herm">Hermitage: ${{d.hermitage.toLocaleString()}} (${{pct_h}}%)</div>
          <div class="tt-shm">SHM: ${{d.shm.toLocaleString()}} (${{pct_s}}%)</div>
        `;
        tt.style.display = 'block';
        tt.style.left = (event.clientX + 16) + 'px';
        tt.style.top = (event.clientY - 16) + 'px';
      }})
      .on('mouseleave', function() {{
        document.getElementById('tooltip').style.display = 'none';
      }});
  }});
}}

// Zoom
const zoom = d3.zoom()
  .scaleExtent([0.5, 5])
  .on('zoom', (event) => {{
    g.attr('transform', event.transform);
  }});

svg.call(zoom);

// Controls
document.getElementById('tiltSlider').addEventListener('input', function() {{
  tiltDeg = +this.value;
  document.getElementById('tiltVal').textContent = tiltDeg + '°';
  render();
}});

document.getElementById('rotSlider').addEventListener('input', function() {{
  rotDeg = +this.value;
  document.getElementById('rotVal').textContent = rotDeg + '°';
  render();
}});

document.getElementById('heightSlider').addEventListener('input', function() {{
  heightScale = +this.value;
  document.getElementById('heightVal').textContent = heightScale;
  render();
}});

// Initial render
render();
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
