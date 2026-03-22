"""
Kohonen-style hexagonal grid map of artifact density within Ukraine's borders.

Reads combined_database.csv (or combined_database_updated.csv) and generates
an interactive HTML hex map colored by artifact density.

Usage:
    python hex_map_ukraine.py
    python hex_map_ukraine.py combined_database_updated.csv

Output:
    ukraine_hex_map.html
    ukraine_hex_map.png
"""

import csv
import math
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.collections import PatchCollection
from matplotlib.colors import Normalize, LinearSegmentedColormap
from shapely.geometry import Point, Polygon, MultiPolygon, shape
import json

# ============================================================
# Simplified Ukraine boundary (main polygon)
# ============================================================
UKRAINE_BOUNDARY = [
    (22.15, 48.40), (22.71, 48.90), (23.14, 48.10), (24.00, 47.96),
    (24.87, 47.74), (25.21, 47.89), (25.95, 48.19), (26.62, 48.26),
    (27.55, 48.47), (28.21, 48.16), (28.67, 48.12), (29.19, 47.88),
    (29.55, 48.15), (29.95, 48.36), (30.26, 48.65), (30.75, 48.85),
    (31.51, 48.78), (32.18, 48.81), (33.21, 48.41), (33.78, 48.12),
    (34.40, 47.84), (35.02, 48.31), (35.41, 48.52), (36.12, 48.56),
    (36.63, 48.79), (37.43, 48.77), (38.21, 49.08), (38.77, 49.29),
    (39.29, 49.06), (39.79, 49.57), (40.08, 49.31), (39.69, 48.78),
    (39.96, 48.29), (39.79, 47.84), (39.17, 47.45), (38.26, 47.10),
    (38.08, 46.98), (37.80, 46.62), (37.25, 46.38), (36.74, 46.39),
    (36.51, 46.66), (35.83, 46.62), (35.19, 46.33), (35.06, 45.65),
    (35.50, 45.46), (35.88, 45.07), (35.47, 44.60), (34.41, 44.52),
    (33.91, 44.39), (33.45, 44.55), (33.55, 45.10), (33.24, 44.70),
    (32.51, 44.48), (31.75, 44.35), (30.95, 44.60), (30.02, 45.32),
    (29.60, 45.40), (29.15, 45.46), (28.73, 45.23), (28.24, 45.47),
    (28.49, 45.60), (28.95, 46.05), (29.01, 46.17), (28.83, 46.43),
    (29.57, 46.40), (29.91, 46.32), (29.84, 46.50), (30.13, 46.42),
    (29.90, 46.72), (29.59, 46.93), (29.56, 47.37), (29.16, 47.49),
    (29.21, 47.74), (28.89, 47.96), (28.53, 48.10), (27.73, 48.45),
    (26.64, 48.26), (25.94, 48.19), (25.21, 47.89), (24.87, 47.74),
    (24.45, 47.96), (23.87, 47.99), (24.01, 48.22), (23.55, 48.38),
    (23.41, 48.18), (22.88, 48.38), (22.56, 49.08), (22.76, 49.03),
    (22.56, 49.08), (22.18, 49.27), (22.47, 49.47), (22.73, 49.65),
    (23.35, 50.22), (23.50, 50.40), (23.92, 50.41), (24.03, 50.61),
    (23.53, 51.58), (24.01, 51.62), (24.33, 51.83), (25.07, 51.59),
    (25.50, 51.91), (26.10, 51.85), (26.46, 51.93), (27.14, 51.75),
    (27.84, 51.59), (28.60, 51.43), (28.99, 51.60), (29.25, 51.37),
    (30.16, 51.42), (30.56, 51.32), (30.93, 51.47), (31.22, 51.75),
    (31.54, 51.51), (31.79, 52.10), (32.16, 52.05), (32.41, 52.29),
    (33.20, 52.35), (33.75, 52.34), (34.10, 51.98), (34.24, 51.77),
    (34.39, 51.77), (35.02, 51.69), (35.38, 51.04), (35.55, 50.37),
    (36.12, 50.37), (36.63, 50.23), (37.42, 50.41), (38.01, 49.92),
    (38.59, 49.93), (38.82, 49.57), (39.29, 49.06), (38.77, 49.29),
    (38.21, 49.08), (37.43, 48.77), (36.63, 48.79), (36.12, 48.56),
    (35.41, 48.52), (35.02, 48.31), (34.40, 47.84), (33.78, 48.12),
    (33.21, 48.41), (32.18, 48.81), (31.51, 48.78), (30.75, 48.85),
    (30.26, 48.65), (29.95, 48.36), (29.55, 48.15), (29.19, 47.88),
    (28.67, 48.12), (28.21, 48.16), (27.55, 48.47), (26.62, 48.26),
    (25.95, 48.19), (25.21, 47.89), (24.87, 47.74), (24.00, 47.96),
    (23.14, 48.10), (22.71, 48.90), (22.15, 48.40),
]


