"""Isolated geometry/analytic audit. Never opens a driver store or trains policies.

Run from any directory with the project's NumPy runtime. JSON and SVG are
analysis evidence, not race qualification or board performance measurements.
"""
from pathlib import Path
import hashlib
import json
import math
import sys

HERE = Path(__file__).resolve().parent
DASHBOARD = HERE.parents[2]
sys.path.insert(0, str(DASHBOARD))
import numpy as np
from game_catalog import VEHICLE, TRACKS
from game_geometry import get_track
from game_simulation import World, vertices, overlap

edge, gap = 0.75, 0.75  # Proposed engineering reserves, not FIA requirements.
spaces = []
for angle in (0, 15, 30):
    transverse = VEHICLE.width * math.cos(math.radians(angle)) + VEHICLE.length * math.sin(math.radians(angle))
    for count in (2, 3, 4):
        spaces.append(dict(angle_deg=angle, cars=count, transverse_body_m=transverse,
                           required_width_m=count*transverse+(count-1)*gap+2*edge))

tracks = []
for item in TRACKS:
    t = get_track(item['id'])
    world = World(4, shared=True, track_id=t.id)
    bodies = vertices(world.state)
    pairs = [[i, j] for i in range(4) for j in range(i+1, 4) if overlap(bodies[i], bodies[j])]
    if t.oval:
        from game_simulation import road_distance
        d = road_distance(bodies)
        boundary_hit = ((d < t.spec['radius']-t.width/2) | (d > t.spec['radius']+t.width/2)).any(axis=1)
        scale = min(912/152, 496/82.6666667)
    else:
        boundary_hit = [t.contact(body) for body in bodies]
        scale = min((912-24)/(np.ptp(t.bounds[:, 0])+8), (496-24)/(np.ptp(t.bounds[:, 1])+8))
    tracks.append(dict(id=t.id, length_m=t.length, road_width_m=t.width,
                       overview_px_per_m=scale,
                       overview_body_px=[VEHICLE.length*scale, VEHICLE.width*scale],
                       overview_selected_outline_px=[VEHICLE.length*scale+10, VEHICLE.width*scale+10],
                       grid_4_pose=world.state[:, :3].tolist(),
                       grid_4_overlapping_pairs=pairs,
                       grid_4_boundary_contact=np.asarray(boundary_hit).tolist()))

braking = []
for mu in (0.95, 0.55):
    for kmh in (90, 120, 160):
        v = kmh/3.6
        braking.append(dict(kmh=kmh, assumed_mu=mu,
                            constant_mu_braking_m=v*v/(2*mu*9.81),
                            reserve_0_3_s_m=0.3*v,
                            total_m=v*v/(2*mu*9.81)+0.3*v))

source_files = ('game_catalog.py', 'game_geometry.py', 'game_simulation.py',
                'game_profiles.py', 'game_curriculum.py', 'game_worker.py',
                'presentations/GameVisual.qml')
result = dict(date='2026-10-12', kind='static_geometry_and_analytic_estimates',
              measured_on='PC, no board benchmark or training',
              vehicle=dict(length_m=VEHICLE.length, width_m=VEHICLE.width,
                           wheelbase_m=VEHICLE.wheelbase, mass_kg=VEHICLE.mass),
              assumptions=dict(edge_reserve_m=edge, inter_body_gap_m=gap,
                               speed_reserve_s=0.3, wet_example_mu=0.55,
                               arena_px=[912, 496]),
              spaces=spaces, tracks=tracks, braking_estimates=braking,
              source_sha256={p: hashlib.sha256((DASHBOARD/p).read_bytes()).hexdigest() for p in source_files})
(HERE/'audit.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')

# SI-scale schematic: physical bodies rotated relative to the road, no halos.
svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="620" viewBox="0 0 1000 620">',
       '<rect width="1000" height="620" fill="#f5f7fa"/>',
       '<style>text{font-family:Arial,sans-serif;fill:#17212d}.small{font-size:15px}.title{font-size:23px;font-weight:bold}</style>',
       '<text x="32" y="38" class="title">Spazio per affiancarsi · strada 12 m · auto 4,4 × 1,8 m</text>',
       '<text x="32" y="65" class="small">Riserve proposte: 0,75 m tra carrozzerie e 0,75 m per ciascun bordo.</text>']
for index, (count, angle) in enumerate(((2, 0), (3, 0), (2, 15), (3, 15))):
    x0, y0 = 60+(index%2)*490, 112+(index//2)*238
    scale = 30
    transverse = VEHICLE.width*math.cos(math.radians(angle))+VEHICLE.length*math.sin(math.radians(angle))
    pack = count*transverse+(count-1)*gap
    required = pack+2*edge
    svg.extend([f'<text x="{x0}" y="{y0-15}" font-size="18">{count} auto · angolo {angle}° · spazio {required:.2f} m</text>',
                f'<rect x="{x0}" y="{y0}" width="360" height="166" fill="#e0e5eb" stroke="#5a6673"/>'])
    for e in (edge, 12-edge):
        xx=x0+e*scale
        svg.append(f'<path d="M{xx},{y0} V{y0+166}" stroke="#8693a2" stroke-dasharray="4 4"/>')
    for i in range(count):
        cx=x0+(6-pack/2+transverse/2+i*(transverse+gap))*scale
        cy=y0+83
        svg.append(f'<rect x="{cx-27}" y="{cy-66}" width="54" height="132" rx="5" fill="{("#4577a6", "#619276", "#b78249")[i]}" transform="rotate({angle},{cx},{cy})"/>')
    svg.append(f'<text x="{x0}" y="{y0+190}" class="small">Margine totale residuo su 12 m: {12-required:.2f} m</text>')
svg.extend(['<text x="32" y="590" class="small">Schema geometrico: non prova aderenza, traiettoria praticabile in curva o capacità del pilota di sorpassare.</text>', '</svg>'])
(HERE/'passing-space.svg').write_text('\n'.join(svg)+'\n')
print(json.dumps(result, indent=2))
