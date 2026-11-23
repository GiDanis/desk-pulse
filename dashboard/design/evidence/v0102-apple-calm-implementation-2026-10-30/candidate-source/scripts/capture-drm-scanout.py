#!/usr/bin/env python3
"""Read linear XR24 DRM scanout memory; this is not a panel photograph."""
import argparse
import ctypes as C
import fcntl
import hashlib
import json
import mmap
import os
from pathlib import Path
import re
import struct

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
state = Path('/sys/kernel/debug/dri/0/state').read_text()
match = re.search(r'\bfb=(\d+)', state)
if not match:
    raise SystemExit('No active framebuffer')
fb_id = int(match[1])

class Framebuffer(C.Structure):
    _fields_ = [('id', C.c_uint32), ('width', C.c_uint32), ('height', C.c_uint32),
                ('format', C.c_uint32), ('modifier', C.c_uint64), ('flags', C.c_uint32),
                ('handles', C.c_uint32 * 4), ('pitches', C.c_uint32 * 4), ('offsets', C.c_uint32 * 4)]

lib = C.CDLL('libdrm.so.2')
lib.drmModeGetFB2.argtypes = [C.c_int, C.c_uint32]
lib.drmModeGetFB2.restype = C.POINTER(Framebuffer)
lib.drmModeFreeFB2.argtypes = [C.POINTER(Framebuffer)]
fd = os.open('/dev/dri/card0', os.O_RDONLY | os.O_CLOEXEC)
fb = None
try:
    fb = lib.drmModeGetFB2(fd, fb_id)
    if not fb:
        raise RuntimeError('drmModeGetFB2 failed')
    f = fb.contents
    if (f.width, f.height, f.format, f.modifier, f.offsets[0]) != (960, 640, 0x34325258, 0, 0):
        raise RuntimeError('Unsupported scanout format: refuse to guess layout')
    mapping = bytearray(struct.pack('<IIQ', f.handles[0], 0, 0))
    fcntl.ioctl(fd, 0xc01064b3, mapping, True)
    offset = struct.unpack('<IIQ', mapping)[2]
    with mmap.mmap(fd, f.pitches[0] * f.height, flags=mmap.MAP_SHARED, prot=mmap.PROT_READ, offset=offset) as data:
        raw = data[:]
    (a.output / 'scanout.raw').write_bytes(raw)
    info = {'fb': fb_id, 'width': f.width, 'height': f.height, 'format': 'XR24',
            'modifier': f.modifier, 'pitch': f.pitches[0], 'sha256': hashlib.sha256(raw).hexdigest(),
            'scope': 'Read-only scanout memory, not physical-panel evidence; concurrent scanout may change'}
    (a.output / 'scanout.json').write_text(json.dumps(info, indent=2) + '\n')
    (a.output / 'drm-state.txt').write_text(state)
    print(json.dumps(info))
finally:
    if fb:
        lib.drmModeFreeFB2(fb)
    os.close(fd)
