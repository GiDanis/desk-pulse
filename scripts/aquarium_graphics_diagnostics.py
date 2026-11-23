"""Strict parsing of native Qt/EGL diagnostics, without calling the render thread."""
import json
from pathlib import Path
import re

MARKER = 'SMARTPC-QT|'

def scanout_content(raw, metadata):
    """Reject a uniform clear frame even if callbacks/context/health are valid.

    This checks scanout memory, never the physical panel or optical cadence.
    """
    width,height,pitch=(metadata[k] for k in ('width','height','pitch'))
    if metadata.get('format')!='XR24' or width<16 or height<16 or pitch<width*4 or pitch%4 or len(raw)!=height*pitch:
        raise ValueError('Unsupported or incomplete scanout layout')
    colors={}
    for y in range(0,height,max(1,height//40)):
        for x in range(0,width,max(1,width//60)):
            offset=y*pitch+x*4
            color=raw[offset:offset+3]
            colors[color]=colors.get(color,0)+1
    total=sum(colors.values());dominant=max(colors.values())/total
    result={'sampledPixels':total,'uniqueColors':len(colors),'dominantFraction':dominant,
            'scope':'Scanout content sanity only; not panel or optical FPS proof'}
    if len(colors)<16 or dominant>.98:
        raise ValueError('Blank or nearly uniform scanout despite healthy renderer: '+str(result))
    return result

def parse_qt_messages(text):
    records = []
    for line in text.splitlines():
        if line.startswith(MARKER):
            parts = line.split('|', 3)
            if len(parts) == 4:
                records.append({'severity':parts[1], 'category':parts[2], 'message':parts[3]})
                continue
        if records:
            records[-1]['message'] += '\n' + line
        elif line.strip():
            records.append({'severity':'unknown','category':'','message':line})
    return records

def read_native_context(path, pid, messages):
    if not path:
        raise ValueError('SMARTPC_GL_PROBE_FILE missing: preload the native EGL diagnostic')
    context = json.loads(Path(path).read_text())
    if context.get('pid') != pid or not all(context.get(k) for k in ('vendor','renderer','version','glsl','eglConfig')):
        raise ValueError('Actual GL context incomplete or from another process')
    versions = [re.search(r'Created OpenGL context QSurfaceFormat\(version (\d+)\.(\d+)', m['message'])
                for m in messages if m['category'] == 'qt.rhi.general']
    versions = [tuple(map(int, m.groups())) for m in versions if m]
    if not versions:
        raise ValueError('Actual Qt RHI context version missing')
    actual = re.search(r'^OpenGL ES (\d+)\.(\d+)', context['version'])
    if not actual or tuple(map(int, actual.groups())) < (3, 0) or versions[-1] < (3, 0):
        raise ValueError('Native skinned scene requires both driver and Qt RHI to recognize GLES >=3.0')
    if versions[-1] > tuple(map(int, actual.groups())):
        raise ValueError('Qt RHI reports a newer GLES version than the native context')
    if any(name in context['renderer'].lower() for name in ('llvmpipe','softpipe','software rasterizer')):
        raise ValueError('Software rendering cannot qualify the device hardware path')
    context['qtRhiVersion'] = list(versions[-1])
    return context
