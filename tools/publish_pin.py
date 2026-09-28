"""Runs inside COMPOSIO_REMOTE_WORKBENCH (needs its run_composio_tool helper).

Usage in a workbench cell:
    import urllib.request
    exec(urllib.request.urlopen('https://raw.githubusercontent.com/webhorse-studio/ninthkart-pins/main/tools/publish_pin.py').read())
    result = render_pin(spec, name)          # render + archive only (dry run)
    result = publish_pin(spec, meta, name)   # render + archive + create the Pinterest pin

spec: a pin spec. "images" are raw.githubusercontent.com URLs (downloaded here).
  v2 layouts (M, Z, N, F, I) are rendered by tools/pin_v2.py; old layouts (A-E, L) by tools/pin_maker.py.
  Layout M: pass "scene": "<id from bg/scenes.json>" (scene file + paper box are fetched here).
meta: {"board_id", "title", "description", "alt_text", "link"}
name: file stem for the archive copy, e.g. "2026-09-29-printable-calendar-2027-M"
"""
import base64, json, os, urllib.request, hashlib, time

RAW = 'https://raw.githubusercontent.com/webhorse-studio/ninthkart-pins/main/'
WORK = '/home/user/nk/pins'
os.makedirs(WORK, exist_ok=True)
V2 = ('M', 'Z', 'N', 'F', 'I')


def _get(url, dest, fresh=False):
    if fresh or not os.path.exists(dest):
        sep = '&' if '?' in url else '?'
        u = url + (sep + 't=%d' % time.time() if fresh else '')
        with urllib.request.urlopen(u, timeout=60) as r:
            open(dest, 'wb').write(r.read())
    return dest


def _load(tool):
    p = _get(RAW + 'tools/' + tool + '.py', os.path.join(WORK, tool + '.py'), fresh=True)
    ns = {'__file__': p, '__name__': tool}
    exec(open(p).read(), ns)
    return ns


def render_pin(spec, name, archive=True):
    layout = spec.get('layout', 'A').upper()
    local = []
    for u in spec.get('images', []):
        fn = os.path.join(WORK, hashlib.md5(u.encode()).hexdigest()[:10] + '_' + u.split('/')[-1].split('?')[0])
        local.append(_get(u, fn))
    s = dict(spec, images=local)
    if spec.get('background', '').startswith('http'):
        u = spec['background']
        s['background'] = _get(u, os.path.join(WORK, 'bg_' + hashlib.md5(u.encode()).hexdigest()[:10] + '.png'))
    if layout == 'M' and spec.get('scene') and not spec.get('scene_data'):
        scenes = json.load(open(_get(RAW + 'bg/scenes.json', os.path.join(WORK, 'scenes.json'), fresh=True)))
        sc = scenes[spec['scene']]
        s['scene_data'] = sc
        s['background'] = _get(RAW + 'bg/' + sc['file'], os.path.join(WORK, 'scene_' + sc['file']))
    mod = _load('pin_v2' if layout in V2 else 'pin_maker')
    img = mod['build'](s)
    out = os.path.join(WORK, name + '.png')
    img.save(out, optimize=True)
    data = open(out, 'rb').read()
    b64 = base64.b64encode(data).decode()
    arch, err = None, None
    if archive:
        r, err = run_composio_tool('GITHUB_CREATE_OR_UPDATE_FILE_CONTENTS', {
            'owner': 'webhorse-studio', 'repo': 'ninthkart-pins', 'branch': 'main',
            'path': f'pins/{name}.png', 'message': f'Pin image {name}', 'content': b64})
        arch = RAW + f'pins/{name}.png' if not err else None
    return {'file': out, 'bytes': len(data), 'size': img.size, 'archive_url': arch, 'archive_error': err, 'b64': b64}


def publish_pin(spec, meta, name):
    res = render_pin(spec, name)
    args = {'board_id': meta['board_id'], 'title': meta['title'][:100], 'description': meta['description'][:800],
            'alt_text': meta['alt_text'][:500], 'link': meta['link'],
            'media_source': {'source_type': 'image_base64', 'content_type': 'image/png', 'data': res['b64']}}
    r, e = run_composio_tool('PINTEREST_CREATE_PIN', args)
    pin_id = None
    if not e and isinstance(r, dict):
        d = r.get('data') or {}
        if isinstance(d, dict):
            pin_id = d.get('id') or (d.get('data') or {}).get('id')
    res.pop('b64')
    res.update({'pin_id': pin_id, 'pin_error': e, 'pin_response_keys': list(r.keys()) if isinstance(r, dict) else str(r)[:300]})
    if not pin_id and isinstance(r, dict):
        res['pin_response_preview'] = json.dumps(r)[:800]
    return res
