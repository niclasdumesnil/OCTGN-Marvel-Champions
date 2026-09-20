# -*- coding: utf-8 -*-
# Conserve dans le depot, et pas dans un scratchpad : le generateur des jetons
# speciaux de 2026 avait ete ecrit puis perdu, et il a fallu le reecrire pour
# ajouter cette famille-ci. Rejouer ce script regenere les 24 PNG a l identique.
# Sortie : ./resource_tokens/, a recopier dans Sets/Stat_Tokens/Cards sous les
# GUID des cartes (voir resourceTokenIds dans scripts/actions.py).
"""Generateur des jetons de ressource (Physical / Energy / Mental / Wild), 0-5.

Meme grammaire que les jetons de stat - une valeur au centre, un bandeau noir en
bas - mais sur le TRIANGLE arrondi qui est le symbole de ressource du jeu, pour
qu'un jeton de ressource ne se confonde pas avec un jeton de stat sur la table.
Couleurs et glyphes repris de mc4db (style.css, ChampionsIcons.ttf).
"""
import os
from PIL import Image, ImageDraw, ImageFont

SIZE = 300
FONTS = 'C:/OS-Merlin/projets/mc4db-2.0/react-src/public/fonts'
ICONS = os.path.join(FONTS, 'ChampionsIcons.ttf')
NUMFONT = os.path.join(FONTS, 'Futura Extra Bold.otf')

RESOURCES = [
    ("Physical", "P", (220, 53, 69)),
    ("Energy",   "E", (255, 193, 7)),
    ("Mental",   "M", (0, 123, 255)),
    ("Wild",     "W", (40, 167, 69)),
]

OUTLINE = (20, 20, 22)


def rounded_triangle(draw, pts, radius, color):
    """Triangle aux coins arrondis : le polygone plein, plus un trait epais a
    jointure ronde qui suit ses cotes - la largeur du trait EST le rayon."""
    draw.polygon(pts, fill=color)
    # Le sommet est repasse : joint="curve" n'arrondit que les jointures
    # INTERIEURES, et le point de depart en laisserait une encoche.
    draw.line(list(pts) + [pts[0], pts[1]], fill=color, width=2 * radius, joint="curve")


def shrink(pts, d):
    """Les memes sommets, rapproches du centre de gravite de d pixels."""
    cx = sum(p[0] for p in pts) / 3.0
    cy = sum(p[1] for p in pts) / 3.0
    out = []
    for (x, y) in pts:
        dx, dy = x - cx, y - cy
        n = (dx * dx + dy * dy) ** 0.5
        out.append((x - dx / n * d, y - dy / n * d))
    return out


def text_centered(draw, xy, text, font, fill, stroke=0, stroke_fill=None):
    x, y = xy
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((x - w / 2.0 - bbox[0], y - h / 2.0 - bbox[1]), text, font=font,
              fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)


def make(name, glyph, color, value, path):
    """Rendu a 4x puis reduit : les bords du triangle et le cerne du chiffre
    sont trop fins pour l'anticrenelage direct de Pillow."""
    S = SIZE * 4
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = [(S / 2.0, 30 * 4), (S - 34 * 4, S - 62 * 4), (34 * 4, S - 62 * 4)]
    rounded_triangle(d, pts, 22 * 4, OUTLINE)
    rounded_triangle(d, shrink(pts, 9 * 4), 18 * 4, color)
    gf = ImageFont.truetype(ICONS, 76 * 4)
    text_centered(d, (S / 2.0, 104 * 4), glyph, gf, (255, 255, 255, 240))
    nf = ImageFont.truetype(NUMFONT, 104 * 4)
    text_centered(d, (S / 2.0, 186 * 4), str(value), nf, (255, 255, 255, 255), 8 * 4, OUTLINE)
    d.rounded_rectangle((16 * 4, 244 * 4, (SIZE - 16) * 4, (SIZE - 6) * 4), 12 * 4, fill=OUTLINE)
    lf = ImageFont.truetype(os.path.join(FONTS, 'AvenirNextLTPro-Bold.otf'), 32 * 4)
    text_centered(d, (S / 2.0, 269 * 4), name.upper(), lf, (255, 255, 255, 255))
    im.resize((SIZE, SIZE), Image.LANCZOS).save(path)


if __name__ == '__main__':
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resource_tokens')
    for name, glyph, color in RESOURCES:
        for v in range(0, 6):
            suffix = '' if v == 0 else '.' + chr(ord('a') + v)
            make(name, glyph, color, v, os.path.join(out, '%s%s.png' % (name, suffix)))
    print('24 images generees dans', out)
