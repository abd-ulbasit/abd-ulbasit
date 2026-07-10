"""
One-time (re)generator for dark_mode.svg / light_mode.svg.

Converts the GitHub avatar to ASCII art and lays out the neofetch-style
card. Live stat fields get `id` attributes that today.py rewrites daily;
everything else is static. Re-run this only when changing the portrait,
colors, or card content.

Usage:
    pip install Pillow
    python scripts/generate_svg.py [path/to/photo.png]
    # default input: assets/avatar_nobg.png (GitHub avatar with the
    # background removed via rembg — the transparent background is what
    # keeps the portrait clean)
"""
import sys
import html

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

USERNAME = 'abd-ulbasit'
CARD_WIDTH_PX = 985
LINE_HEIGHT_PX = 20
TEXT_COL_X = 390
COL_WIDTH_CHARS = 58  # visible character budget per right-column line

ASCII_X = 15
ASCII_FONT_PX = 10
ASCII_LINE_PX = 10
ASCII_CHAR_W = 6.0    # Consolas advance at 10px with 109% size-adjust
ASCII_COLS = 60
ASCII_CROP = (75, 5, 445, 460)  # subject bounding box in the 460x460 avatar

# 10-level luminance ramp, sparse -> dense
RAMP = " .:-=+*#%@"

THEMES = {
    'dark_mode.svg': {
        'bg': '#161b22', 'fg': '#c9d1d9', 'key': '#ffa657', 'value': '#a5d6ff',
        'add': '#3fb950', 'del': '#f85149', 'cc': '#616e7f',
        'invert': False, 'gamma': 0.8,
    },
    'light_mode.svg': {
        'bg': '#fffefe', 'fg': '#24292f', 'key': '#953800', 'value': '#0a3069',
        'add': '#1a7f37', 'del': '#cf222e', 'cc': '#afb8c1',
        'invert': True, 'gamma': 1.4,
    },
}


