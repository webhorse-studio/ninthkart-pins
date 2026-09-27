#!/usr/bin/env python3
"""NinthKart / Maya More Pinterest pin maker.

Builds a 1000x1500 product pin from REAL product preview images.
Usage:  python3 pin_maker.py spec.json out.png

spec.json keys:
  layout     "A" hero | "B" what's inside | "C" benefits | "D" localized/use-case | "E" seasonal
  headline   big headline, keyword phrase first (use "\n" to force a line break)
  subhead    one short line under the headline
  badges     list of 2-3 short strings (layouts A, D)
  benefits   list of 3 short strings (layout C)
  price      e.g. "$1.99"  (optional; omit to hide)
  cta        e.g. "Instant download"  (localize for non-English)
  images     list of local image paths (first = hero). Previews with a light
             background and a white page are auto-cropped to the page.
  accent     hex accent colour, e.g. "#1F7A6D" (default teal)
  tilt       degrees to rotate the hero image in layout E/L (default -4 for E, -3 for L)
  background local path of a lifestyle scene (layout "L"): e.g. a Canva AI desk flat-lay
             with an empty centre. The REAL product page is composited on top in code,
             so the product shown is always exactly what is sold.
Layout "L" lifestyle: full-bleed background scene, headline on a frosted card, real page(s)
             placed centre with a soft shadow, price tag and CTA.
No logo or brand badge is drawn (current NinthKart policy).
The bottom 10% of the canvas is kept free of text (Pinterest mobile overlay).
"""
import json, sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W, H = 1000, 1500
SAFE_BOTTOM = int(H * 0.90)
FONT_DIRS = ['/usr/share/fonts/truetype/google-fonts/', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts/')]


def _fetch_font(weight):
    d = FONT_DIRS[1]
    p = os.path.join(d, f'Poppins-{weight}.ttf')
    if not os.path.exists(p):
        try:
            import urllib.request
            os.makedirs(d, exist_ok=True)
            data = urllib.request.urlopen(f'https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-{weight}.ttf', timeout=20).read()
            open(p, 'wb').write(data)
        except Exception:
            pass


def font(weight, size):
    if not any(os.path.exists(os.path.join(d, f'Poppins-{weight}.ttf')) for d in FONT_DIRS):
        _fetch_font(weight)
    for d in FONT_DIRS:
        p = os.path.join(d, f'Poppins-{weight}.ttf')
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    bold = weight in ('Bold', 'SemiBold', 'ExtraBold')
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf' % ('-Bold' if bold else ''), size)


def hexrgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def crop_page(im):
    """If the image is a mockup (light background + white page), crop to the white page."""
    im = im.convert('RGB')
    g = im.convert('L').point(lambda v: 255 if v >= 253 else 0)
    w, h = g.size
    px = g.load()
    step = 4
    rows = [y for y in range(0, h, step) if sum(1 for x in range(0, w, step) if px[x, y]) > 0.35 * (w / step)]
    cols = [x for x in range(0, w, step) if sum(1 for y in range(0, h, step) if px[x, y]) > 0.35 * (h / step)]
    if not rows or not cols:
        return im
    x0, x1, y0, y1 = min(cols), max(cols) + step, min(rows), max(rows) + step
    area = (x1 - x0) * (y1 - y0)
    if area < 0.15 * w * h or area > 0.95 * w * h:
        return im
    return im.crop((x0, y0, min(w, x1), min(h, y1)))


def shadowed(img, radius=18, offset=(0, 14), opacity=70):
    pad = radius * 3
    base = Image.new('RGBA', (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    a = img.convert('RGBA').getchannel('A').point(lambda v: opacity if v > 8 else 0)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
    sh.putalpha(a)
    base.paste(sh, (pad + offset[0], pad + offset[1]), sh)
    base = base.filter(ImageFilter.GaussianBlur(radius))
    rgba = img.convert('RGBA')
    base.paste(rgba, (pad, pad), rgba)
    return base, pad


def fit(img, maxw, maxh):
    r = min(maxw / img.width, maxh / img.height)
    return img.resize((max(1, int(img.width * r)), max(1, int(img.height * r))), Image.LANCZOS)


def wrap(d, text, fnt, maxw):
    lines = []
    for para in text.split('\n'):
        cur = ''
        for w in para.split():
            t = (cur + ' ' + w).strip()
            if d.textlength(t, font=fnt) <= maxw:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def headline(d, text, y, color, maxw=880, start=112, minsize=60, maxlines=3):
    size = start
    for ml in (2, maxlines):
        size = start
        while size >= minsize:
            f = font('Bold', size)
            lines = wrap(d, text, f, maxw)
            if len(lines) <= ml and all(d.textlength(l, font=f) <= maxw for l in lines):
                break
            size -= 4
        if len(lines) <= ml:
            break
    lh = int(size * 1.08)
    for i, l in enumerate(lines):
        d.text((W / 2, y + i * lh), l, font=f, fill=color, anchor='mt')
    return y + len(lines) * lh


def pill_row(d, items, y, bg, fg, size=34):
    f = font('SemiBold', size)
    padx, h, gap = 26, size + 30, 16
    widths = [d.textlength(t, font=f) + padx * 2 for t in items]
    # shrink font if the row is too wide
    while sum(widths) + gap * (len(items) - 1) > W - 80 and size > 22:
        size -= 2
        f = font('SemiBold', size)
        h = size + 30
        widths = [d.textlength(t, font=f) + padx * 2 for t in items]
    x = (W - (sum(widths) + gap * (len(items) - 1))) / 2
    for t, w in zip(items, widths):
        d.rounded_rectangle([x, y, x + w, y + h], radius=h / 2, fill=bg)
        d.text((x + w / 2, y + h / 2), t, font=f, fill=fg, anchor='mm')
        x += w + gap
    return y + h


def price_tag(canvas, text, cx, cy, bg, fg=(255, 255, 255), r=88):
    d = ImageDraw.Draw(canvas)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg, outline=(255, 255, 255), width=6)
    f = font('Bold', 52 if len(text) <= 5 else 42)
    d.text((cx, cy), text, font=f, fill=fg, anchor='mm')


def cta_bar(d, text, accent, y=SAFE_BOTTOM - 96):
    f = font('SemiBold', 38)
    w = d.textlength(text, font=f) + 90
    x = (W - w) / 2
    d.rounded_rectangle([x, y, x + w, y + 76], radius=38, fill=accent)
    d.text((W / 2, y + 38), text, font=f, fill=(255, 255, 255), anchor='mm')


def place(canvas, img, box, shadow=True):
    x0, y0, x1, y1 = box
    im = fit(img, x1 - x0, y1 - y0)
    if shadow:
        s, pad = shadowed(im)
        px = int(x0 + ((x1 - x0) - im.width) / 2 - pad)
        py = int(y0 + ((y1 - y0) - im.height) / 2 - pad)
        canvas.alpha_composite(s, (px, py))
        return (px + pad, py + pad, px + pad + im.width, py + pad + im.height)
    px = int(x0 + ((x1 - x0) - im.width) / 2)
    py = int(y0 + ((y1 - y0) - im.height) / 2)
    canvas.alpha_composite(im.convert('RGBA'), (px, py))
    return (px, py, px + im.width, py + im.height)


def build(spec):
    layout = spec.get('layout', 'A').upper()
    accent = hexrgb(spec.get('accent', '#1F7A6D'))
    ink = (28, 28, 30)
    cream = (247, 243, 237)
    imgs = [crop_page(Image.open(p)) for p in spec['images']]
    cta = spec.get('cta', 'Instant download')
    price = spec.get('price')

    if layout == 'L':
        return build_lifestyle(spec, imgs, accent, ink, cream, cta, price)
    if layout == 'E':
        bg = accent
    elif layout == 'D':
        bg = mix(accent, (255, 255, 255), 0.86)
    else:
        bg = cream
    canvas = Image.new('RGBA', (W, H), bg + (255,))
    d = ImageDraw.Draw(canvas)
    title_col = (255, 255, 255) if layout == 'E' else ink
    sub_col = mix(accent, (255, 255, 255), 0.75) if layout == 'E' else accent

    y = headline(d, spec['headline'], 70, title_col)
    if spec.get('subhead'):
        f = font('Medium', 38)
        for l in wrap(d, spec['subhead'], f, 860)[:2]:
            y += 12
            d.text((W / 2, y), l, font=f, fill=sub_col, anchor='mt')
            y += 44
    y += 28

    if layout in ('A', 'D'):
        if spec.get('badges'):
            y = pill_row(d, spec['badges'][:3], y, accent if layout == 'A' else ink, (255, 255, 255)) + 34
        bottom = SAFE_BOTTOM - 130
        if imgs[0].width > imgs[0].height * 1.1 and len(imgs) >= 2:
            mid = y + (bottom - y) * 0.52
            place(canvas, imgs[1], (150, int(mid) - 10, W - 40, bottom))
            box = place(canvas, imgs[0], (40, y, W - 150, int(mid) + 40))
        else:
            box = place(canvas, imgs[0], (60, y, W - 60, bottom))
        if price:
            price_tag(canvas, price, min(box[2] - 30, W - 100), box[3] - 40, (224, 110, 54))
    elif layout == 'B':
        grid = imgs[:4] if len(imgs) >= 4 else (imgs * 4)[:4]
        top, bottom = y, SAFE_BOTTOM - 130
        cw, ch, g = (W - 120 - 30) / 2, (bottom - top - 30) / 2, 30
        for i, im in enumerate(grid):
            cx = 60 + (i % 2) * (cw + g)
            cy = top + (i // 2) * (ch + g)
            place(canvas, im, (int(cx), int(cy), int(cx + cw), int(cy + ch)))
        if price:
            price_tag(canvas, price, W / 2, (top + bottom) / 2, (224, 110, 54), r=82)
    elif layout == 'C':
        nb = len(spec.get('benefits', [])[:3])
        img_bottom = SAFE_BOTTOM - 130 - nb * 112 - 40
        box = place(canvas, imgs[0], (90, y, W - 90, img_bottom))
        if price:
            price_tag(canvas, price, min(box[2] - 20, W - 100), box[3] - 30, (224, 110, 54), r=78)
        y = box[3] + 50
        f = font('SemiBold', 38)
        for b in spec.get('benefits', [])[:3]:
            lines = wrap(d, b, f, 740)[:1]
            d.ellipse([90, y, 142, y + 52], fill=accent)
            d.line([(104, y + 27), (113, y + 37), (129, y + 17)], fill=(255, 255, 255), width=6)
            for j, l in enumerate(lines):
                d.text((170, y + 4 + j * 50), l, font=f, fill=ink)
            y += 112 - 50 + 50 * len(lines)
    elif layout == 'E':
        hero = imgs[0].convert('RGBA').rotate(spec.get('tilt', -4), expand=True, resample=Image.BICUBIC)
        box = place(canvas, hero, (70, y + 10, W - 70, SAFE_BOTTOM - 140), shadow=True)
        if price:
            price_tag(canvas, price, W - 120, box[1] + 40, (255, 255, 255), fg=accent)

    cta_bar(d, cta, (224, 110, 54) if layout != 'E' else ink)
    return canvas.convert('RGB')


def cover(img, w, h):
    r = max(w / img.width, h / img.height)
    im = img.resize((int(img.width * r) + 1, int(img.height * r) + 1), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def build_lifestyle(spec, imgs, accent, ink, cream, cta, price):
    bgp = spec.get('background')
    if bgp and os.path.exists(bgp):
        canvas = cover(Image.open(bgp).convert('RGB'), W, H).convert('RGBA')
    else:
        canvas = Image.new('RGBA', (W, H), cream + (255,))
    # frosted headline card
    probe = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    f = font('Bold', 96)
    lines = wrap(probe, spec['headline'], f, 800)
    size = 96
    while (len(lines) > 2 or any(probe.textlength(l, font=f) > 800 for l in lines)) and size > 60:
        size -= 4
        f = font('Bold', size)
        lines = wrap(probe, spec['headline'], f, 800)
    lh = int(size * 1.08)
    sub = spec.get('subhead')
    card_h = 60 + len(lines) * lh + (60 if sub else 0) + 20
    card = canvas.crop((50, 50, W - 50, 50 + card_h)).filter(ImageFilter.GaussianBlur(14))
    veil = Image.new('RGBA', card.size, (255, 253, 249, 205))
    card = Image.alpha_composite(card.convert('RGBA'), veil)
    mask = Image.new('L', card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, card.width, card.height], radius=36, fill=255)
    canvas.paste(card, (50, 50), mask)
    d = ImageDraw.Draw(canvas)
    y = 50 + 40
    for l in lines:
        d.text((W / 2, y), l, font=f, fill=ink, anchor='mt')
        y += lh
    if sub:
        fs = font('Medium', 36)
        d.text((W / 2, y + 12), wrap(d, sub, fs, 820)[0], font=fs, fill=accent, anchor='mt')
    top = 50 + card_h + 40
    bottom = SAFE_BOTTOM - 130
    hero = imgs[0].convert('RGBA')
    t = spec.get('tilt', -3)
    if t:
        hero = hero.rotate(t, expand=True, resample=Image.BICUBIC)
    if len(imgs) >= 2 and imgs[0].width > imgs[0].height * 1.1:
        mid = top + (bottom - top) * 0.5
        place(canvas, imgs[1].convert('RGBA').rotate(2, expand=True, resample=Image.BICUBIC), (170, int(mid) - 20, W - 50, bottom))
        box = place(canvas, hero, (50, top, W - 170, int(mid) + 50))
    else:
        box = place(canvas, hero, (90, top, W - 90, bottom))
    if price:
        price_tag(canvas, price, min(box[2] - 30, W - 100), box[3] - 40, (224, 110, 54))
    d = ImageDraw.Draw(canvas)
    cta_bar(d, cta, (224, 110, 54))
    return canvas.convert('RGB')


if __name__ == '__main__':
    spec = json.load(open(sys.argv[1]))
    build(spec).save(sys.argv[2], optimize=True)
    print('saved', sys.argv[2])
