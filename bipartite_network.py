"""
Bipartite Network: Collections ↔ Time Periods
Plus transposed: Collection ↔ Collection (shared time periods)

Usage:
    python bipartite_network.py
    python bipartite_network.py combined_database_updated.csv
"""

import csv
import json
import math
import sys
from pathlib import Path
from collections import defaultdict


def read_data(filepath):
    """Read collections and dates, build bipartite edges."""
    edges = defaultdict(int)  # (collection, date) -> count
    coll_totals = defaultdict(int)
    date_totals = defaultdict(int)
    coll_museums = defaultdict(lambda: {'hermitage': 0, 'shm': 0})

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            coll = (row.get('Коллекция') or '').strip()
            date = (row.get('dates') or '').strip()
            museum = (row.get('museum') or '').strip().lower()

            if not coll or not date:
                continue

            try:
                date_val = float(date)
            except ValueError:
                continue

            # Bin dates into periods
            period = date_to_period(date_val)

            edges[(coll, period)] += 1
            coll_totals[coll] += 1
            date_totals[period] += 1

            if museum == 'shm':
                coll_museums[coll]['shm'] += 1
            else:
                coll_museums[coll]['hermitage'] += 1

    print(f"Collections: {len(coll_totals)}")
    print(f"Time periods: {len(date_totals)}")
    print(f"Bipartite edges: {len(edges)}")
    print(f"Total artifacts with both fields: {sum(edges.values()):,}")

    return edges, coll_totals, date_totals, coll_museums


def date_to_period(year):
    """Bin a year into a meaningful period."""
    if year < -3000:
        return "Before 3000 BCE"
    elif year < -1000:
        return f"{int(year // 1000 * 1000)} BCE"
    elif year < -500:
        return "1000–500 BCE"
    elif year < -300:
        return "500–300 BCE"
    elif year < -100:
        return "300–100 BCE"
    elif year < 0:
        return "100–1 BCE"
    elif year < 100:
        return "1–100 CE"
    elif year < 300:
        return "100–300 CE"
    elif year < 500:
        return "300–500 CE"
    elif year < 700:
        return "500–700 CE"
    elif year < 900:
        return "700–900 CE"
    elif year < 1100:
        return "900–1100 CE"
    elif year < 1300:
        return "1100–1300 CE"
    elif year < 1500:
        return "1300–1500 CE"
    elif year < 1700:
        return "1500–1700 CE"
    elif year < 1800:
        return "1700–1800 CE"
    elif year < 1900:
        return "1800–1900 CE"
    else:
        return "1900+ CE"


def period_sort_key(p):
    """Sort key for period labels."""
    order = [
        "Before 3000 BCE",
        "-5000 BCE", "-4000 BCE", "-3000 BCE",
        "-2000 BCE", "-1000 BCE",
        "1000–500 BCE", "500–300 BCE", "300–100 BCE", "100–1 BCE",
        "1–100 CE", "100–300 CE", "300–500 CE", "500–700 CE",
        "700–900 CE", "900–1100 CE", "1100–1300 CE", "1300–1500 CE",
        "1500–1700 CE", "1700–1800 CE", "1800–1900 CE", "1900+ CE",
    ]
    if p in order:
        return order.index(p)
    return 999


def build_transposed(edges, coll_totals):
    """Build collection-to-collection network (shared time periods)."""
    # For each period, which collections are present?
    period_colls = defaultdict(set)
    period_coll_counts = defaultdict(lambda: defaultdict(int))

    for (coll, period), count in edges.items():
        period_colls[period].add(coll)
        period_coll_counts[period][coll] = count

    # Create edges between collections that share periods
    coll_edges = defaultdict(lambda: {'weight': 0, 'shared_periods': []})
    colls = list(coll_totals.keys())

    for period, colls_in_period in period_colls.items():
        coll_list = sorted(colls_in_period)
        for i in range(len(coll_list)):
            for j in range(i + 1, len(coll_list)):
                key = (coll_list[i], coll_list[j])
                # Weight = min of the two counts in this period
                w = min(period_coll_counts[period][coll_list[i]],
                        period_coll_counts[period][coll_list[j]])
                coll_edges[key]['weight'] += w
                coll_edges[key]['shared_periods'].append(period)

    print(f"Transposed edges (collection pairs): {len(coll_edges)}")
    return coll_edges