def get_ukraine_polygon():
    """Return a simplified Shapely polygon of Ukraine."""
    try:
        return Polygon(UKRAINE_BOUNDARY).buffer(0)
    except:
        return Polygon(UKRAINE_BOUNDARY).convex_hull


def detect_columns(fieldnames):
    """Auto-detect latitude, longitude, and museum columns."""
    fn_lower = {f.lower().strip(): f for f in fieldnames}

    lat_candidates = ['lat', 'latitude', 'широта', 'y']
    lng_candidates = ['lng', 'lon', 'longitude', 'довгота', 'x']
    museum_candidates = ['museum', 'музей']
    id_candidates = ['id', '№', 'inv', 'inv_number']

    lat_col = lng_col = museum_col = id_col = None

    for c in lat_candidates:
        if c in fn_lower:
            lat_col = fn_lower[c]
            break

    for c in lng_candidates:
        if c in fn_lower:
            lng_col = fn_lower[c]
            break

    for c in museum_candidates:
        if c in fn_lower:
            museum_col = fn_lower[c]
            break

    for c in id_candidates:
        if c in fn_lower:
            id_col = fn_lower[c]
            break

    # Also check for compound names
    for f in fieldnames:
        fl = f.lower().strip()
        if lat_col is None and 'lat' in fl:
            lat_col = f
        if lng_col is None and ('lng' in fl or 'lon' in fl):
            lng_col = f

    return lat_col, lng_col, museum_col, id_col


def read_artifacts(filepath):
    """Read artifact locations from CSV."""
    artifacts = []
    hermitage = []
    shm = []

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        lat_col, lng_col, museum_col, id_col = detect_columns(reader.fieldnames)

        if not lat_col or not lng_col:
            print(f"Could not detect lat/lng columns!")
            print(f"Available columns: {reader.fieldnames}")
            sys.exit(1)

        print(f"Using columns: lat={lat_col}, lng={lng_col}, museum={museum_col}")

        for row in reader:
            try:
                raw_lat = float(row[lat_col])
                raw_lng = float(row[lng_col])

                # Auto-detect swap: if "lat" value looks like longitude, swap them
                if 22 < raw_lat < 41 and 44 < raw_lng < 53:
                    lat, lng = raw_lng, raw_lat  # CSV has them reversed
                else:
                    lat, lng = raw_lat, raw_lng

                museum = row.get(museum_col, '').strip().lower() if museum_col else ''

                if 22 < lng < 41 and 44 < lat < 53:  # rough Ukraine bbox
                    artifacts.append((lng, lat))
                    if museum == 'shm':
                        shm.append((lng, lat))
                    else:
                        hermitage.append((lng, lat))
            except (ValueError, TypeError):
                continue

    print(f"Loaded {len(artifacts)} artifacts ({len(hermitage)} Hermitage, {len(shm)} SHM)")
    return artifacts, hermitage, shm


