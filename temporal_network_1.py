"""
Temporal Network Animation: How the material network grows over time.

Shows materials appearing and connecting as you move through historical periods.
Animated playback with play/pause, scrubber, and cumulative/snapshot modes.

Usage:
    python temporal_network.py
    python temporal_network.py combined_database_updated.csv
"""

import csv
import json
import math
import sys
from pathlib import Path
from collections import defaultdict


def format_date(year):
    """Format a numeric year into a readable label."""
    y = int(year)
    if y < 0:
        return f"{abs(y)} BCE"
    elif y == 0:
        return "1 BCE"
    else:
        return f"{y} CE"


def read_data(filepath):
    # Per individual date: which keywords appear, and co-occurrence
    period_keywords = defaultdict(lambda: defaultdict(int))  # date -> keyword -> count
    period_museum = defaultdict(lambda: defaultdict(lambda: {'hermitage': 0, 'shm': 0}))
    keyword_totals = defaultdict(int)
    raw_dates = set()

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            kw = (row.get('Ключевые слова') or '').strip()
            date = (row.get('dates') or '').strip()
            museum = (row.get('museum') or '').strip().lower()
            if not kw or not date:
                continue
            try:
                date_val = float(date)
            except ValueError:
                continue

            date_label = format_date(date_val)
            raw_dates.add((date_val, date_label))
            period_keywords[date_label][kw] += 1
            keyword_totals[kw] += 1
            if museum == 'shm':
                period_museum[date_label][kw]['shm'] += 1
            else:
                period_museum[date_label][kw]['hermitage'] += 1

    # Sort by numeric value
    sorted_dates = sorted(raw_dates, key=lambda x: x[0])
    active_periods = [label for _, label in sorted_dates]

    print(f"Active periods (individual dates): {len(active_periods)}")
    print(f"Total keywords: {len(keyword_totals)}")
    total = sum(keyword_totals.values())
    print(f"Total artifacts: {total:,}")
    print(f"Date range: {active_periods[0]} → {active_periods[-1]}")

    return period_keywords, period_museum, keyword_totals, active_periods


def build_temporal_snapshots(period_keywords, period_museum, keyword_totals, active_periods):
    """Build snapshot network state at each time step — only materials present in that period."""
    snapshots = []
    first_seen = {}

    for pi, period in enumerate(active_periods):
        kws_this_period = period_keywords[period]
        if not kws_this_period:
            continue

        new_keywords = []
        for kw in kws_this_period:
            if kw not in first_seen:
                first_seen[kw] = pi
                new_keywords.append(kw)

        # Nodes: ONLY keywords present in this period
        nodes = []
        for kw, count in kws_this_period.items():
            mus = period_museum[period][kw]
            nodes.append({
                'id': kw,
                'label': kw,
                'total': count,
                'thisperiod': count,
                'hermitage': mus['hermitage'],
                'shm': mus['shm'],
                'firstSeen': first_seen[kw],
                'isNew': kw in new_keywords,
            })

        # Edges: co-occurrence ONLY within this period
        kw_list = list(kws_this_period.keys())
        edges = []
        for i in range(len(kw_list)):
            for j in range(i + 1, len(kw_list)):
                w = min(kws_this_period[kw_list[i]], kws_this_period[kw_list[j]])
                if w > 0:
                    edges.append({
                        'source': kw_list[i],
                        'target': kw_list[j],
                        'weight': w,
                    })

        artifact_count = sum(kws_this_period.values())

        snapshots.append({
            'period': period,
            'periodIndex': pi,
            'nodes': nodes,
            'edges': edges,
            'newKeywords': new_keywords,
            'artifactsThisPeriod': artifact_count,
            'nodeCount': len(nodes),
            'edgeCount': len(edges),
        })

    print(f"Built {len(snapshots)} snapshots")
    return snapshots