def generate_html(edges, coll_totals, date_totals, coll_museums, coll_edges):
    """Generate interactive D3.js bipartite + transposed network."""

    # Prepare bipartite data
    sorted_periods = sorted(date_totals.keys(), key=period_sort_key)
    sorted_colls = sorted(coll_totals.keys(), key=lambda c: -coll_totals[c])

    # Shorten collection names for display
    def shorten(name, max_len=45):
        if len(name) <= max_len:
            return name
        return name[:max_len-2] + '…'

    # Bipartite nodes
    bp_nodes = []
    for i, c in enumerate(sorted_colls):
        mus = coll_museums[c]
        bp_nodes.append({
            'id': f'c_{i}',
            'label': shorten(c),
            'fullLabel': c,
            'type': 'collection',
            'total': coll_totals[c],
            'hermitage': mus['hermitage'],
            'shm': mus['shm'],
        })
    for i, p in enumerate(sorted_periods):
        bp_nodes.append({
            'id': f'p_{i}',
            'label': p,
            'fullLabel': p,
            'type': 'period',
            'total': date_totals[p],
        })

    # Bipartite edges
    bp_edges = []
    for (coll, period), count in edges.items():
        ci = sorted_colls.index(coll)
        pi = sorted_periods.index(period)
        bp_edges.append({
            'source': f'c_{ci}',
            'target': f'p_{pi}',
            'weight': count,
        })

    # Transposed nodes (just collections)
    tr_nodes = []
    for i, c in enumerate(sorted_colls):
        mus = coll_museums[c]
        tr_nodes.append({
            'id': f'c_{i}',
            'label': shorten(c),
            'fullLabel': c,
            'type': 'collection',
            'total': coll_totals[c],
            'hermitage': mus['hermitage'],
            'shm': mus['shm'],
        })

    # Transposed edges
    tr_edges = []
    for (c1, c2), data in coll_edges.items():
        ci1 = sorted_colls.index(c1)
        ci2 = sorted_colls.index(c2)
        tr_edges.append({
            'source': f'c_{ci1}',
            'target': f'c_{ci2}',
            'weight': data['weight'],
            'sharedPeriods': len(data['shared_periods']),
            'periodNames': data['shared_periods'][:5],
        })

    bp_data = json.dumps({'nodes': bp_nodes, 'edges': bp_edges})
    tr_data = json.dumps({'nodes': tr_nodes, 'edges': tr_edges})
    total_artifacts = sum(edges.values())

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Украдені скарби — Bipartite Network</title>
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
    padding: 14px 24px;
    background: rgba(10, 14, 23, 0.95);
    border-bottom: 1px solid #1e2533;
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 10;
    flex-shrink: 0;
  }}
  .title-block h1 {{
    font-size: 22px;
    color: #ffd500;
  }}
  .title-block h2 {{
    font-size: 13px;
    color: #6e7681;
    font-weight: 400;
    margin-top: 2px;
  }}

  .mode-buttons {{
    display: flex;
    gap: 6px;
  }}
  .mode-btn {{
    padding: 8px 18px;
    border: 1px solid #30363d;
    border-radius: 8px;
    background: #161b22;
    color: #8b949e;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
  }}
  .mode-btn:hover {{ background: #21262d; color: #e6edf3; }}
  .mode-btn.active {{
    background: #1a2744;
    color: #ffd500;
    border-color: #ffd500;
  }}

  #chart {{
    flex: 1;
    position: relative;
  }}
  svg {{ width: 100%; height: 100%; }}

  .link {{
    fill: none;
    stroke-opacity: 0.15;
    transition: stroke-opacity 0.2s;
  }}
  .link.highlighted {{
    stroke-opacity: 0.7;
  }}
  .link.dimmed {{
    stroke-opacity: 0.03;
  }}

  .node-group {{ cursor: pointer; }}
  .node-group:hover .node-circle {{
    filter: brightness(1.4);
  }}
  .node-label {{
    fill: #c9d1d9;
    font-size: 10px;
    pointer-events: none;
  }}
  .node-label.collection {{
    text-anchor: end;
    font-size: 10.5px;
  }}
  .node-label.period {{
    text-anchor: start;
    font-size: 11px;
    font-weight: 600;
  }}

  #tooltip {{
    position: fixed;
    background: rgba(13, 17, 23, 0.96);
    border: 1px solid #ffd500;
    border-radius: 10px;
    padding: 12px 16px;
    pointer-events: none;
    display: none;
    z-index: 100;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5), 0 0 12px rgba(255,213,0,0.1);
    font-size: 13px;
    line-height: 1.7;
    max-width: 350px;
  }}
  .tt-name {{ font-weight: 700; color: #ffd500; font-size: 15px; margin-bottom: 4px; }}
  .tt-count {{ font-size: 20px; font-weight: 800; color: #fff; }}
  .tt-bar {{ height: 6px; border-radius: 3px; margin: 6px 0; display: flex; overflow: hidden; }}
  .tt-bar-herm {{ background: #4ade80; }}
  .tt-bar-shm {{ background: #60a5fa; }}
  .tt-detail {{ color: #8b949e; font-size: 12px; }}

  #info-bar {{
    padding: 8px 24px;
    background: #0d1117;
    border-top: 1px solid #1e2533;
    font-size: 12px;
    color: #6e7681;
    display: flex;
    gap: 24px;
    flex-shrink: 0;
  }}
  .info-val {{ color: #ffd500; font-weight: 600; }}
</style>
</head>
<body>

<header>
  <div class="title-block">
    <h1>Украдені скарби — Network View</h1>
    <h2 id="subtitle">Collections ↔ Time Periods (bipartite)</h2>
  </div>
  <div class="mode-buttons">
    <button class="mode-btn active" id="btnBipartite">Collections ↔ Periods</button>
    <button class="mode-btn" id="btnTransposed">Collection ↔ Collection</button>
  </div>
</header>

<div id="chart"></div>

<div id="info-bar">
  <span>Artifacts: <span class="info-val">{total_artifacts:,}</span></span>
  <span>Collections: <span class="info-val">{len(sorted_colls)}</span></span>
  <span>Time periods: <span class="info-val">{len(sorted_periods)}</span></span>
  <span id="edgeInfo">Edges: <span class="info-val">{len(bp_edges)}</span></span>
  <span style="margin-left:auto; color:#4a5568">Drag to reposition · Hover for details · Click to highlight</span>
</div>

<div id="tooltip"></div>

<script>
const bpData = {bp_data};
const trData = {tr_data};
let currentMode = 'bipartite';

const width = window.innerWidth;
const height = window.innerHeight - 110;

const svg = d3.select('#chart').append('svg')
  .attr('viewBox', `0 0 ${{width}} ${{height}}`);

const g = svg.append('g');

// Zoom
svg.call(d3.zoom()
  .scaleExtent([0.3, 4])
  .on('zoom', (event) => g.attr('transform', event.transform))
);

const tooltip = d3.select('#tooltip');

function showTooltip(event, html) {{
  tooltip.html(html)
    .style('display', 'block')
    .style('left', (event.clientX + 16) + 'px')
    .style('top', (event.clientY - 16) + 'px');
}}

function hideTooltip() {{
  tooltip.style('display', 'none');
}}

// ============== BIPARTITE LAYOUT ==============
function drawBipartite() {{
  g.selectAll('*').remove();
  document.getElementById('subtitle').textContent = 'Collections ↔ Time Periods (bipartite)';
  document.getElementById('edgeInfo').innerHTML = 'Edges: <span class="info-val">' + bpData.edges.length + '</span>';

  const colls = bpData.nodes.filter(n => n.type === 'collection');
  const periods = bpData.nodes.filter(n => n.type === 'period');

  const leftX = width * 0.28;
  const rightX = width * 0.72;
  const padding = 30;
  const collSpacing = Math.min(20, (height - 2 * padding) / colls.length);
  const periodSpacing = Math.min(30, (height - 2 * padding) / periods.length);

  const collStartY = (height - colls.length * collSpacing) / 2;
  const periodStartY = (height - periods.length * periodSpacing) / 2;

  // Position nodes
  const nodeMap = {{}};
  colls.forEach((n, i) => {{
    n.x = leftX;
    n.y = collStartY + i * collSpacing;
    nodeMap[n.id] = n;
  }});
  periods.forEach((n, i) => {{
    n.x = rightX;
    n.y = periodStartY + i * periodSpacing;
    nodeMap[n.id] = n;
  }});

  // Max edge weight for scaling
  const maxWeight = d3.max(bpData.edges, d => d.weight);

  // Draw edges
  const links = g.append('g').selectAll('.link')
    .data(bpData.edges)
    .join('path')
    .attr('class', 'link')
    .attr('d', d => {{
      const s = nodeMap[d.source];
      const t = nodeMap[d.target];
      const midX = (s.x + t.x) / 2;
      return `M${{s.x}},${{s.y}} C${{midX}},${{s.y}} ${{midX}},${{t.y}} ${{t.x}},${{t.y}}`;
    }})
    .attr('stroke', d => {{
      const s = nodeMap[d.source];
      if (s.shm > s.hermitage) return '#60a5fa';
      return '#4ade80';
    }})
    .attr('stroke-width', d => Math.max(0.5, Math.sqrt(d.weight / maxWeight) * 6));

  // Draw collection nodes
  const collGroups = g.append('g').selectAll('.node-group')
    .data(colls)
    .join('g')
    .attr('class', 'node-group')
    .attr('transform', d => `translate(${{d.x}},${{d.y}})`);

  collGroups.append('circle')
    .attr('class', 'node-circle')
    .attr('r', d => Math.max(4, Math.sqrt(d.total / d3.max(colls, c => c.total)) * 14))
    .attr('fill', d => d.shm > d.hermitage ? '#60a5fa' : '#4ade80')
    .attr('stroke', '#fff')
    .attr('stroke-width', 0.5);

  collGroups.append('text')
    .attr('class', 'node-label collection')
    .attr('x', -12)
    .attr('dy', '0.35em')
    .text(d => d.label);

  // Draw period nodes
  const periodGroups = g.append('g').selectAll('.node-group')
    .data(periods)
    .join('g')
    .attr('class', 'node-group')
    .attr('transform', d => `translate(${{d.x}},${{d.y}})`);

  periodGroups.append('circle')
    .attr('class', 'node-circle')
    .attr('r', d => Math.max(4, Math.sqrt(d.total / d3.max(periods, p => p.total)) * 14))
    .attr('fill', '#ffd500')
    .attr('stroke', '#fff')
    .attr('stroke-width', 0.5);

  periodGroups.append('text')
    .attr('class', 'node-label period')
    .attr('x', 12)
    .attr('dy', '0.35em')
    .text(d => d.label);

  // Interactions
  function highlightNode(nodeId) {{
    const connected = new Set();
    connected.add(nodeId);
    bpData.edges.forEach(e => {{
      if (e.source === nodeId) connected.add(e.target);
      if (e.target === nodeId) connected.add(e.source);
    }});

    links.classed('highlighted', d => d.source === nodeId || d.target === nodeId)
         .classed('dimmed', d => d.source !== nodeId && d.target !== nodeId);
    collGroups.style('opacity', d => connected.has(d.id) ? 1 : 0.2);
    periodGroups.style('opacity', d => connected.has(d.id) ? 1 : 0.2);
  }}

  function resetHighlight() {{
    links.classed('highlighted', false).classed('dimmed', false);
    collGroups.style('opacity', 1);
    periodGroups.style('opacity', 1);
  }}

  collGroups.on('mouseover', (event, d) => {{
    highlightNode(d.id);
    const pctH = d.total > 0 ? ((d.hermitage / d.total) * 100).toFixed(0) : 0;
    const hermW = d.total > 0 ? (d.hermitage / d.total) * 150 : 0;
    showTooltip(event, `
      <div class="tt-name">${{d.fullLabel}}</div>
      <div class="tt-count">${{d.total.toLocaleString()}} artifacts</div>
      <div class="tt-bar">
        <div class="tt-bar-herm" style="width:${{hermW}}px"></div>
        <div class="tt-bar-shm" style="flex:1"></div>
      </div>
      <div><span style="color:#4ade80">■</span> Hermitage: ${{d.hermitage.toLocaleString()}}</div>
      <div><span style="color:#60a5fa">■</span> SHM: ${{d.shm.toLocaleString()}}</div>
    `);
  }})
  .on('mouseout', () => {{ resetHighlight(); hideTooltip(); }});

  periodGroups.on('mouseover', (event, d) => {{
    highlightNode(d.id);
    showTooltip(event, `
      <div class="tt-name">${{d.fullLabel}}</div>
      <div class="tt-count">${{d.total.toLocaleString()}} artifacts</div>
    `);
  }})
  .on('mouseout', () => {{ resetHighlight(); hideTooltip(); }});
}}

// ============== TRANSPOSED (force-directed) ==============
function drawTransposed() {{
  g.selectAll('*').remove();
  document.getElementById('subtitle').textContent = 'Collection ↔ Collection (shared time periods)';
  document.getElementById('edgeInfo').innerHTML = 'Edges: <span class="info-val">' + trData.edges.length + '</span>';

  const nodes = trData.nodes.map(d => ({{ ...d }}));
  const edges = trData.edges.map(d => ({{
    ...d,
    source: d.source,
    target: d.target,
  }}));

  const maxWeight = d3.max(edges, d => d.weight) || 1;

  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(d => d.id).distance(d => 120 - (d.weight / maxWeight) * 60).strength(d => 0.3 + (d.weight / maxWeight) * 0.5))
    .force('charge', d3.forceManyBody().strength(-400))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(30));

  // Draw edges
  const links = g.append('g').selectAll('.link')
    .data(edges)
    .join('line')
    .attr('class', 'link')
    .attr('stroke', '#ffd500')
    .attr('stroke-width', d => Math.max(0.5, Math.sqrt(d.weight / maxWeight) * 5))
    .attr('stroke-opacity', d => 0.05 + (d.weight / maxWeight) * 0.35);

  // Draw nodes
  const nodeGroups = g.append('g').selectAll('.node-group')
    .data(nodes)
    .join('g')
    .attr('class', 'node-group')
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

  nodeGroups.append('circle')
    .attr('class', 'node-circle')
    .attr('r', d => Math.max(8, Math.sqrt(d.total / d3.max(nodes, n => n.total)) * 25))
    .attr('fill', d => d.shm > d.hermitage ? '#60a5fa' : '#4ade80')
    .attr('stroke', '#fff')
    .attr('stroke-width', 1);

  nodeGroups.append('text')
    .attr('class', 'node-label')
    .attr('text-anchor', 'middle')
    .attr('dy', d => Math.max(8, Math.sqrt(d.total / d3.max(nodes, n => n.total)) * 25) + 14)
    .style('font-size', '9px')
    .style('fill', '#8b949e')
    .text(d => d.label.length > 30 ? d.label.substring(0, 28) + '…' : d.label);

  simulation.on('tick', () => {{
    links
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);
    nodeGroups.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
  }});

  // Interactions
  function highlightNode(nodeId) {{
    const connected = new Set();
    connected.add(nodeId);
    edges.forEach(e => {{
      const sid = typeof e.source === 'object' ? e.source.id : e.source;
      const tid = typeof e.target === 'object' ? e.target.id : e.target;
      if (sid === nodeId) connected.add(tid);
      if (tid === nodeId) connected.add(sid);
    }});

    links.classed('highlighted', d => {{
      const sid = typeof d.source === 'object' ? d.source.id : d.source;
      const tid = typeof d.target === 'object' ? d.target.id : d.target;
      return sid === nodeId || tid === nodeId;
    }}).classed('dimmed', d => {{
      const sid = typeof d.source === 'object' ? d.source.id : d.source;
      const tid = typeof d.target === 'object' ? d.target.id : d.target;
      return sid !== nodeId && tid !== nodeId;
    }});
    nodeGroups.style('opacity', d => connected.has(d.id) ? 1 : 0.15);
  }}

  function resetHighlight() {{
    links.classed('highlighted', false).classed('dimmed', false);
    nodeGroups.style('opacity', 1);
  }}

  nodeGroups.on('mouseover', (event, d) => {{
    highlightNode(d.id);
    const pctH = d.total > 0 ? ((d.hermitage / d.total) * 100).toFixed(0) : 0;
    const hermW = d.total > 0 ? (d.hermitage / d.total) * 150 : 0;

    // Count connections
    const connCount = edges.filter(e => {{
      const sid = typeof e.source === 'object' ? e.source.id : e.source;
      const tid = typeof e.target === 'object' ? e.target.id : e.target;
      return sid === d.id || tid === d.id;
    }}).length;

    showTooltip(event, `
      <div class="tt-name">${{d.fullLabel}}</div>
      <div class="tt-count">${{d.total.toLocaleString()}} artifacts</div>
      <div class="tt-bar">
        <div class="tt-bar-herm" style="width:${{hermW}}px"></div>
        <div class="tt-bar-shm" style="flex:1"></div>
      </div>
      <div><span style="color:#4ade80">■</span> Hermitage: ${{d.hermitage.toLocaleString()}}</div>
      <div><span style="color:#60a5fa">■</span> SHM: ${{d.shm.toLocaleString()}}</div>
      <div class="tt-detail">Connected to ${{connCount}} other collections via shared time periods</div>
    `);
  }})
  .on('mouseout', () => {{ resetHighlight(); hideTooltip(); }});
}}

// ============== MODE SWITCHING ==============
document.getElementById('btnBipartite').addEventListener('click', function() {{
  currentMode = 'bipartite';
  document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
  this.classList.add('active');
  drawBipartite();
}});

document.getElementById('btnTransposed').addEventListener('click', function() {{
  currentMode = 'transposed';
  document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
  this.classList.add('active');
  drawTransposed();
}});

// Initial draw
drawBipartite();

// Resize
window.addEventListener('resize', () => {{
  const w = window.innerWidth;
  const h = window.innerHeight - 110;
  svg.attr('viewBox', `0 0 ${{w}} ${{h}}`);
  if (currentMode === 'bipartite') drawBipartite();
  else drawTransposed();
}});
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
    edges, coll_totals, date_totals, coll_museums = read_data(input_file)

    if not edges:
        print("No data found!")
        sys.exit(1)

    print("\nBuilding transposed network...")
    coll_edges = build_transposed(edges, coll_totals)

    print("\nGenerating visualization...")
    html = generate_html(edges, coll_totals, date_totals, coll_museums, coll_edges)

    output_file = 'bipartite_network.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\nSaved: {output_file}")
    print("Open in a browser!")


if __name__ == '__main__':
    main()
