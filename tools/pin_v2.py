#!/usr/bin/env python3
"""NinthKart / Maya More pin designs v2 (28 Sep 2026).

Pinterest-native layouts that use REAL product pages (never AI-drawn pages):

  M  mockup     real page composited (multiply blend) onto a photo scene with a blank sheet
                (desk / clipboard / fridge / marble). Scene + paper box come from bg/scenes.json.
  Z  zoom       one month page large, with a magnifier bubble on a marked holiday cell
                ("already marked") and a handwritten note.
  N  big year   huge "2027" poster type, the year page overlapping the numerals.
  F  fan        3-5 real pages fanned out, stat sticker ("13 pages", "17 PDFs").
  I  info       value pin: a list (long weekends, bridge days, ...) with dates in chips and
                the product as a small card at the bottom. Built to be saved.

Spec keys (JSON):
  layout, hook (big 2-6 word line), kicker (small keyword line), images (paths),
  price, cta, palette (name from PALETTES) or accent/bg/ink hex overrides,
  scene (M: scene id in scenes.json), stat (F: e.g. ["13", "pages"]),
  note (Z: handwritten text), zoom_color (Z: hex of the holiday mark colour to find),
  items (I: list of [chip, label]), card_title (I), year (N, default "2027"),
  footer (small line under the product: formats etc.)

No logo is drawn. Text stays inside a 48 px margin; there is no dead bottom band.
"""
import json, os, sys, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageChops

W, H = 1000, 1500
M = 48
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, 'fonts')

FONTS = {
    'anton': 'Anton-Regular.ttf', 'bebas': 'BebasNeue-Regular.ttf', 'archivo': 'ArchivoBlack-Regular.ttf',
    'dmserif': 'DMSerifDisplay-Regular.ttf', 'playfair': 'PlayfairDisplay.ttf', 'caveat': 'Caveat.ttf',
    'dmsans': 'DMSans.ttf', 'fraunces': 'Fraunces.ttf',
    'poppins': 'Poppins-Regular.ttf', 'poppins-medium': 'Poppins-Medium.ttf',
    'poppins-semibold': 'Poppins-SemiBold.ttf', 'poppins-bold': 'Poppins-Bold.ttf',
}
FONT_URLS = {
    'Anton-Regular.ttf': 'anton/Anton-Regular.ttf', 'BebasNeue-Regular.ttf': 'bebasneue/BebasNeue-Regular.ttf',
    'ArchivoBlack-Regular.ttf': 'archivoblack/ArchivoBlack-Regular.ttf',
    'DMSerifDisplay-Regular.ttf': 'dmserifdisplay/DMSerifDisplay-Regular.ttf',
    'PlayfairDisplay.ttf': 'playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf', 'Caveat.ttf': 'caveat/Caveat%5Bwght%5D.ttf',
    'DMSans.ttf': 'dmsans/DMSans%5Bopsz,wght%5D.ttf', 'Fraunces.ttf': 'fraunces/Fraunces%5BSOFT,WONK,opsz,wght%5D.ttf',
    'Poppins-Regular.ttf': 'poppins/Poppins-Regular.ttf', 'Poppins-Medium.ttf': 'poppins/Poppins-Medium.ttf',
    'Poppins-SemiBold.ttf': 'poppins/Poppins-SemiBold.ttf', 'Poppins-Bold.ttf': 'poppins/Poppins-Bold.ttf',
}

