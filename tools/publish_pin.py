"""Runs inside COMPOSIO_REMOTE_WORKBENCH (needs its run_composio_tool helper).

Usage in a workbench cell:
    import urllib.request
    exec(urllib.request.urlopen('https://raw.githubusercontent.com/webhorse-studio/ninthkart-pins/main/tools/publish_pin.py').read())
    result = render_pin(spec, name)          # render + archive only (dry run)
    result = publish_pin(spec, meta, name)   # render + archive + create the Pinterest pin

spec: pin_maker spec, but "images" are raw.githubusercontent.com URLs (downloaded here).
meta: {"board_id", "title", "description", "alt_text", "link"}
name: file stem for the archive copy, e.g. "2026-09-27-kalender-2027-A"
"""
import base64, json, os, urllib.request, hashlib

RAW = 'https://raw.githubusercontent.com/webhorse-studio/ninthkart-pins/main/'
WORK = '/home/user/nk/pins'
os.makedirs(WORK, exist_ok=True)


def _get(url, dest):
    if not os.path.exists(dest):
        with urllib.request.urlopen(url, timeout=30) as r:
            open(dest, 'wb').write(r.read())
    return dest


def _pin_maker():
    p = _get(RAW + 'tools/pin_maker.py?nocache', os.path.join(WORK, 'pin_maker.py'))
    ns = {'__file__': p, '__name__': 'pin_maker'}
    exec(open(p).read(), ns)
    return ns


def render_pin(spec, name):
    pm = _pin_maker()
    local = []
    for u in spec['images']:
        fn = os.path.join(WORK, hashlib.md5(u.encode()).hexdigest()[:10] + '_' + u.split('/')[-1])
        local.append(_get(u, fn))
    s = dict(spec, images=local)
    if spec.get('background', '').startswith('http'):
        u = spec['background']
        s['background'] = _get(u, os.path.join(WORK, 'bg_' + hashlib.md5(u.encode()).hexdigest()[:10] + '.png'))
    out = os.path.join(WORK, name + '.png')
    img = pm['build'](s)
    img.save(out, optimize=True)
    data = open(out, 'rb').read()
    b64 = base64.b64encode(data).decode()
    r, e = run_composio_tool('GITHUB_CREATE_OR_UPDATE_FILE_CONTENTS', {
        'owner': 'webhorse-studio', 'repo': 'ninthkart-pins', 'branch': 'main',
        'path': f'pins/{name}.png', 'message': f'Pin image {name}', 'content': b64})
    archive = RAW + f'pins/{name}.png' if not e else None
    return {'file': out, 'bytes': len(data), 'size': img.size, 'archive_url': archive, 'archive_error': e, 'b64': b64}


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