def generate_hex_grid(polygon, hex_size=0.35):
    """Generate a hexagonal grid within a polygon."""
    bounds = polygon.bounds  # minx, miny, maxx, maxy
    minx, miny, maxx, maxy = bounds

    # Hex geometry
    w = hex_size * 2
    h = hex_size * math.sqrt(3)

    hexagons = []
    row = 0
    y = miny
    while y <= maxy + h:
        col = 0
        x = minx + (hex_size if row % 2 else 0)
        while x <= maxx + w:
            center = Point(x, y)
            if polygon.contains(center) or polygon.buffer(hex_size * 0.3).contains(center):
                hex_verts = []
                for angle_deg in range(0, 360, 60):
                    angle_rad = math.radians(angle_deg + 30)
                    vx = x + hex_size * math.cos(angle_rad)
                    vy = y + hex_size * math.sin(angle_rad)
                    hex_verts.append((vx, vy))
                hexagons.append({
                    'center': (x, y),
                    'vertices': hex_verts,
                    'count': 0,
                    'hermitage': 0,
                    'shm': 0,
                })
            x += w * 0.75 + hex_size * 0.5
            col += 1
        y += h
        row += 1

    return hexagons


def assign_artifacts_to_hexes(hexagons, artifacts, hermitage_set, shm_set, hex_size):
    """Count artifacts in each hexagon."""
    for art in artifacts:
        min_dist = float('inf')
        nearest = None
        for hexagon in hexagons:
            cx, cy = hexagon['center']
            dist = (art[0] - cx) ** 2 + (art[1] - cy) ** 2
            if dist < min_dist:
                min_dist = dist
                nearest = hexagon
        if nearest and min_dist < (hex_size * 1.5) ** 2:
            nearest['count'] += 1

    for art in hermitage_set:
        min_dist = float('inf')
        nearest = None
        for hexagon in hexagons:
            cx, cy = hexagon['center']
            dist = (art[0] - cx) ** 2 + (art[1] - cy) ** 2
            if dist < min_dist:
                min_dist = dist
                nearest = hexagon
        if nearest and min_dist < (hex_size * 1.5) ** 2:
            nearest['hermitage'] += 1

    for art in shm_set:
        min_dist = float('inf')
        nearest = None
        for hexagon in hexagons:
            cx, cy = hexagon['center']
            dist = (art[0] - cx) ** 2 + (art[1] - cy) ** 2
            if dist < min_dist:
                min_dist = dist
                nearest = hexagon
        if nearest and min_dist < (hex_size * 1.5) ** 2:
            nearest['shm'] += 1


