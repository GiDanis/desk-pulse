import math

w = 104.0
d = 77.0
angle = 6.0 # degrees
tan_a = math.tan(math.radians(angle))
delta_z = d * tan_a

print(f"Case Width: {w} mm")
print(f"Case Depth: {d} mm")
print(f"Tilt Angle: {angle} deg")
print(f"Delta Z rise over {d} mm: {delta_z:.3f} mm")
print(f"Front lid height: 4.0 mm -> Rear lid height: {4.0 + delta_z:.3f} mm")
print(f"Total front height: {20.0 + 4.0:.1f} mm -> Total rear height: {20.0 + 4.0 + delta_z:.1f} mm")