def to_ascii(rgba, invert, gamma):
    # composite the cutout on the theme's effective background so the
    # transparent region maps to blank space in both modes
    if rgba.mode == 'RGBA':
        img = Image.new('L', rgba.size, 255 if invert else 0)
        img.paste(rgba.convert('L'), (0, 0), rgba.split()[-1])
    else:
        img = rgba.convert('L')
    img = img.crop(ASCII_CROP)
    img = ImageOps.autocontrast(img, cutoff=1)
    if gamma != 1.0:
        lut = [min(255, int((i / 255) ** gamma * 255)) for i in range(256)]
        img = img.point(lut)
    img = ImageEnhance.Sharpness(img).enhance(1.6)
    rows = int(ASCII_COLS * (img.height / img.width) * (ASCII_CHAR_W / ASCII_LINE_PX))
    img = img.resize((ASCII_COLS, rows), Image.LANCZOS)
    if invert:
        img = ImageOps.invert(img)
    px = img.load()
    lines = []
    for y in range(rows):
        lines.append(''.join(RAMP[px[x, y] * (len(RAMP) - 1) // 255] for x in range(ASCII_COLS)))

    # faint dot grid behind the silhouette: a '.' every 3rd col / 2nd row on
    # cells outside the subject mask (dilated one cell so the edge stays crisp)
    if rgba.mode == 'RGBA':
        mask = rgba.split()[-1].crop(ASCII_CROP).resize((ASCII_COLS, rows), Image.LANCZOS)
        mask = mask.point(lambda v: 255 if v > 60 else 0).filter(ImageFilter.MaxFilter(3))
        mpx = mask.load()
        bg_lines = []
        for y in range(rows):
            bg_lines.append(''.join(
                '.' if (x % 3 == 0 and y % 2 == 0 and not mpx[x, y]) else ' '
                for x in range(ASCII_COLS)))
    else:
        bg_lines = [' ' * ASCII_COLS] * rows
    return lines, bg_lines


def esc(s):
    return html.escape(s, quote=False)


class Card:
    """Accumulates right-column lines, padding each to COL_WIDTH_CHARS."""

    def __init__(self):
        self.rows = []  # list of tspan-content strings, None = skipped row (gap)

    def header(self, text):
        dashes = '—' * (COL_WIDTH_CHARS - len(text) - 3)
        self.rows.append(f'<tspan x="{TEXT_COL_X}" y="__Y__">{esc(text)}</tspan> -{dashes}-')

    def blank(self):
        self.rows.append(f'<tspan x="{TEXT_COL_X}" y="__Y__" class="cc">. </tspan>')

    def gap(self):
        self.rows.append(None)

    @staticmethod
    def _key_markup(key):
        return '.'.join(f'<tspan class="key">{esc(part)}</tspan>' for part in key.split('.'))

    @staticmethod
    def _dots(n):
        return {0: '', 1: ' ', 2: '. '}.get(n, ' ' + '.' * n + ' ')

    def field(self, key, value, value_id=None):
        """A '. Key: .... value' line, right-aligned to COL_WIDTH_CHARS.

        For dynamic fields (value_id set), today.py keeps the alignment by
        rewriting the dots with justify_format(root, value_id, value, L)
        where L = COL_WIDTH_CHARS - 5 - len(key) — the dots+value budget.
        """
        just_len = COL_WIDTH_CHARS - 2 - len(key) - 1 - 2 - len(value)
        assert just_len >= 0, f'line too long: {key}: {value}'
        dots = self._dots(just_len)
        dots_id = f' id="{value_id}_dots"' if value_id else ''
        val_id = f' id="{value_id}"' if value_id else ''
        self.rows.append(
            f'<tspan x="{TEXT_COL_X}" y="__Y__" class="cc">. </tspan>{self._key_markup(key)}:'
            f'<tspan class="cc"{dots_id}>{dots}</tspan><tspan class="value"{val_id}>{esc(value)}</tspan>')

    def raw(self, content):
        self.rows.append(f'<tspan x="{TEXT_COL_X}" y="__Y__" class="cc">. </tspan>{content}')


def build_card():
    c = Card()
    c.header(f'basit@{USERNAME}')
    c.field('OS', 'macOS, Linux')
    c.field('Uptime', '22 years, 10 months, 2 days', value_id='age_data')
    c.field('Host', 'Elite IT Team')
    c.field('Kernel', 'Software Engineer, Platform & Distributed')
    c.field('IDE', 'VSCode, Neovim')
    c.blank()
    c.field('Education', 'BSCS, NUST Islamabad')
    c.field('Certs', 'AWS Solutions Architect - Associate')
    c.blank()
    c.field('Languages.Programming', 'Go, TypeScript, Python')
    c.field('Languages.Cloud', 'Kubernetes, Docker, AWS, Nginx')
    c.field('Languages.Backend', 'NestJS, Django, FastAPI, Express')
    c.field('Languages.Frontend', 'React, Next.js, Redux, Tailwind')
    c.field('Languages.Database', 'PostgreSQL, MongoDB, Redis, MySQL')
    c.field('Languages.Real', 'English, Urdu')
    c.blank()
    c.field('Focus.Software', 'Kubernetes Operators, CRDT Sync')
    c.field('Focus.Hardware', 'Homelab (ThinkPad k8s cluster)')
    c.gap()
    c.header('- Contact')
    c.field('Email', 'basit01035@gmail.com')
    c.field('LinkedIn', 'abd-ulbasit')
    c.field('Portfolio', 'abd-ulbasit.vercel.app')
    c.gap()
    c.header('- GitHub Stats')
    # Stat lines: the justify budgets (dots+value) live in today.py's
    # svg_overwrite — repo 6, star 13, commit 22, follower 9, loc 13, del 7.
    c.raw('<tspan class="key">Repos</tspan>:<tspan class="cc" id="repo_data_dots"> .... </tspan>'
          '<tspan class="value" id="repo_data">10</tspan> {<tspan class="key">Contributed</tspan>: '
          '<tspan class="value" id="contrib_data">20</tspan>} | <tspan class="key">Stars</tspan>:'
          '<tspan class="cc" id="star_data_dots"> ............ </tspan><tspan class="value" id="star_data">0</tspan>')
    c.raw('<tspan class="key">Commits</tspan>:<tspan class="cc" id="commit_data_dots"> ..................... </tspan>'
          '<tspan class="value" id="commit_data">0</tspan> | <tspan class="key">Followers</tspan>:'
          '<tspan class="cc" id="follower_data_dots"> ........ </tspan><tspan class="value" id="follower_data">0</tspan>')
    c.raw('<tspan class="key">Lines of Code</tspan>:<tspan class="cc" id="loc_data_dots"> ............ </tspan>'
          '<tspan class="value" id="loc_data">0</tspan> ( <tspan class="addColor" id="loc_add">0</tspan>'
          '<tspan class="addColor">++</tspan>, <tspan id="loc_del_dots"> ...... </tspan>'
          '<tspan class="delColor" id="loc_del">0</tspan><tspan class="delColor">--</tspan> )')
    return c.rows


def render_svg(theme, ascii_lines, bg_lines, card_rows):
    height = 30 + LINE_HEIGHT_PX * (len(card_rows) - 1) + 20
    ascii_block_h = len(ascii_lines) * ASCII_LINE_PX
    ascii_y0 = max(20, (height - ascii_block_h) // 2 + 8)

    parts = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        f'<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,monospace" '
        f'width="{CARD_WIDTH_PX}px" height="{height}px" font-size="16px">',
        '<style>',
        '@font-face {',
        "src: local('Consolas'), local('Consolas Bold');",
        "font-family: 'ConsolasFallback';",
        'font-display: swap;',
        '-webkit-size-adjust: 109%;',
        'size-adjust: 109%;',
        '}',
        f'.key {{fill: {theme["key"]};}}',
        f'.value {{fill: {theme["value"]};}}',
        f'.addColor {{fill: {theme["add"]};}}',
        f'.delColor {{fill: {theme["del"]};}}',
        f'.cc {{fill: {theme["cc"]};}}',
        f'.ascii {{font-size: {ASCII_FONT_PX}px;}}',
        'text, tspan {white-space: pre;}',
        '</style>',
        f'<rect width="{CARD_WIDTH_PX}px" height="{height}px" fill="{theme["bg"]}" rx="15"/>',
        f'<text x="{ASCII_X}" y="{ascii_y0}" class="ascii cc">',
    ]
    for i, line in enumerate(bg_lines):
        if line.strip():
            parts.append(f'<tspan x="{ASCII_X}" y="{ascii_y0 + i * ASCII_LINE_PX}">{esc(line.rstrip())}</tspan>')
    parts.append('</text>')
    parts.append(f'<text x="{ASCII_X}" y="{ascii_y0}" fill="{theme["fg"]}" class="ascii">')
    for i, line in enumerate(ascii_lines):
        parts.append(f'<tspan x="{ASCII_X}" y="{ascii_y0 + i * ASCII_LINE_PX}">{esc(line)}</tspan>')
    parts.append('</text>')
    parts.append(f'<text x="{TEXT_COL_X}" y="30" fill="{theme["fg"]}">')
    for i, row in enumerate(card_rows):
        if row is not None:
            parts.append(row.replace("__Y__", str(30 + i * LINE_HEIGHT_PX)))
    parts.append('</text>')
    parts.append('</svg>')
    return '\n'.join(parts)


if __name__ == '__main__':
    photo = sys.argv[1] if len(sys.argv) > 1 else 'assets/avatar_nobg.png'
    avatar = Image.open(photo)
    card_rows = build_card()
    for filename, theme in THEMES.items():
        ascii_lines, bg_lines = to_ascii(avatar, theme['invert'], theme['gamma'])
        with open(filename, 'w') as f:
            f.write(render_svg(theme, ascii_lines, bg_lines, card_rows))
        print(f'wrote {filename} ({len(ascii_lines)} ascii rows)')