def render_matplotlib(hexagons, polygon, output_png='ukraine_hex_map.png'):
    """Render the hex map as a PNG using matplotlib."""
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    fig.patch.set_facecolor('#f0f0f0')
    ax.set_facecolor('#f0f0f0')

    # Draw Ukraine boundary
    boundary_x, boundary_y = polygon.exterior.xy
    ax.plot(boundary_x, boundary_y, color='#333333', linewidth=1.5, zorder=3)

    # Color scale
    counts = [h['count'] for h in hexagons]
    max_count = max(counts) if counts else 1

    # Custom colormap: light → amber → deep red
    colors_list = ['#f7f7f7', '#fff3cd', '#ffc107', '#ff9800', '#f44336', '#b71c1c']
    cmap = LinearSegmentedColormap.from_list('density', colors_list, N=256)
    norm = Normalize(vmin=0, vmax=max_count)

    patches = []
    colors = []
    for hexagon in hexagons:
        poly = mpatches.Polygon(hexagon['vertices'], closed=True)
        patches.append(poly)
        colors.append(hexagon['count'])

    collection = PatchCollection(patches, cmap=cmap, norm=norm,
                                  edgecolor='#cccccc', linewidth=0.3, zorder=2)
    collection.set_array(np.array(colors))
    ax.add_collection(collection)

    # Colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label('Artifact Count', fontsize=12)

    ax.set_xlim(21, 41)
    ax.set_ylim(44, 53)
    ax.set_aspect('equal')
    ax.set_title('Украдені скарби — Artifact Density Hex Map\n'
                 'Ukrainian artifacts in Russian museums (Hermitage & SHM)',
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Longitude', fontsize=11)
    ax.set_ylabel('Latitude', fontsize=11)

    # Stats annotation
    total = sum(counts)
    nonzero = sum(1 for c in counts if c > 0)
    ax.text(0.02, 0.02,
            f'Total artifacts: {total:,}  |  Active hexes: {nonzero}/{len(hexagons)}  |  Max density: {max_count:,}',
            transform=ax.transAxes, fontsize=10, color='#555555',
            verticalalignment='bottom')

    plt.tight_layout()
    plt.savefig(output_png, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f"Saved: {output_png}")
    plt.close()


def render_html(hexagons, polygon, output_html='ukraine_hex_map.html'):
    """Render an interactive HTML/SVG hex map."""
    counts = [h['count'] for h in hexagons]
    max_count = max(counts) if counts else 1

    # SVG coordinate transform (lng/lat → SVG pixels)
    svg_w, svg_h = 1200, 900
    min_lng, max_lng = 21.5, 40.5
    min_lat, max_lat = 44.0, 52.8

    def to_svg(lng, lat):
        x = (lng - min_lng) / (max_lng - min_lng) * svg_w
        y = svg_h - (lat - min_lat) / (max_lat - min_lat) * svg_h
        return x, y

    # Build Ukraine boundary path
    boundary_points = list(polygon.exterior.coords)
    path_d = 'M ' + ' L '.join(f'{to_svg(lng, lat)[0]:.1f},{to_svg(lng, lat)[1]:.1f}'
                                 for lng, lat in boundary_points) + ' Z'

    # Build hex SVG elements
    hex_svgs = []
    for hexagon in hexagons:
        count = hexagon['count']
        herm = hexagon['hermitage']
        shm = hexagon['shm']

        if count == 0:
            fill = '#f0f0f0'
            opacity = '0.4'
        else:
            # Intensity: log scale
            intensity = min(math.log(count + 1) / math.log(max_count + 1), 1.0)

            # Blue-green split: blend between Hermitage green and SHM blue
            if herm + shm > 0:
                blue_ratio = shm / (herm + shm)
            else:
                blue_ratio = 0.5

            r = int(30 + (1 - intensity) * 200)
            g = int(80 * (1 - blue_ratio) + 100 * intensity * (1 - blue_ratio))
            b = int(180 * blue_ratio + 80 * (1 - blue_ratio))

            # Simpler: use warm scale
            if intensity < 0.25:
                fill = f'#fff3cd'
            elif intensity < 0.5:
                fill = f'#ffc107'
            elif intensity < 0.75:
                fill = f'#ff9800'
            else:
                fill = f'#e53935'
            opacity = f'{0.5 + intensity * 0.5:.2f}'

        points = ' '.join(f'{to_svg(vx, vy)[0]:.1f},{to_svg(vx, vy)[1]:.1f}'
                          for vx, vy in hexagon['vertices'])

        cx, cy = to_svg(*hexagon['center'])
        tooltip = f"Artifacts: {count} (Hermitage: {herm}, SHM: {shm})"

        hex_svgs.append(
            f'<polygon points="{points}" fill="{fill}" fill-opacity="{opacity}" '
            f'stroke="#999" stroke-width="0.5" data-count="{count}" '
            f'data-hermitage="{herm}" data-shm="{shm}">'
            f'<title>{tooltip}</title></polygon>'
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Украдені скарби — Hex Density Map</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ 
    background: #1a1a2e; 
    color: #e0e0e0; 
    font-family: 'Segoe UI', system-ui, sans-serif;
    display: flex; flex-direction: column; align-items: center;
    min-height: 100vh; padding: 30px 20px;
  }}
  h1 {{ 
    font-size: 28px; margin-bottom: 5px; color: #ffd500;
    letter-spacing: 1px;
  }}
  h2 {{
    font-size: 16px; color: #8ab4e0; margin-bottom: 20px;
    font-weight: 400;
  }}
  .map-container {{
    background: #f8f8f8;
    border-radius: 12px;
    padding: 15px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
  }}
  svg polygon:hover {{
    stroke: #000;
    stroke-width: 2;
    cursor: pointer;
  }}
  .legend {{
    display: flex; gap: 20px; margin-top: 20px;
    align-items: center; font-size: 14px;
  }}
  .legend-item {{
    display: flex; align-items: center; gap: 6px;
  }}
  .legend-swatch {{
    width: 24px; height: 24px; border-radius: 4px;
    border: 1px solid #555;
  }}
  .stats {{
    margin-top: 15px; font-size: 14px; color: #8ab4e0;
  }}
  #tooltip {{
    position: fixed; background: #222; color: #fff;
    padding: 8px 14px; border-radius: 6px; font-size: 13px;
    pointer-events: none; display: none; z-index: 100;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
  }}