# Curated palettes: bg, ink (text), accent (main colour), pop (second colour), soft (tint)
PALETTES = {
    'terracotta': dict(bg='#F4EADF', ink='#2B211C', accent='#C4553A', pop='#F2B84B', soft='#EBD5C3'),
    'sage':       dict(bg='#E9EEE6', ink='#1E2B22', accent='#56785F', pop='#E7A95A', soft='#D3DECF'),
    'navy':       dict(bg='#EDF1F7', ink='#14203A', accent='#26466E', pop='#F08C6B', soft='#D5DEEC'),
    'blush':      dict(bg='#F9EAE6', ink='#3A2330', accent='#B5557A', pop='#2F5670', soft='#F1D3CF'),
    'mustard':    dict(bg='#FFF5DD', ink='#1F1F1F', accent='#D99A1E', pop='#2C4A63', soft='#F6E3B3'),
    'teal':       dict(bg='#E5F1F0', ink='#0F2F2D', accent='#1F6F78', pop='#F08A5D', soft='#CBE3E1'),
    'forest':     dict(bg='#F2EFE6', ink='#15261C', accent='#234B35', pop='#E3A33B', soft='#DDE3D4'),
    'plum':       dict(bg='#F3EDF5', ink='#241631', accent='#5B2A86', pop='#F1C04E', soft='#E1D3EA'),
    'tomato':     dict(bg='#FFF1EA', ink='#231815', accent='#E4572E', pop='#1F4E5F', soft='#FAD7C8'),
    'maroon':     dict(bg='#FBF3E6', ink='#3A0F1F', accent='#7A1F3D', pop='#D9A441', soft='#F1DFC4'),
}


def rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def font(name, size, weight=None):
    fn = FONTS.get(name, name)
    p = os.path.join(FONT_DIR, fn)
    if not os.path.exists(p) and fn in FONT_URLS:
        try:
            import urllib.request
            os.makedirs(FONT_DIR, exist_ok=True)
            data = urllib.request.urlopen('https://raw.githubusercontent.com/google/fonts/main/ofl/' + FONT_URLS[fn], timeout=30).read()
            open(p, 'wb').write(data)
        except Exception:
            pass
    try:
        f = ImageFont.truetype(p, size)
    except Exception:
        return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', size)
    if weight:
        try:
            f.set_variation_by_axes([weight] + ([] if 'Fraunces' not in fn and 'DMSans' not in fn else []))
        except Exception:
            try:
                f.set_variation_by_name(weight if isinstance(weight, str) else 'Bold')
            except Exception:
                pass
    return f


def vfont(name, size, wght):
    """Variable font at a given weight (DM Sans / Playfair / Caveat / Fraunces)."""
    f = font(name, size)
    try:
        axes = f.get_variation_axes()
        vals = []
        for a in axes:
            tag = a.get('name', b'')
            tag = tag.decode() if isinstance(tag, bytes) else str(tag)
            if 'eight' in tag or tag.lower().startswith('wght'):
                vals.append(max(a['minimum'], min(a['maximum'], wght)))
            elif 'ptical' in tag or tag.lower().startswith('opsz'):
                vals.append(a['maximum'])
            else:
                vals.append(a.get('default', a['minimum']))
        f.set_variation_by_axes(vals)
    except Exception:
        pass
    return f


def pal(spec):
    p = dict(PALETTES.get(spec.get('palette', 'terracotta'), PALETTES['terracotta']))
    for k in ('bg', 'ink', 'accent', 'pop', 'soft'):
        if spec.get(k):
            p[k] = spec[k]
    return {k: rgb(v) for k, v in p.items()}


def _longest_run(mask1d):
    best, cur, start, bs = 0, 0, 0, 0
    for i, v in enumerate(mask1d):
        if v:
            if cur == 0:
                start = i
            cur += 1
            if cur > best:
                best, bs = cur, start
        else:
            cur = 0
    return bs, bs + best


def crop_page(im):
    """Crop a preview mockup (light bg + white sheet) down to the white sheet (largest block)."""
    import numpy as np
    im = im.convert('RGB')
    a = np.asarray(im).astype(int)
    white = (a.min(2) >= 250)
    def close(m, gap=40):
        m = m.copy()
        idx = np.where(m)[0]
        for a_, b_ in zip(idx[:-1], idx[1:]):
            if 1 < b_ - a_ <= gap:
                m[a_:b_] = True
        return m
    x0, x1 = _longest_run(close(white.mean(0) > 0.12))
    y0, y1 = _longest_run(close(white[:, x0:x1].mean(1) > 0.12))
    x0, x1 = _longest_run(close(white[y0:y1, :].mean(0) > 0.12))
    area = (x1 - x0) * (y1 - y0)
    if area < 0.15 * im.width * im.height or area > 0.97 * im.width * im.height:
        return im
    return im.crop((int(x0), int(y0), int(x1), int(y1)))