def generate_html(snapshots, active_periods):
    snapshots_json = json.dumps(snapshots)
    periods_json = json.dumps(active_periods)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Украдені скарби — Temporal Material Network</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #0a0e17;
    color: #e6edf3;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    overflow: hidden;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }}

  header {{
    padding: 12px 24px;
    background: rgba(10,14,23,0.95);
    border-bottom: 1px solid #1e2533;
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 10;
    flex-shrink: 0;
  }}
  .title-block h1 {{ font-size: 22px; color: #ffd500; }}
  .title-block h2 {{ font-size: 13px; color: #6e7681; font-weight: 400; margin-top: 2px; }}

  #chart {{ flex: 1; position: relative; }}
  svg {{ width: 100%; height: 100%; }}

  .link {{ fill: none; transition: stroke-opacity 0.3s; }}
  .node-group {{ cursor: pointer; transition: opacity 0.3s; }}
  .node-label {{
    fill: #c9d1d9;
    font-size: 10px;
    pointer-events: none;
    text-anchor: middle;
  }}

  /* Timeline bar */
  #timeline {{
    padding: 12px 24px 16px;
    background: #0d1117;
    border-top: 1px solid #1e2533;
    flex-shrink: 0;
  }}
  #timeline-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }}
  #period-label {{
    font-size: 26px;
    font-weight: 800;
    color: #ffd500;
    text-shadow: 0 0 20px rgba(255,213,0,0.3);
    min-width: 200px;
  }}
  #timeline-stats {{
    display: flex;
    gap: 24px;
    font-size: 13px;
  }}
  .ts-val {{ font-weight: 700; font-variant-numeric: tabular-nums; }}
  .ts-gold {{ color: #ffd500; }}
  .ts-green {{ color: #4ade80; }}
  .ts-blue {{ color: #60a5fa; }}
  .ts-new {{ color: #f97316; }}

  #controls-row {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .play-btn {{
    width: 44px; height: 44px;
    border-radius: 50%;
    border: 2px solid #ffd500;
    background: transparent;
    color: #ffd500;
    font-size: 20px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
    flex-shrink: 0;
  }}
  .play-btn:hover {{ background: rgba(255,213,0,0.15); }}
  .play-btn.playing {{ background: rgba(255,213,0,0.2); }}

  .speed-btn {{
    padding: 4px 10px;
    border: 1px solid #30363d;
    border-radius: 6px;
    background: #161b22;
    color: #8b949e;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.15s;
  }}
  .speed-btn:hover {{ color: #e6edf3; }}
  .speed-btn.active {{ color: #ffd500; border-color: #ffd500; }}

  #scrubber {{
    -webkit-appearance: none;
    appearance: none;
    flex: 1;
    height: 10px;
    background: #1a2233;
    border-radius: 5px;
    cursor: pointer;
    position: relative;
  }}
  #scrubber::-webkit-slider-thumb {{
    -webkit-appearance: none;
    width: 22px; height: 22px;
    border-radius: 50%;
    background: #ffd500;
    border: 2px solid #fff;
    box-shadow: 0 0 10px rgba(255,213,0,0.5);
    cursor: pointer;
  }}
  #scrubber::-moz-range-thumb {{
    width: 22px; height: 22px;
    border-radius: 50%;
    background: #ffd500;
    border: 2px solid #fff;
    box-shadow: 0 0 10px rgba(255,213,0,0.5);
    cursor: pointer;
  }}
  #scrubber::-moz-range-track {{
    height: 10px;
    background: #1a2233;
    border-radius: 5px;
  }}

  /* Period markers under scrubber */
  #period-marks {{
    display: flex;
    justify-content: space-between;
    margin-top: 4px;
    padding: 0 11px;
  }}
  .period-mark {{
    font-size: 8px;
    color: #4a5568;
    transform: rotate(-30deg);
    transform-origin: left;
    white-space: nowrap;
  }}

  #tooltip {{
    position: fixed;
    background: rgba(13,17,23,0.96);
    border: 1px solid #ffd500;
    border-radius: 10px;
    padding: 12px 16px;
    pointer-events: none;
    display: none;
    z-index: 100;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    font-size: 13px;
    line-height: 1.7;
    max-width: 300px;
  }}
  .tt-name {{ font-weight: 700; color: #ffd500; font-size: 15px; }}
  .tt-count {{ font-size: 20px; font-weight: 800; color: #fff; }}
  .tt-bar {{ height: 6px; border-radius: 3px; margin: 6px 0; display: flex; overflow: hidden; }}
  .tt-bar-herm {{ background: #4ade80; }}
  .tt-bar-shm {{ background: #60a5fa; }}

  /* New node pulse animation */
  @keyframes pulse {{
    0% {{ r: 8; opacity: 1; }}
    50% {{ r: 20; opacity: 0.3; }}
    100% {{ r: 8; opacity: 0; }}
  }}
  .pulse-ring {{
    fill: #f97316;
    animation: pulse 1.5s ease-out;
    pointer-events: none;
  }}
</style>
</head>
<body>

<header>
  <div class="title-block">
    <h1>Украдені скарби — Temporal Material Network</h1>
    <h2>Material co-occurrence at each date — materials appear only when active</h2>
  </div>
</header>

<div id="chart"></div>

<div id="timeline">
  <div id="timeline-header">
    <div id="period-label">—</div>
    <div id="timeline-stats">
      <span>Materials: <span class="ts-val ts-gold" id="sNodes">0</span></span>
      <span>Connections: <span class="ts-val ts-gold" id="sEdges">0</span></span>
      <span>Artifacts: <span class="ts-val ts-new" id="sThis">0</span></span>
      <span>New materials: <span class="ts-val ts-new" id="sNew">0</span></span>
    </div>
  </div>
  <div id="controls-row">
    <button class="play-btn" id="btnPlay">▶</button>
    <input type="range" id="scrubber" min="0" max="0" value="0" step="1">
    <button class="speed-btn" data-speed="2000">0.5×</button>
    <button class="speed-btn active" data-speed="800">1×</button>
    <button class="speed-btn" data-speed="400">2×</button>
    <button class="speed-btn" data-speed="150">4×</button>
  </div>
  <div id="period-marks"></div>
</div>

<div id="tooltip"></div>

<script>
const snapshots = {snapshots_json};
const periods = {periods_json};
let currentStep = 0;
let playing = false;
let playInterval = null;
let speed = 800;

const width = window.innerWidth;
const height = window.innerHeight - 200;

const svg = d3.select('#chart').append('svg')
  .attr('viewBox', `0 0 ${{width}} ${{height}}`);

const g = svg.append('g');

svg.call(d3.zoom()
  .scaleExtent([0.3, 4])
  .on('zoom', (event) => g.attr('transform', event.transform))
);

const tooltip = d3.select('#tooltip');

// Setup scrubber
const scrubber = document.getElementById('scrubber');
scrubber.max = snapshots.length - 1;

// Period marks (show every Nth to avoid overlap)
const marksDiv = document.getElementById('period-marks');
const markStep = Math.max(1, Math.floor(snapshots.length / 15));
snapshots.forEach((s, i) => {{
  if (i % markStep === 0 || i === snapshots.length - 1) {{
    const mark = document.createElement('span');
    mark.className = 'period-mark';
    mark.textContent = s.period;
    marksDiv.appendChild(mark);
  }}
}});

// Force simulation (persistent)
let simulation = d3.forceSimulation()
  .force('charge', d3.forceManyBody().strength(-200))
  .force('center', d3.forceCenter(width / 2, height / 2))
  .force('collision', d3.forceCollide().radius(d => nodeRadius(d) + 5))
  .force('link', d3.forceLink().id(d => d.id).distance(80).strength(0.3))
  .alphaDecay(0.02)
  .on('tick', ticked);

let nodeElements, linkElements, labelElements;
let currentNodes = [];
let currentLinks = [];

function nodeRadius(d) {{
  return Math.max(5, Math.sqrt(d.total) * 0.8);
}}

function nodeColor(d) {{
  if (d.isNew) return '#f97316';
  if (d.shm > d.hermitage) return '#60a5fa';
  return '#4ade80';
}}

function ticked() {{
  if (linkElements) {{
    linkElements
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);
  }}
  if (nodeElements) {{
    nodeElements.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
  }}
  if (labelElements) {{
    labelElements.attr('x', d => d.x).attr('y', d => d.y + nodeRadius(d) + 12);
  }}
}}

function updateVisualization(step) {{
  const snap = snapshots[step];

  // Update stats
  document.getElementById('period-label').textContent = snap.period;
  document.getElementById('sNodes').textContent = snap.nodeCount;
  document.getElementById('sEdges').textContent = snap.edgeCount;
  document.getElementById('sThis').textContent = snap.artifactsThisPeriod.toLocaleString();
  document.getElementById('sNew').textContent = snap.newKeywords.length;
  scrubber.value = step;

  // Merge nodes — keep positions of existing ones
  const oldMap = {{}};
  currentNodes.forEach(n => {{ oldMap[n.id] = {{ x: n.x, y: n.y, vx: n.vx, vy: n.vy }}; }});

  const newNodes = snap.nodes.map(n => {{
    const existing = oldMap[n.id];
    return {{
      ...n,
      x: existing ? existing.x : width / 2 + (Math.random() - 0.5) * 100,
      y: existing ? existing.y : height / 2 + (Math.random() - 0.5) * 100,
      vx: existing ? existing.vx * 0.5 : 0,
      vy: existing ? existing.vy * 0.5 : 0,
    }};
  }});

  const newLinks = snap.edges.map(e => ({{ ...e }}));
  const maxWeight = d3.max(newLinks, d => d.weight) || 1;

  currentNodes = newNodes;
  currentLinks = newLinks;

  // Update links
  const linkSel = g.selectAll('.link').data(newLinks, d => d.source + '-' + d.target);
  linkSel.exit().transition().duration(300).attr('stroke-opacity', 0).remove();
  const linkEnter = linkSel.enter().append('line')
    .attr('class', 'link')
    .attr('stroke', '#ffd500')
    .attr('stroke-opacity', 0);

  linkElements = linkEnter.merge(linkSel)
    .transition().duration(500)
    .attr('stroke-width', d => Math.max(0.3, Math.sqrt(d.weight / maxWeight) * 4))
    .attr('stroke-opacity', d => 0.05 + (d.weight / maxWeight) * 0.4)
    .selection();

  // Update nodes
  const nodeSel = g.selectAll('.node-group').data(newNodes, d => d.id);
  nodeSel.exit().transition().duration(300).attr('opacity', 0).remove();

  const nodeEnter = nodeSel.enter().append('g')
    .attr('class', 'node-group')
    .attr('transform', d => `translate(${{d.x}},${{d.y}})`)
    .call(d3.drag()
      .on('start', (event, d) => {{
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x; d.fy = d.y;
      }})
      .on('drag', (event, d) => {{ d.fx = event.x; d.fy = event.y; }})
      .on('end', (event, d) => {{
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null; d.fy = null;
      }})
    );

  // Pulse ring for new nodes
  nodeEnter.filter(d => d.isNew).append('circle')
    .attr('class', 'pulse-ring')
    .attr('r', 8);

  nodeEnter.append('circle')
    .attr('class', 'node-circle')
    .attr('r', 0)
    .attr('stroke', '#fff')
    .attr('stroke-width', 0.8);

  nodeElements = nodeEnter.merge(nodeSel);

  nodeElements.select('.node-circle')
    .transition().duration(500)
    .attr('r', d => nodeRadius(d))
    .attr('fill', d => nodeColor(d));

  // Labels
  const labelSel = g.selectAll('.node-label').data(newNodes, d => d.id);
  labelSel.exit().remove();
  const labelEnter = labelSel.enter().append('text')
    .attr('class', 'node-label')
    .attr('opacity', 0);

  labelElements = labelEnter.merge(labelSel)
    .text(d => d.label)
    .style('font-size', d => d.total > 500 ? '11px' : '9px')
    .style('font-weight', d => d.total > 1000 ? '600' : '400')
    .style('fill', d => d.isNew ? '#f97316' : '#8b949e')
    .transition().duration(500)
    .attr('opacity', d => d.total > 50 ? 1 : 0.6)
    .selection();

  // Tooltip
  nodeElements.on('mouseover', (event, d) => {{
    const hermW = d.total > 0 ? (d.hermitage / d.total) * 140 : 0;
    tooltip.html(`
      <div class="tt-name">${{d.label}}</div>
      <div class="tt-count">${{d.total.toLocaleString()}} artifacts</div>
      <div class="tt-bar">
        <div class="tt-bar-herm" style="width:${{hermW}}px"></div>
        <div class="tt-bar-shm" style="flex:1"></div>
      </div>
      <div><span style="color:#4ade80">■</span> Hermitage: ${{d.hermitage.toLocaleString()}}</div>
      <div><span style="color:#60a5fa">■</span> SHM: ${{d.shm.toLocaleString()}}</div>
      <div style="color:#f97316;margin-top:4px">${{d.isNew ? '★ First appearance!' : 'First seen: ' + periods[d.firstSeen]}}</div>
    `)
    .style('display', 'block')
    .style('left', (event.clientX + 16) + 'px')
    .style('top', (event.clientY - 16) + 'px');

    // Highlight connections
    const connected = new Set([d.id]);
    newLinks.forEach(l => {{
      const sid = typeof l.source === 'object' ? l.source.id : l.source;
      const tid = typeof l.target === 'object' ? l.target.id : l.target;
      if (sid === d.id) connected.add(tid);
      if (tid === d.id) connected.add(sid);
    }});
    nodeElements.style('opacity', n => connected.has(n.id) ? 1 : 0.1);
    linkElements.attr('stroke-opacity', l => {{
      const sid = typeof l.source === 'object' ? l.source.id : l.source;
      const tid = typeof l.target === 'object' ? l.target.id : l.target;
      return (sid === d.id || tid === d.id) ? 0.7 : 0.02;
    }});
  }})
  .on('mouseout', () => {{
    tooltip.style('display', 'none');
    nodeElements.style('opacity', 1);
    if (linkElements) {{
      const mw = d3.max(newLinks, d => d.weight) || 1;
      linkElements.attr('stroke-opacity', d => 0.05 + (d.weight / mw) * 0.4);
    }}
  }});

  // Restart simulation
  simulation.nodes(newNodes);
  simulation.force('link').links(newLinks);
  simulation.alpha(0.4).restart();
}}

// === PLAYBACK ===
function play() {{
  playing = true;
  document.getElementById('btnPlay').textContent = '⏸';
  document.getElementById('btnPlay').classList.add('playing');

  playInterval = setInterval(() => {{
    if (currentStep < snapshots.length - 1) {{
      currentStep++;
      updateVisualization(currentStep);
    }} else {{
      pause();
    }}
  }}, speed);
}}

function pause() {{
  playing = false;
  clearInterval(playInterval);
  document.getElementById('btnPlay').textContent = '▶';
  document.getElementById('btnPlay').classList.remove('playing');
}}

document.getElementById('btnPlay').addEventListener('click', () => {{
  if (playing) pause();
  else {{
    if (currentStep >= snapshots.length - 1) currentStep = 0;
    play();
  }}
}});

scrubber.addEventListener('input', function() {{
  pause();
  currentStep = parseInt(this.value);
  updateVisualization(currentStep);
}});

// Speed buttons
document.querySelectorAll('.speed-btn').forEach(btn => {{
  btn.addEventListener('click', function() {{
    document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
    this.classList.add('active');
    speed = parseInt(this.dataset.speed);
    if (playing) {{ pause(); play(); }}
  }});
}});

// Keyboard
document.addEventListener('keydown', e => {{
  if (e.code === 'Space') {{ e.preventDefault(); playing ? pause() : play(); }}
  if (e.code === 'ArrowRight' && currentStep < snapshots.length - 1) {{
    pause(); currentStep++; updateVisualization(currentStep);
  }}
  if (e.code === 'ArrowLeft' && currentStep > 0) {{
    pause(); currentStep--; updateVisualization(currentStep);
  }}
}});

// Resize
window.addEventListener('resize', () => {{
  const w = window.innerWidth;
  const h = window.innerHeight - 200;
  svg.attr('viewBox', `0 0 ${{w}} ${{h}}`);
  simulation.force('center', d3.forceCenter(w / 2, h / 2));
}});

// Start at first step
updateVisualization(0);
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
    period_keywords, period_museum, keyword_totals, active_periods = read_data(input_file)

    if not active_periods:
        print("No data found!")
        sys.exit(1)

    print("\nBuilding temporal snapshots...")
    snapshots = build_temporal_snapshots(period_keywords, period_museum, keyword_totals, active_periods)

    print("\nGenerating visualization...")
    html = generate_html(snapshots, active_periods)

    output_file = 'temporal_network.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\nSaved: {output_file}")


if __name__ == '__main__':
    main()