</style>
</head>
<body>

<h1>Украдені скарби</h1>
<h2>Artifact Density Hex Map — Ukrainian artifacts in Russian museums</h2>

<div class="map-container">
  <svg viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}" height="{svg_h}"
       xmlns="http://www.w3.org/2000/svg">
    <!-- Hexagons -->
    {''.join(hex_svgs)}
    <!-- Ukraine boundary -->
    <path d="{path_d}" fill="none" stroke="#333" stroke-width="2"/>
  </svg>
</div>

<div class="legend">
  <div class="legend-item"><div class="legend-swatch" style="background:#f0f0f0"></div> 0</div>
  <div class="legend-item"><div class="legend-swatch" style="background:#fff3cd"></div> Low</div>
  <div class="legend-item"><div class="legend-swatch" style="background:#ffc107"></div> Medium</div>
  <div class="legend-item"><div class="legend-swatch" style="background:#ff9800"></div> High</div>
  <div class="legend-item"><div class="legend-swatch" style="background:#e53935"></div> Very High</div>
</div>

<div class="stats">
  Total artifacts: {sum(counts):,} &nbsp;|&nbsp; 
  Hexagons: {len(hexagons)} &nbsp;|&nbsp;
  Max density: {max_count:,} per hex
</div>

<div id="tooltip"></div>

<script>
document.querySelectorAll('polygon').forEach(p => {{
  p.addEventListener('mousemove', e => {{
    const tt = document.getElementById('tooltip');
    const count = p.getAttribute('data-count');
    const herm = p.getAttribute('data-hermitage');
    const shm = p.getAttribute('data-shm');
    tt.innerHTML = `<strong>${{count}}</strong> artifacts<br>Hermitage: ${{herm}} · SHM: ${{shm}}`;
    tt.style.display = 'block';
    tt.style.left = (e.clientX + 15) + 'px';
    tt.style.top = (e.clientY - 10) + 'px';
  }});
  p.addEventListener('mouseleave', () => {{
    document.getElementById('tooltip').style.display = 'none';
  }});
}});
</script>

</body>
</html>"""

    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Saved: {output_html}")


def main():
    # Input file
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    elif Path('combined_database_updated.csv').exists():
        input_file = 'combined_database_updated.csv'
    elif Path('combined_database.csv').exists():
        input_file = 'combined_database.csv'
    else:
        print("Error: No CSV file found. Provide as argument or place in current directory.")
        sys.exit(1)

    print(f"Reading: {input_file}")
    artifacts, hermitage, shm = read_artifacts(input_file)

    if not artifacts:
        print("No artifacts with valid coordinates found!")
        sys.exit(1)

    # Generate hex grid
    hex_size = 0.35  # degrees — adjust for finer/coarser grid
    print(f"\nGenerating hex grid (size={hex_size}°)...")
    polygon = get_ukraine_polygon()
    hexagons = generate_hex_grid(polygon, hex_size)
    print(f"Created {len(hexagons)} hexagons within Ukraine boundary")

    # Assign artifacts to hexes
    print("Computing density...")
    assign_artifacts_to_hexes(hexagons, artifacts, hermitage, shm, hex_size)

    # Render outputs
    print("\nRendering...")
    render_matplotlib(hexagons, polygon, 'ukraine_hex_map.png')
    render_html(hexagons, polygon, 'ukraine_hex_map.html')

    print("\nDone!")


if __name__ == '__main__':
    main()