def fit(img, mw, mh):
    r = min(mw / img.width, mh / img.height)
    return img.resize((max(1, round(img.width * r)), max(1, round(img.height * r))), Image.LANCZOS)


def cover(img, w, h):
    r = max(w / img.width, h / img.height)
    im = img.resize((math.ceil(img.width * r), math.ceil(img.height * r)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def shadow_paste(canvas, img, xy, blur=22, off=(0, 18), alpha=90, rot=0):
    """Paste img (RGB/RGBA) at xy (top-left of the unrotated box centre-anchored) with a soft shadow."""
    im = img.convert('RGBA')
    if rot:
        im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    pad = blur * 3
    sh = Image.new('RGBA', (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    a = im.getchannel('A').point(lambda v: alpha if v > 10 else 0)
    blk = Image.new('RGBA', im.size, (0, 0, 0, 255))
    blk.putalpha(a)
    sh.alpha_composite(blk, (pad + off[0], pad + off[1]))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    x, y = int(xy[0]), int(xy[1])
    canvas.alpha_composite(sh, (x - pad, y - pad))
    canvas.alpha_composite(im, (x, y))
    return (x, y, x + im.width, y + im.height)


def wrap(d, text, f, maxw):
    out = []
    for para in text.split('\n'):
        cur = ''
        for w in [x for x in para.split(' ') if x]:
            t = (cur + ' ' + w).strip()
            if d.textlength(t, font=f) <= maxw or not cur:
                cur = t
            else:
                out.append(cur)
                cur = w
        out.append(cur)
    return out


def fit_text(d, text, fname, maxw, maxh, start, minsize=40, lh=1.0, maxlines=4, upper=False, wght=None):
    t = text.upper() if upper else text
    size = start
    while size >= minsize:
        f = vfont(fname, size, wght) if wght else font(fname, size)
        lines = wrap(d, t, f, maxw)
        th = len(lines) * size * lh
        if len(lines) <= maxlines and th <= maxh and all(d.textlength(l, font=f) <= maxw for l in lines):
            return f, lines, size
        size -= 3
    f = vfont(fname, minsize, wght) if wght else font(fname, minsize)
    return f, wrap(d, t, f, maxw), minsize


def draw_lines(d, lines, f, size, x, y, fill, anchor='mt', lh=1.0, spacing_px=None):
    step = spacing_px or int(size * lh)
    for i, l in enumerate(lines):
        d.text((x, y + i * step), l, font=f, fill=fill, anchor=anchor)
    return y + len(lines) * step


def sticker(canvas, text1, text2, cx, cy, r, bg, fg, rot=-10, f1='anton', f2='poppins-semibold'):
    s = Image.new('RGBA', (r * 2 + 20, r * 2 + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    # scalloped badge
    n = 18
    pts = []
    for i in range(n * 2):
        ang = math.pi * i / n
        rr = r if i % 2 == 0 else r * 0.9
        pts.append((r + 10 + rr * math.cos(ang), r + 10 + rr * math.sin(ang)))
    d.polygon(pts, fill=bg)
    if text2:
        fa = font(f1, int(r * 0.62))
        fb = font(f2, int(r * 0.24))
        d.text((r + 10, r + 10 - r * 0.12), text1, font=fa, fill=fg, anchor='mm')
        d.text((r + 10, r + 10 + r * 0.42), text2, font=fb, fill=fg, anchor='mm')
    else:
        fa = font(f1, int(r * (0.58 if len(text1) <= 5 else 0.46)))
        d.text((r + 10, r + 10), text1, font=fa, fill=fg, anchor='mm')
    s = s.rotate(rot, resample=Image.BICUBIC)
    shadow_paste(canvas, s, (cx - s.width / 2, cy - s.height / 2), blur=10, off=(0, 6), alpha=60)


def pill(d, text, cx, y, bg, fg, fname='poppins-semibold', size=34, padx=34, h=None, anchor='center'):
    f = font(fname, size)
    w = d.textlength(text, font=f) + padx * 2
    h = h or size + 34
    x = cx - w / 2 if anchor == 'center' else cx
    d.rounded_rectangle([x, y, x + w, y + h], radius=h / 2, fill=bg)
    d.text((x + w / 2, y + h / 2 + 1), text, font=f, fill=fg, anchor='mm')
    return (x, y, x + w, y + h)


def arrow(d, x, y, size, color):
    """Draw a right arrow starting at x, centred on y (fonts lack the glyph)."""
    w = size * 0.9
    t = max(3, int(size * 0.11))
    d.line([(x, y), (x + w, y)], fill=color, width=t)
    d.line([(x + w - size * 0.34, y - size * 0.3), (x + w, y), (x + w - size * 0.34, y + size * 0.3)], fill=color, width=t, joint='curve')
    return x + w


def cta_line(d, p, text, y, price=None, dark=False):
    """Bottom CTA: price chip + arrow text, compact (no empty band)."""
    fg = p['bg'] if dark else p['ink']
    f = font('poppins-semibold', 36)
    parts_w = d.textlength(text, font=f) + 58
    pw = 0
    if price:
        fp = font('poppins-bold', 36)
        pw = d.textlength(price, font=fp) + 56 + 22
    x = (W - (parts_w + pw)) / 2
    if price:
        d.rounded_rectangle([x, y, x + pw - 22, y + 66], radius=33, fill=p['accent'])
        d.text((x + (pw - 22) / 2, y + 34), price, font=fp, fill=(255, 255, 255), anchor='mm')
        x += pw
    d.text((x, y + 34), text, font=f, fill=fg, anchor='lm')
    arrow(d, x + d.textlength(text, font=f) + 18, y + 35, 36, fg)


def load_pages(spec):
    out = []
    for pth in spec['images']:
        im = Image.open(pth)
        out.append(crop_page(im) if spec.get('crop', True) else im.convert('RGB'))
    return out


def scenes_manifest():
    for c in (os.path.join(HERE, '..', 'bg', 'scenes.json'), os.path.join(HERE, 'bg', 'scenes.json'),
              os.path.join(os.getcwd(), 'bg', 'scenes.json')):
        if os.path.exists(c):
            return json.load(open(c)), os.path.dirname(os.path.abspath(c))
    return {}, os.getcwd()


# ------------------------------------------------------------------ M: mockup
def build_M(spec, p, pages):
    scenes, base = scenes_manifest()
    sc = spec.get('scene_data') or scenes.get(spec.get('scene', ''), {})
    scene_path = spec.get('background') or os.path.join(base, sc.get('file', ''))
    scene = cover(Image.open(scene_path).convert('RGB'), W, H)
    x0, y0, x1, y1 = sc['paper']
    page = pages[0]
    # paper orientation vs page orientation
    pw, ph = x1 - x0, y1 - y0
    inset = sc.get('inset', 0.0)
    pg = fit(page, pw * (1 - inset), ph * (1 - inset))
    layer = Image.new('RGB', (W, H), (255, 255, 255))
    layer.paste(pg, (int(x0 + (pw - pg.width) / 2), int(y0 + (ph - pg.height) / 2)))
    comp = ImageChops.multiply(scene, layer).convert('RGBA')
    d = ImageDraw.Draw(comp)
    # headline area: above the paper if room, else a card
    top_room = y0 - M
    hook = spec['hook']
    if top_room >= 230:
        band = Image.new('RGBA', (W, int(y0 - 24)), p['bg'] + (238,))
        comp.alpha_composite(band, (0, 0))
        f, lines, size = fit_text(d, hook, spec.get('hook_font', 'dmserif'), W - 2 * M, top_room - 110, 118, 56, lh=1.0, maxlines=2)
        y = draw_lines(d, lines, f, size, W / 2, M + 4, p['ink'], lh=1.0)
        if spec.get('kicker'):
            fk = font('poppins-semibold', 32)
            d.text((W / 2, y + 18), spec['kicker'].upper(), font=fk, fill=p['accent'], anchor='mt')
    else:
        card_w = W - 2 * M
        f, lines, size = fit_text(d, hook, spec.get('hook_font', 'dmserif'), card_w - 80, 230, 104, 52, maxlines=2)
        ch = len(lines) * size + (70 if spec.get('kicker') else 0) + 70
        card = Image.new('RGBA', (card_w, int(ch)), p['bg'] + (240,))
        cm = Image.new('L', card.size, 0)
        ImageDraw.Draw(cm).rounded_rectangle([0, 0, card.width, card.height], radius=34, fill=255)
        comp.paste(card, (M, M), cm)
        d = ImageDraw.Draw(comp)
        y = draw_lines(d, lines, f, size, W / 2, M + 36, p['ink'])
        if spec.get('kicker'):
            d.text((W / 2, y + 12), spec['kicker'].upper(), font=font('poppins-semibold', 30), fill=p['accent'], anchor='mt')
    # price sticker near paper top-right
    if spec.get('price'):
        sticker(comp, spec['price'], None, min(x1 + 10, W - 110), max(y0 + 40, 330) if top_room >= 230 else y0 + 80, 92, p['pop'], p['ink'], rot=-12)
    # bottom label
    if spec.get('footer') or spec.get('cta'):
        txt = spec.get('footer') or spec.get('cta')
        fb = font('poppins-semibold', 32)
        tw = d.textlength(txt, font=fb) + 70
        yb = H - M - 70
        lab = Image.new('RGBA', (int(tw), 70), (255, 255, 255, 235))
        lm = Image.new('L', lab.size, 0)
        ImageDraw.Draw(lm).rounded_rectangle([0, 0, lab.width, lab.height], radius=35, fill=255)
        comp.paste(lab, (int((W - tw) / 2), yb), lm)
        d = ImageDraw.Draw(comp)
        d.text((W / 2, yb + 36), txt, font=fb, fill=p['ink'], anchor='mm')
    return comp.convert('RGB')


# ------------------------------------------------------------------ Z: zoom
def find_mark(page, color, tol=60):
    import numpy as np
    a = np.asarray(page.convert('RGB')).astype(int)
    c = np.array(color)
    dist = np.abs(a - c).sum(2)
    sat = a.max(2) - a.min(2)
    m = (dist < tol) & (sat >= max(12, int((max(color) - min(color)) * 0.5)))
    if m.sum() < 30:
        # fallback: most saturated warm pixels
        mx, mn = a.max(2), a.min(2)
        m = ((mx - mn) > 90) & (a[:, :, 0] > a[:, :, 2])
    ys, xs = np.where(m)
    if len(xs) == 0:
        return page.width * 0.3, page.height * 0.4
    # densest cell: histogram on a coarse grid
    gx, gy = (xs // 60), (ys // 60)
    key = gx * 10000 + gy
    vals, counts = np.unique(key, return_counts=True)
    k = vals[counts.argmax()]
    cx, cy = (k // 10000) * 60 + 30, (k % 10000) * 60 + 30
    sel = (np.abs(xs - cx) < 160) & (np.abs(ys - cy) < 120)
    return float(xs[sel].mean()), float(ys[sel].mean())


def build_Z(spec, p, pages):
    canvas = Image.new('RGBA', (W, H), p['bg'] + (255,))
    d = ImageDraw.Draw(canvas)
    # soft blob
    blob = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(blob).ellipse([-260, 820, 700, 1780], fill=p['soft'] + (255,))
    canvas.alpha_composite(blob)
    d = ImageDraw.Draw(canvas)
    f, lines, size = fit_text(d, spec['hook'], spec.get('hook_font', 'archivo'), W - 2 * M, 300, 104, 54, lh=1.04, maxlines=3)
    y = draw_lines(d, lines, f, size, W / 2, M + 10, p['ink'], lh=1.04)
    if spec.get('kicker'):
        d.text((W / 2, y + 14), spec['kicker'], font=font('poppins-medium', 34), fill=p['accent'], anchor='mt')
        y += 60
    page = pages[0]
    pg = fit(page, W - 2 * M - 10, 560)
    px, py = (W - pg.width) / 2, y + 40
    shadow_paste(canvas, pg, (px, py))
    # magnifier
    zc = rgb(spec.get('zoom_color', '#E07A36'))
    if spec.get('zoom_at'):
        mx, my = spec['zoom_at'][0] * page.width, spec['zoom_at'][1] * page.height
    else:
        mx, my = find_mark(page, zc)
    s = pg.width / page.width
    tx, ty = px + mx * s, py + my * s
    R = 190
    src_r = page.width * 0.085
    box = [int(mx - src_r * 1.25), int(my - src_r * 0.9), int(mx + src_r * 1.25), int(my + src_r * 1.6)]
    padded = Image.new('RGB', (page.width + 2000, page.height + 2000), (255, 255, 255))
    padded.paste(page.convert('RGB'), (1000, 1000))
    crop = padded.crop((box[0] + 1000, box[1] + 1000, box[2] + 1000, box[3] + 1000))
    crop = cover(crop, R * 2, R * 2)
    mask = Image.new('L', (R * 2, R * 2), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, R * 2, R * 2], fill=255)
    bub = Image.new('RGBA', (R * 2 + 24, R * 2 + 24), (0, 0, 0, 0))
    ImageDraw.Draw(bub).ellipse([0, 0, R * 2 + 24, R * 2 + 24], fill=(255, 255, 255, 255))
    ring = Image.new('RGBA', (R * 2, R * 2), (0, 0, 0, 0))
    ring.paste(crop.convert('RGBA'), (0, 0), mask)
    bub.alpha_composite(ring, (12, 12))
    ImageDraw.Draw(bub).ellipse([4, 4, R * 2 + 20, R * 2 + 20], outline=p['accent'], width=8)
    bx = W - M - bub.width + 10 if tx < W / 2 + 80 else M - 10
    by = py + pg.height - 60
    # connector
    d = ImageDraw.Draw(canvas)
    d.ellipse([tx - 34, ty - 26, tx + 34, ty + 26], outline=p['accent'], width=6)
    d.line([(tx, ty + 26), (bx + bub.width / 2, by + 10)], fill=p['accent'], width=6)
    shadow_paste(canvas, bub, (bx, by), blur=16, off=(0, 10), alpha=70)
    # handwritten note
    d = ImageDraw.Draw(canvas)
    note = spec.get('note', 'already marked!')
    fn = vfont('caveat', 70, 700)
    nx = M + 20 if bx > W / 2 else W - M - 20
    anchor = 'lm' if bx > W / 2 else 'rm'
    ny = by + bub.height * 0.45
    for i, l in enumerate(wrap(d, note, fn, W - bub.width - 2 * M - 20)[:3]):
        d.text((nx, ny + i * 70), l, font=fn, fill=p['ink'], anchor=anchor)
    # CTA
    cta_line(d, p, spec.get('cta', 'Instant download'), H - M - 70, spec.get('price'))
    if spec.get('footer'):
        d.text((W / 2, H - M - 96), spec['footer'], font=font('poppins-medium', 28), fill=p['ink'] + (170,), anchor='mb')
    return canvas.convert('RGB')


# ------------------------------------------------------------------ N: big year
def build_N(spec, p, pages):
    bgc = p['accent']
    canvas = Image.new('RGBA', (W, H), bgc + (255,))
    d = ImageDraw.Draw(canvas)
    year = spec.get('year', '2027')
    ys = 620
    while ys > 200 and d.textlength(year, font=font('anton', ys)) > W - 2 * M + 10:
        ys -= 10
    fy = font('anton', ys)
    ky = M - 4
    if spec.get('kicker'):
        d.text((W / 2, ky), spec['kicker'].upper(), font=font('poppins-semibold', 30), fill=p['pop'], anchor='mt')
        ky += 44
    d.text((W / 2, ky - int(ys * 0.06)), year, font=fy, fill=p['bg'], anchor='mt')
    page = pages[0]
    pg = fit(page, 660, 780)
    rot = spec.get('tilt', -4)
    box = shadow_paste(canvas, pg, ((W - pg.width) / 2 - 20, 430), blur=26, off=(0, 22), alpha=110, rot=rot)
    d = ImageDraw.Draw(canvas)
    y = box[3] + 30
    f, lines, size = fit_text(d, spec['hook'], spec.get('hook_font', 'dmserif'), W - 2 * M, H - y - 170, 84, 46, maxlines=2)
    y = draw_lines(d, lines, f, size, W / 2, y, p['bg'], lh=1.02)
    if spec.get('footer'):
        d.text((W / 2, y + 16), spec['footer'], font=font('poppins-medium', 32), fill=p['soft'], anchor='mt')
    if spec.get('price'):
        sticker(canvas, spec['price'], None, box[2] - 40, box[1] + 90, 96, p['pop'], p['ink'], rot=10)
    d = ImageDraw.Draw(canvas)
    f = font('poppins-semibold', 34)
    t = spec.get('cta', 'Instant download')
    tw = d.textlength(t, font=f) + 70 + 50
    x0 = (W - tw) / 2
    d.rounded_rectangle([x0, H - M - 72, x0 + tw, H - M], radius=36, fill=p['bg'])
    d.text((x0 + 35, H - M - 35), t, font=f, fill=p['accent'], anchor='lm')
    arrow(d, x0 + 35 + d.textlength(t, font=f) + 14, H - M - 35, 32, p['accent'])
    return canvas.convert('RGB')


# ------------------------------------------------------------------ F: fan
def build_F(spec, p, pages):
    canvas = Image.new('RGBA', (W, H), p['bg'] + (255,))
    d = ImageDraw.Draw(canvas)
    d.ellipse([W / 2 - 520, 560, W / 2 + 520, 1600], fill=p['soft'])
    f, lines, size = fit_text(d, spec['hook'], spec.get('hook_font', 'dmserif'), W - 2 * M, 290, 112, 56, maxlines=3)
    y = draw_lines(d, lines, f, size, W / 2, M + 6, p['ink'], lh=1.0)
    if spec.get('kicker'):
        d.text((W / 2, y + 14), spec['kicker'], font=font('poppins-medium', 34), fill=p['accent'], anchor='mt')
        y += 58
    imgs = (pages * 5)[:max(3, min(5, len(pages)))]
    n = len(imgs)
    rots = {3: [-11, 0, 11], 4: [-14, -5, 5, 14], 5: [-16, -8, 0, 8, 16]}[n]
    area_top = y + 70
    cw = 520 if imgs[0].width < imgs[0].height else 600
    for i, (im, r) in enumerate(zip(imgs, rots)):
        pg = fit(im, cw, 640)
        off = (i - (n - 1) / 2) * 120
        cx = W / 2 + off
        cy = area_top + 360 + abs(i - (n - 1) / 2) * 30
        rim = pg.convert('RGBA').rotate(r, expand=True, resample=Image.BICUBIC)
        shadow_paste(canvas, rim, (cx - rim.width / 2, cy - rim.height / 2), blur=18, off=(0, 14), alpha=80)
    if spec.get('stat'):
        s1, s2 = spec['stat']
        sticker(canvas, s1, s2, W - 170, area_top + 40, 118, p['accent'], (255, 255, 255), rot=8)
    d = ImageDraw.Draw(canvas)
    if spec.get('footer'):
        fb = font('poppins-semibold', 32)
        pill(d, spec['footer'], W / 2, H - M - 170, p['ink'], p['bg'], size=30)
    cta_line(d, p, spec.get('cta', 'Instant download'), H - M - 72, spec.get('price'))
    return canvas.convert('RGB')


# ------------------------------------------------------------------ I: info list
def build_I(spec, p, pages):
    canvas = Image.new('RGBA', (W, H), p['bg'] + (255,))
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, 0, W, 16], fill=p['accent'])
    if spec.get('kicker'):
        d.text((W / 2, M + 8), spec['kicker'].upper(), font=font('poppins-semibold', 30), fill=p['accent'], anchor='mt')
    f, lines, size = fit_text(d, spec['hook'], spec.get('hook_font', 'dmserif'), W - 2 * M, 250, 110, 56, maxlines=2)
    y = draw_lines(d, lines, f, size, W / 2, M + 60, p['ink'], lh=1.0)
    items = spec.get('items', [])[:12]
    card_h = 250 if pages else 0
    bottom_res = card_h + (0 if pages else 110)
    avail = H - y - 40 - bottom_res - M - 20
    n = max(1, len(items))
    rh = min(92 if pages else 200, avail / n)
    y += 36 if pages else max(36, (avail - rh * n) / 2 + 20)
    fchip = font('poppins-bold', int(min(rh * 0.36, 38)))
    chip_w = max(d.textlength(c, font=fchip) for c, _ in items) + 44 if items else 0
    lab_w = W - 2 * M - chip_w - 30
    for i, (chip, label) in enumerate(items):
        cy = y + i * rh
        size = int(min(rh * 0.38, 40))
        while True:
            flab = font('poppins-medium', size)
            ll = wrap(d, label, flab, lab_w)
            if (len(ll) * size * 1.2 <= rh * 0.86 and len(ll) <= 3) or size <= 22:
                break
            size -= 2
        ch = min(rh * 0.72, 76)
        d.rounded_rectangle([M, cy + (rh - ch) / 2, M + chip_w, cy + (rh + ch) / 2], radius=ch / 2, fill=p['accent'])
        d.text((M + chip_w / 2, cy + rh / 2), chip, font=fchip, fill=(255, 255, 255), anchor='mm')
        ty = cy + rh / 2 - (len(ll) - 1) * size * 0.6
        for j, l in enumerate(ll):
            d.text((M + chip_w + 26, ty + j * size * 1.2), l, font=flab, fill=p['ink'], anchor='lm')
        if i < len(items) - 1:
            d.line([(M + chip_w + 26, cy + rh), (W - M, cy + rh)], fill=p['soft'], width=2)
    if not pages:
        t = spec.get('cta', 'Read more')
        f = font('poppins-semibold', 36)
        tw = d.textlength(t, font=f) + 70 + 52
        x0 = (W - tw) / 2
        d.rounded_rectangle([x0, H - M - 76, x0 + tw, H - M], radius=38, fill=p['accent'])
        d.text((x0 + 35, H - M - 37), t, font=f, fill=(255, 255, 255), anchor='lm')
        arrow(d, x0 + 35 + d.textlength(t, font=f) + 14, H - M - 37, 34, (255, 255, 255))
    if pages:
        cy0 = H - M - card_h
        d.rounded_rectangle([M, cy0, W - M, H - M], radius=30, fill=p['soft'])
        th = fit(pages[0], 300, card_h - 50)
        shadow_paste(canvas, th, (M + 30, cy0 + (card_h - th.height) / 2), blur=10, off=(0, 6), alpha=70, rot=-3)
        d = ImageDraw.Draw(canvas)
        tx = M + 30 + th.width + 50
        ft = font('poppins-bold', 38)
        for j, l in enumerate(wrap(d, spec.get('card_title', 'Printable 2027 calendar'), ft, W - M - tx - 20)[:2]):
            d.text((tx, cy0 + 50 + j * 46), l, font=ft, fill=p['ink'])
        fl = font('poppins-medium', 30)
        yy = cy0 + 50 + min(2, len(wrap(d, spec.get('card_title', ''), ft, W - M - tx - 20))) * 46 + 10
        if spec.get('footer'):
            d.text((tx, yy), spec['footer'], font=fl, fill=p['ink'])
            yy += 44
        t = (spec.get('price', '') + '  ·  ' if spec.get('price') else '') + spec.get('cta', 'Instant download')
        fc = font('poppins-semibold', 32)
        d.text((tx, yy + 6), t, font=fc, fill=p['accent'])
        arrow(d, tx + d.textlength(t, font=fc) + 14, yy + 26, 30, p['accent'])
    return canvas.convert('RGB')


BUILDERS = {'M': build_M, 'Z': build_Z, 'N': build_N, 'F': build_F, 'I': build_I}


def build(spec):
    p = pal(spec)
    pages = load_pages(spec) if spec.get('images') else []
    return BUILDERS[spec['layout'].upper()](spec, p, pages)


if __name__ == '__main__':
    s = json.load(open(sys.argv[1]))
    build(s).save(sys.argv[2], optimize=True)
    print('saved', sys.argv[2])
