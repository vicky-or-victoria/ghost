# Map Render
# Layout: [Left: Region Minimap] [Center: Viewport Grid] [Right: Legend]

import math, random, io
import discord
import utils.db as db

try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_OK = True
except ImportError:
    PILLOW_OK = False

FONT_BOLD = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"

TILE      = 32
VIEW      = 15
PAD       = 10
HDR_H     = 60
LEG_TILE  = 22

MINI_CELL = 3
MINI_W    = 60 * MINI_CELL
MINI_H    = 120 * MINI_CELL
LEFT_PAD  = 10
LEFT_W    = MINI_W + LEFT_PAD * 2

RIGHT_W   = 160

GRID_W    = VIEW * TILE
GRID_H    = VIEW * TILE
IMG_W     = LEFT_W + GRID_W + RIGHT_W + PAD * 2
IMG_H     = HDR_H + PAD + GRID_H + PAD + 24


def moves_for_spd(spd: int) -> int:
    return max(1, spd // 3)


NAMED_LOCATIONS = {
    "cave_of_refuge":    (30, 85),
    "naha_port":         (28,110),
    "itoman_village":    (25,108),
    "shuri_castle":      (31, 90),
    "katsuren_castle":   (45, 75),
    "nakagusuku_castle": (38, 82),
    "yomitan_village":   (20, 88),
    "motobu_peninsula":  (18, 45),
    "hedo_point":        (22,  5),
    "cape_kyan":         (28,118),
    "nago_town":         (24, 35),
    "urasoe_village":    (29, 95),
    "chinen_peninsula":  (40,112),
    "iso_camp":          (33,100),
    "hana_farmstead":    (27, 92),
}

TERRAINS = {
    "jungle":        {"base":(28,72,28),    "acc":(15,50,15),    "dark":(8,35,8),    "label":"Jungle"},
    "dense_bamboo":  {"base":(18,88,45),    "acc":(10,65,28),    "dark":(6,48,16),   "label":"Dense Bamboo"},
    "farmland":      {"base":(115,158,55),  "acc":(88,125,35),   "dark":(60,90,20),  "label":"Farmland"},
    "village":       {"base":(162,132,78),  "acc":(105,82,42),   "dark":(70,52,22),  "label":"Village"},
    "mountain_pass": {"base":(108,96,84),   "acc":(76,66,58),    "dark":(50,44,38),  "label":"Mountain"},
    "hilltop":       {"base":(135,118,88),  "acc":(102,88,62),   "dark":(72,60,40),  "label":"Hilltop"},
    "coastal_beach": {"base":(205,178,112), "acc":(162,138,78),  "dark":(115,96,48), "label":"Beach"},
    "ruins":         {"base":(98,88,78),    "acc":(66,58,50),    "dark":(42,36,30),  "label":"Ruins"},
    "river_ford":    {"base":(65,118,178),  "acc":(42,88,148),   "dark":(28,58,108), "label":"River Ford"},
    "swamp":         {"base":(55,92,55),    "acc":(35,65,35),    "dark":(20,42,20),  "label":"Swamp"},
    "sacred_grove":  {"base":(42,132,52),   "acc":(22,95,32),    "dark":(12,62,18),  "label":"Sacred Grove"},
    "castle":        {"base":(112,92,72),   "acc":(72,56,40),    "dark":(42,32,22),  "label":"Castle"},
    "port_town":     {"base":(72,108,158),  "acc":(48,78,125),   "dark":(28,50,88),  "label":"Port Town"},
    "cave":          {"base":(72,62,82),    "acc":(48,40,58),    "dark":(28,22,35),  "label":"Cave"},
    "camp":          {"base":(158,128,65),  "acc":(118,92,40),   "dark":(80,62,22),  "label":"Camp"},
}

TERRAIN_COLORS_MINI = {k: v["base"] for k, v in TERRAINS.items()}
BORDER = {k: tuple(max(0, c-30) for c in v["dark"]) for k, v in TERRAINS.items()}

FOG        = (20, 20, 30)
FOG_LINE   = (32, 32, 46)
BG         = (10, 10, 16)
FRAME_GOLD = (80, 65, 20)
GOLD_LIGHT = (220, 185, 75)
GOLD_DIM   = (140, 115, 45)

SYMBOLS = {
    "castle":        ("S", (255,245,180)),
    "port_town":     ("P", (180,220,255)),
    "village":       ("V", (255,220,140)),
    "cave":          ("O", (210,185,230)),
    "camp":          ("C", (255,205,100)),
    "ruins":         ("#", (185,172,155)),
    "sacred_grove":  ("*", (140,255,140)),
    "mountain_pass": ("^", (225,215,200)),
}

IMPASSABLE = {"cliff_edge"}


def addr(x: int, y: int) -> str:
    return f"{x},{y}"


def parse(a: str) -> tuple:
    p = a.split(",")
    return int(p[0]), int(p[1])


def in_bounds(x: int, y: int) -> bool:
    return 0 <= x < 60 and 0 <= y < 120


def _n(x, y, s=0):
    return ((x * 1847 + y * 2311 + s * 997) % 256) / 255.0


def _cl(v):
    return max(0, min(255, int(v)))


def _load_fonts():
    try:
        return {k: ImageFont.truetype(FONT_BOLD, sz) for k, sz in
                [("title",13),("sub",9),("sym",11),("tiny",7),("micro",6),("compass",8),("leg_sym",9)]}
    except Exception:
        d = ImageFont.load_default()
        return {k: d for k in ("title","sub","sym","tiny","micro","compass","leg_sym")}


# Terrain drawing

def _draw_tile(draw, tx, ty, terrain, size=TILE, explored=True):
    t = TERRAINS.get(terrain, TERRAINS["jungle"])
    base, acc, dark = t["base"], t["acc"], t["dark"]
    border = BORDER.get(terrain, (20, 20, 20))
    s = size

    draw.rectangle([tx, ty, tx+s-1, ty+s-1], fill=base)
    if not explored:
        draw.rectangle([tx, ty, tx+s-1, ty+s-1], outline=border)
        return

    if terrain == "jungle":
        for i in range(8 if s >= TILE else 4):
            cx = tx + int(_n(tx+i, ty, 1)*(s-12)) + 6
            cy = ty + int(_n(tx+i, ty, 2)*(s-12)) + 6
            r  = int(3 + _n(tx, ty+i, 3)*5)
            shade = tuple(_cl(b*(0.55+_n(tx+i, ty+i, 4)*0.65)) for b in acc)
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=shade, outline=dark)
        for i in range(3):
            gx = tx + int(_n(tx, ty, i*7+10)*(s-8))+4
            gy = ty + int(_n(tx+1, ty, i*7+10)*(s-8))+4
            draw.ellipse([gx, gy, gx+2, gy+2], fill=dark)

    elif terrain == "dense_bamboo":
        draw.rectangle([tx, ty, tx+s-1, ty+s-1], fill=(25,95,45))
        num = max(3, s // 6)
        for i in range(num):
            sx2 = tx + i*(s//num) + int(_n(i,0,1)*2)
            w2  = 2 + (i%3==0)
            draw.line([(sx2,ty+2),(sx2,ty+s-2)], fill=(20,110,55), width=w2)
            for ny2 in range(ty+6, ty+s-4, 8+int(_n(i,1,2)*4)):
                draw.line([(sx2-2,ny2),(sx2+w2+1,ny2)], fill=(10,75,30), width=1)
            draw.line([(sx2-1,ty+3),(sx2-1,ty+s-3)], fill=(8,50,20), width=1)
        for i in range(0, max(3,s//6), 2):
            sx2 = tx + i*(s//max(3,s//6)) + 2
            ly2 = ty + 4 + int(_n(i,2,3)*6)
            draw.line([(sx2,ly2),(sx2+5,ly2-4)], fill=(20,110,55), width=1)
            draw.line([(sx2,ly2),(sx2-4,ly2-3)], fill=(20,110,55), width=1)

    elif terrain == "farmland":
        strip_h = max(2, s // 6)
        for row in range(6):
            ry = ty + row*strip_h
            shade = acc if row%2==0 else tuple(_cl(c*0.85) for c in acc)
            draw.rectangle([tx, ry, tx+s-1, min(ty+s-1,ry+strip_h-1)], fill=shade)
        for row in range(7):
            ry = ty + row*(s//6)
            draw.line([(tx+1,ry),(tx+s-2,ry)], fill=dark, width=1)
        for col in range(4):
            cx2 = tx + col*(s//3)
            draw.line([(cx2,ty+1),(cx2,ty+s-2)], fill=dark, width=1)
        for row in range(2):
            for col in range(3):
                sdx = tx + col*(s//3) + s//6
                sdy = ty + row*(s//2) + s//4
                draw.ellipse([sdx-1,sdy-2,sdx+1,sdy+2], fill=tuple(_cl(c*1.2) for c in dark))

    elif terrain == "village":
        draw.rectangle([tx, ty+s*2//3, tx+s-1, ty+s-1], fill=tuple(_cl(c*0.85) for c in base))
        # House 1
        h1x, h1y = tx+3, ty+s//3
        draw.rectangle([h1x,h1y,h1x+14,h1y+18], fill=acc, outline=dark)
        draw.polygon([(h1x-1,h1y),(h1x+7,h1y-8),(h1x+15,h1y)], fill=(140,80,40), outline=dark)
        draw.rectangle([h1x+4,h1y+9,h1x+9,h1y+18], fill=dark)
        draw.rectangle([h1x+1,h1y+3,h1x+5,h1y+7], fill=(180,200,220))
        # House 2
        h2x, h2y = tx+s//2-2, ty+s//4
        draw.rectangle([h2x,h2y,h2x+16,h2y+20], fill=tuple(_cl(c*0.9) for c in acc), outline=dark)
        draw.polygon([(h2x-1,h2y),(h2x+8,h2y-9),(h2x+17,h2y)], fill=(155,90,45), outline=dark)
        draw.rectangle([h2x+5,h2y+11,h2x+11,h2y+20], fill=dark)
        draw.rectangle([h2x+1,h2y+4,h2x+6,h2y+9], fill=(180,200,220))
        draw.rectangle([h2x+10,h2y+4,h2x+15,h2y+9], fill=(180,200,220))
        draw.line([(tx+s//3,ty+s-2),(tx+s//2+4,ty+s*2//3+8)], fill=dark, width=2)

    elif terrain == "mountain_pass":
        draw.rectangle([tx,ty,tx+s-1,ty+s//4], fill=tuple(_cl(c*1.1) for c in base))
        back = tuple(_cl(c*1.15) for c in base)
        draw.polygon([(tx+2,ty+s-2),(tx+s//3,ty+s//5),(tx+s//2,ty+s//3),(tx+s-2,ty+s-2)],
                     fill=back, outline=dark)
        draw.polygon([(tx+2,ty+s-2),(tx+s//2,ty+4),(tx+s-2,ty+s-2)], fill=acc, outline=dark)
        draw.polygon([(tx+2,ty+s-2),(tx+s//2,ty+4),(tx+s//2,ty+s-2)], fill=dark)
        draw.polygon([(tx+s//2,ty+4),(tx+s//2-8,ty+16),(tx+s//2+8,ty+16)], fill=(235,235,245))
        for i in range(3):
            rx = tx + int(_n(tx,ty,i*5)*(s//2-4))+4
            ry = ty + s//2 + int(_n(tx+1,ty,i*5)*(s//3))
            draw.ellipse([rx,ry,rx+4,ry+3], fill=dark)

    elif terrain == "hilltop":
        draw.rectangle([tx,ty,tx+s-1,ty+s//3], fill=tuple(_cl(c*1.08) for c in base))
        hill_pts = [(tx,ty+s-2)]
        for xi in range(s):
            curve = int(math.sin(xi/s*math.pi)*s*0.45)
            hill_pts.append((tx+xi, ty+s-curve-4))
        hill_pts.append((tx+s-1,ty+s-2))
        draw.polygon(hill_pts, fill=acc)
        for i in range(6):
            gx = tx+5 + int(_n(i,ty,1)*(s-10))
            gy = ty+s - int(math.sin((gx-tx)/s*math.pi)*s*0.4) - 7
            draw.line([(gx,gy),(gx-2,gy-4)], fill=dark, width=1)
            draw.line([(gx,gy),(gx+2,gy-4)], fill=dark, width=1)
            draw.line([(gx,gy),(gx,gy-5)],   fill=dark, width=1)

    elif terrain == "coastal_beach":
        for row in range(s*3//5):
            t_frac = row/(s*3//5)
            draw.line([(tx,ty+row),(tx+s-1,ty+row)],
                      fill=(int(205-t_frac*30), int(178-t_frac*25), int(112-t_frac*10)))
        for row in range(s*3//5, s):
            t_frac = (row-s*3//5)/(s*2//5+1)
            draw.line([(tx,ty+row),(tx+s-1,ty+row)],
                      fill=(int(65+t_frac*15), int(118+t_frac*12), int(178+t_frac*22)))
        wave_y = ty + s*3//5
        for xi in range(0, s, 2):
            wy2 = wave_y + int(math.sin(xi*0.3)*3)
            draw.point((tx+xi,wy2),   fill=(200,220,240))
            draw.point((tx+xi,wy2-1), fill=(230,240,250))
        for row in range(2):
            ry = ty + s//5 + row*(s//5)
            draw.arc([tx+3,ry,tx+s//2,ry+5], 0, 180, fill=tuple(_cl(c*0.9) for c in acc), width=1)

    elif terrain == "ruins":
        for i in range(5):
            rx = tx + int(_n(tx,ty,i*3)*(s-10))+5
            ry = ty + int(_n(tx+1,ty,i*3)*(s-10))+5
            rw = 4 + int(_n(tx,ty+1,i*3)*7)
            rh = 3 + int(_n(tx+2,ty,i*3)*4)
            draw.rectangle([rx,ry,rx+rw,ry+rh], fill=acc, outline=dark)
        pts  = [(tx+4,ty+s//2+6),(tx+4,ty+10),(tx+12,ty+8),(tx+14,ty+s//2+4)]
        draw.polygon(pts, fill=acc, outline=dark)
        draw.line([(tx+7,ty+12),(tx+10,ty+26)], fill=dark, width=1)
        draw.line([(tx+10,ty+26),(tx+8,ty+38)], fill=dark, width=1)
        pts2 = [(tx+s-5,ty+s//2+4),(tx+s-7,ty+16),(tx+s-15,ty+14),(tx+s-17,ty+s//2+2)]
        draw.polygon(pts2, fill=tuple(_cl(c*0.9) for c in acc), outline=dark)
        for i in range(4):
            gx = tx+4 + int(_n(i,tx,7)*(s-8))
            gy = ty+s-7 - int(_n(gx,ty,8)*10)
            draw.line([(gx,gy),(gx-2,gy-5)], fill=(55,100,35), width=1)
            draw.line([(gx,gy),(gx+2,gy-4)], fill=(55,100,35), width=1)

    elif terrain == "castle":
        wall  = acc
        tower = tuple(_cl(c*0.85) for c in acc)
        draw.rectangle([tx+6,ty+s//4,tx+s-6,ty+s-4], fill=wall, outline=dark)
        draw.rectangle([tx+s//2-5,ty+s//2,tx+s//2+5,ty+s-4], fill=(30,20,15))
        draw.arc([tx+s//2-7,ty+s//2-7,tx+s//2+7,ty+s//2+7], 0, 180, fill=wall, width=2)
        for tcx, tcy in [(tx+3,ty+s//5),(tx+s-12,ty+s//5)]:
            draw.rectangle([tcx,tcy,tcx+8,tcy+s//3], fill=tower, outline=dark)
            for mx2 in range(tcx, tcx+8, 3):
                draw.rectangle([mx2,tcy-3,mx2+2,tcy], fill=tower, outline=dark)
        for mx2 in range(tx+8, tx+s-8, 5):
            draw.rectangle([mx2,ty+s//4-3,mx2+3,ty+s//4], fill=tower, outline=dark)
        for wx2 in [tx+s//4, tx+s*3//4-4]:
            draw.rectangle([wx2-1,ty+s//3,wx2+1,ty+s//2], fill=(20,15,10))

    elif terrain == "river_ford":
        draw.rectangle([tx,ty,tx+s//3,ty+s-1],        fill=(88,140,65))
        draw.rectangle([tx+s*2//3,ty,tx+s-1,ty+s-1],  fill=(88,140,65))
        draw.rectangle([tx+s//3,ty,tx+s*2//3,ty+s-1], fill=acc)
        for yi in range(s):
            offset = int(math.sin(yi/s*math.pi*2)*s//10)
            cx2 = tx + s//2 + offset
            draw.line([(cx2-s//7,ty+yi),(cx2+s//7,ty+yi)],
                      fill=tuple(_cl(c*0.85) for c in acc))
        for i in range(4):
            ry2 = ty + 5 + i*(s//4)
            offset = int(math.sin(i*1.2)*5)
            draw.arc([tx+s//3+2+offset,ry2,tx+s*2//3-2+offset,ry2+6],
                     10, 170, fill=(180,210,240), width=1)
        for i, sx2 in enumerate([tx+s//3+3, tx+s//2-2, tx+s*2//3-7]):
            sy2 = ty + s//5 + i*(s//4)
            draw.ellipse([sx2,sy2,sx2+6,sy2+4], fill=dark, outline=tuple(_cl(c*0.7) for c in dark))
        for i in range(3):
            gx = tx+2 + int(_n(i,ty,1)*(s//3-4))
            gy = ty+4 + int(_n(i,ty,2)*(s-8))
            draw.line([(gx,gy),(gx-2,gy-4)], fill=(55,110,40), width=1)
            draw.line([(gx,gy),(gx+2,gy-4)], fill=(55,110,40), width=1)

    elif terrain == "swamp":
        for i in range(4):
            wx2 = tx+4  + int(_n(tx,ty,i*4)*(s-16))
            wy2 = ty+4  + int(_n(tx+1,ty,i*4)*(s-16))
            wr  = 5 + int(_n(tx,ty+2,i*4)*9)
            wh  = 3 + int(_n(tx+2,ty,i*4)*5)
            draw.ellipse([wx2,wy2,wx2+wr,wy2+wh], fill=(38,55,42), outline=(25,38,30))
            draw.line([(wx2+2,wy2+wh//2),(wx2+wr//2,wy2+wh//2)], fill=(55,80,62), width=1)
        for i in range(2):
            sx2 = tx+8 + int(_n(i,ty+1,3)*(s-16))
            sy2 = ty+s//3 + int(_n(i+1,ty,3)*(s//2-8))
            draw.rectangle([sx2,sy2,sx2+3,sy2+10], fill=(45,32,22), outline=(28,20,14))
            draw.line([(sx2+1,sy2+3),(sx2-4,sy2-2)], fill=(45,32,22), width=1)
            draw.line([(sx2+1,sy2+3),(sx2+6,sy2-2)], fill=(45,32,22), width=1)
        for i in range(4):
            bx = tx+5 + int(_n(tx+3,ty,i*6)*(s-10))
            by = ty+5 + int(_n(tx,ty+3,i*6)*(s-10))
            draw.ellipse([bx,by,bx+3,by+3], outline=(50,75,52), width=1)

    elif terrain == "sacred_grove":
        draw.rectangle([tx,ty,tx+s-1,ty+s-1], fill=(20,55,25))
        cx2, cy2 = tx+s//2, ty+s//2
        for r2 in range(s//2-2, 0, -4):
            intensity = 1.0 - r2/(s//2)
            ring_col  = tuple(int(c*(0.3+intensity*0.9)) for c in (80,200,90))
            draw.ellipse([cx2-r2,cy2-r2,cx2+r2,cy2+r2], outline=ring_col, width=1)
        draw.ellipse([cx2-5,cy2-5,cx2+5,cy2+5], fill=(150,255,140), outline=(100,220,100))
        draw.ellipse([cx2-2,cy2-2,cx2+2,cy2+2], fill=(220,255,210))
        step = max(3, s//8)
        for angle in range(0, 360, 60):
            rad = math.radians(angle)
            mx2 = int(cx2 + math.cos(rad)*(s//3))
            my2 = int(cy2 + math.sin(rad)*(s//3))
            draw.rectangle([mx2-2,my2-4,mx2+2,my2+4], fill=(60,90,55), outline=(40,65,38))
        for i in range(6):
            angle = _n(tx,ty,i*9)*2*math.pi
            dist  = 6 + _n(tx+1,ty,i*9)*s//5
            lx2   = int(cx2 + math.cos(angle)*dist)
            ly2   = int(cy2 + math.sin(angle)*dist)
            draw.ellipse([lx2,ly2,lx2+3,ly2+2], fill=(100,200,80))

    elif terrain == "port_town":
        draw.rectangle([tx,ty,tx+s-1,ty+s*2//5], fill=(90,140,190))
        draw.rectangle([tx,ty+s*2//5,tx+s-1,ty+s-1], fill=(45,85,145))
        for i in range(3):
            wy2 = ty + s*2//5 + 5 + i*7
            draw.arc([tx+2,wy2,tx+s-2,wy2+4], 5, 175, fill=(65,110,175), width=1)
        bx = tx+2
        for i in range(3):
            bw = 12 + i*4; bh = 14 + i*5
            by = ty + s*2//5 - bh
            col = tuple(_cl(c*(0.7+i*0.15)) for c in acc)
            draw.rectangle([bx,by,bx+bw,ty+s*2//5], fill=col, outline=dark)
            draw.polygon([(bx-1,by),(bx+bw//2,by-6),(bx+bw+1,by)], fill=dark)
            for wi in range(max(1,bw//8)):
                wx2 = bx+3+wi*7
                draw.rectangle([wx2,by+3,wx2+3,by+8], fill=(200,215,235))
            bx += bw + 3
        draw.rectangle([tx+2,ty+s*2//5-3,tx+s-3,ty+s*2//5+4], fill=(90,65,40))
        for dx2 in range(tx+4,tx+s-4,5):
            draw.line([(dx2,ty+s*2//5-3),(dx2,ty+s*2//5+4)], fill=(65,45,28), width=1)
        for mx2 in [tx+s//4, tx+s*3//4-4]:
            my2 = ty+s*2//5+5
            draw.line([(mx2,my2),(mx2,my2+s//3)], fill=(65,45,28), width=2)
            draw.polygon([(mx2,my2+3),(mx2+8,my2+9),(mx2,my2+18)], fill=(220,210,190))

    elif terrain == "cave":
        for i in range(6):
            rx = tx + int(_n(tx,ty,i*6)*(s-8))+4
            ry = ty + int(_n(tx+1,ty,i*6)*(s-8))+4
            rr = 2 + int(_n(tx,ty+2,i)*4)
            draw.ellipse([rx-rr,ry-rr,rx+rr,ry+rr], fill=tuple(_cl(c*0.85) for c in base), outline=dark)
        cx2 = tx+s//2; ey = ty+s*2//5; aw = s//3; ah = s//3
        draw.ellipse([cx2-aw,ey-ah//2,cx2+aw,ey+ah], fill=(8,5,12))
        draw.arc([cx2-aw-2,ey-ah//2-2,cx2+aw+2,ey+ah+2], 180, 360, fill=dark, width=3)
        for i in range(5):
            sx2 = cx2 - aw + 5 + i*(aw*2//5)
            sh  = 5 + int(_n(i,ty,3)*8)
            sw  = 2 + int(_n(i+1,ty,3)*1)
            draw.polygon([(sx2-sw,ey-ah//2+2),(sx2+sw,ey-ah//2+2),(sx2,ey-ah//2+2+sh)], fill=dark)
        draw.ellipse([cx2-3,ey+2,cx2+3,ey+7], fill=(18,12,22))
        for i in range(3):
            rx = cx2-aw+4 + int(_n(tx,ty,i+20)*(aw*2-8))
            ry = ey+ah-4
            draw.ellipse([rx,ry,rx+4,ry+3], fill=dark)

    elif terrain == "camp":
        draw.ellipse([tx+s//2-9,ty+s*2//3-5,tx+s//2+9,ty+s*2//3+5],
                     fill=tuple(_cl(c*0.75) for c in base))
        tx2, ty2 = tx+s//2-12, ty+s//4
        tw, th   = 24, 20
        draw.polygon([(tx2,ty2+th),(tx2+tw//2,ty2),(tx2+tw,ty2+th)], fill=acc, outline=dark)
        draw.polygon([(tx2+tw//2-4,ty2+th),(tx2+tw//2,ty2+7),(tx2+tw//2+4,ty2+th)], fill=dark)
        draw.line([(tx2+tw//2,ty2),(tx2-3,ty2+th+3)], fill=dark, width=1)
        draw.line([(tx2+tw//2,ty2),(tx2+tw+3,ty2+th+3)], fill=dark, width=1)
        draw.ellipse([tx2-5,ty2+th+2,tx2-3,ty2+th+5], fill=dark)
        draw.ellipse([tx2+tw+3,ty2+th+2,tx2+tw+5,ty2+th+5], fill=dark)
        fx, fy = tx+s//2-2, ty+s*2//3-4
        draw.ellipse([fx-3,fy-2,fx+8,fy+7], fill=(80,40,10))
        draw.polygon([(fx+3,fy-7),(fx,fy+4),(fx+6,fy+4)], fill=(220,120,20))
        draw.polygon([(fx+3,fy-5),(fx+1,fy+4),(fx+5,fy+4)], fill=(255,200,50))
        draw.ellipse([fx+1,fy,fx+4,fy+3], fill=(255,230,100))
        draw.line([(fx-2,fy+5),(fx+7,fy+5)], fill=(55,32,15), width=2)
        draw.ellipse([tx+4,ty+s//2,tx+12,ty+s//2+7], fill=tuple(_cl(c*0.8) for c in acc), outline=dark)

    draw.rectangle([tx, ty, tx+s-1, ty+s-1], outline=border, width=1)


def _draw_player(draw, tx, ty):
    cx, cy = tx+TILE//2, ty+TILE//2
    for r2 in range(10, 6, -1):
        draw.ellipse([cx-r2,cy-r2,cx+r2,cy+r2], outline=GOLD_LIGHT)
    draw.ellipse([cx-6,cy-6,cx+6,cy+6], fill=(255,225,40), outline=(180,140,0))
    draw.ellipse([cx-2,cy-2,cx+2,cy+2], fill=(80,50,0))


def _draw_enemy(draw, tx, ty):
    cx, cy = tx+TILE//2, ty+TILE//2
    draw.ellipse([cx-7,cy-7,cx+7,cy+7], fill=(185,25,25), outline=(100,0,0))
    draw.line([(cx-4,cy-4),(cx+4,cy+4)], fill=(255,180,180), width=2)
    draw.line([(cx+4,cy-4),(cx-4,cy+4)], fill=(255,180,180), width=2)


def _draw_named(draw, tx, ty, terrain, fnt):
    cx, cy   = tx+TILE//2, ty+TILE//2
    sym, col = SYMBOLS.get(terrain, ("?", (255,255,255)))
    draw.ellipse([cx-8,cy-8,cx+8,cy+8], outline=GOLD_LIGHT, width=2)
    draw.text((cx+1,cy+1), sym, font=fnt, fill=(0,0,0),  anchor="mm")
    draw.text((cx,  cy),   sym, font=fnt, fill=col,       anchor="mm")


def _draw_compass(draw, cx, cy, r, fnt):
    draw.ellipse([cx-r,cy-r,cx+r,cy+r], fill=(18,18,28), outline=GOLD_DIM)
    for angle, label, col in [(0,"N",GOLD_LIGHT),(90,"E",GOLD_DIM),(180,"S",GOLD_DIM),(270,"W",GOLD_DIM)]:
        rad = math.radians(angle-90)
        ex  = cx+int((r-5)*math.cos(rad)); ey = cy+int((r-5)*math.sin(rad))
        lx2 = cx+int((r+5)*math.cos(rad)); ly2= cy+int((r+5)*math.sin(rad))
        draw.line([(cx,cy),(ex,ey)], fill=col, width=1)
        draw.text((lx2,ly2), label, font=fnt, fill=col, anchor="mm")
    draw.ellipse([cx-2,cy-2,cx+2,cy+2], fill=GOLD_LIGHT)


def _draw_moves_bar(draw, x, y, w, left, total, fnt):
    h = 10
    draw.rectangle([x,y,x+w,y+h], fill=(25,25,35), outline=GOLD_DIM)
    if total > 0 and left > 0:
        filled = max(1, int(w*left/total))
        col    = (80,200,80) if left==total else (200,180,50) if left>total//2 else (200,80,50)
        draw.rectangle([x+1,y+1,x+filled-1,y+h-1], fill=col)
    draw.text((x+w+5,y-1), f"Moves: {left}/{total}", font=fnt, fill=GOLD_DIM)


def _draw_location_label(draw, cx, tile_bottom_y, label, fnt):
    words = label.split(); lines = []; cur = ""
    for word in words:
        test = (cur+" "+word).strip()
        if len(test) <= 12:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = word
    if cur: lines.append(cur)
    for i, line in enumerate(lines):
        ly = tile_bottom_y + i*9
        draw.text((cx+1,ly+1), line, font=fnt, fill=(0,0,0),        anchor="mt")
        draw.text((cx,  ly),   line, font=fnt, fill=(255,240,150),   anchor="mt")


def _draw_left_minimap(img, draw, lx, ly, hex_rows, player_addr, F):
    px, py  = parse(player_addr)
    hex_map = {r["address"]: r for r in hex_rows}
    draw.text((lx, ly-14), "REGION", font=F["tiny"], fill=GOLD_LIGHT)
    for x in range(60):
        for y in range(120):
            a  = f"{x},{y}"; h = hex_map.get(a)
            cx = lx+x*MINI_CELL; cy = ly+y*MINI_CELL
            x2 = cx+MINI_CELL-1; y2 = cy+MINI_CELL-1
            if not h or not h.get("is_explored"):
                draw.rectangle([cx,cy,x2,y2], fill=FOG)
            else:
                col = TERRAIN_COLORS_MINI.get(h.get("terrain","jungle"), (28,72,28))
                draw.rectangle([cx,cy,x2,y2], fill=col)
    for loc,(nx,ny) in NAMED_LOCATIONS.items():
        a = f"{nx},{ny}"; h = hex_map.get(a)
        if h and h.get("is_explored"):
            draw.ellipse([lx+nx*MINI_CELL,ly+ny*MINI_CELL,
                          lx+nx*MINI_CELL+MINI_CELL,ly+ny*MINI_CELL+MINI_CELL],
                         fill=(255,200,60))
    half = VIEW//2
    vx1 = lx+max(0,px-half)*MINI_CELL; vy1 = ly+max(0,py-half)*MINI_CELL
    vx2 = lx+min(60,px+half+1)*MINI_CELL; vy2 = ly+min(120,py+half+1)*MINI_CELL
    draw.rectangle([vx1,vy1,vx2,vy2], outline=(200,200,60), width=1)
    draw.ellipse([lx+px*MINI_CELL,ly+py*MINI_CELL,
                  lx+px*MINI_CELL+MINI_CELL+1,ly+py*MINI_CELL+MINI_CELL+1],
                 fill=(255,225,40), outline=(180,140,0))
    draw.rectangle([lx-2,ly-2,lx+MINI_W+1,ly+MINI_H+1], outline=FRAME_GOLD, width=1)
    leg_y = ly+MINI_H+8
    for label, col in [("@ You",(255,225,40)),("o Named",(255,200,60)),("Box=View",(200,200,60))]:
        draw.ellipse([lx,leg_y,lx+5,leg_y+5], fill=col)
        draw.text((lx+8,leg_y-1), label, font=F["micro"], fill=(165,160,140))
        leg_y += 10


def render_map(
    player_addr: str,
    hex_rows: list,
    satsuma_units: list,
    recon_radius: int = 3,
    act_label: str = "",
    loc_name: str = "",
    player_stats: dict = None,
    moves_left: int = None,
    moves_max: int = None,
) -> "discord.File | None":
    if not PILLOW_OK:
        return None

    px, py  = parse(player_addr)
    hex_map = {r["address"]: r for r in hex_rows}
    sat_set = {u["hex_address"] for u in satsuma_units if u.get("is_active")}
    half    = VIEW//2
    F       = _load_fonts()

    img  = Image.new("RGB", (IMG_W, IMG_H), BG)
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([0,0,IMG_W,HDR_H], fill=(14,14,22))
    draw.line([(0,HDR_H-1),(IMG_W,HDR_H-1)], fill=FRAME_GOLD, width=2)
    for cx2,cy2 in [(4,4),(IMG_W-4,4)]:
        draw.ellipse([cx2-3,cy2-3,cx2+3,cy2+3], fill=GOLD_DIM)
    draw.text((LEFT_W+PAD,7),  "OVERWORLD MAP", font=F["title"], fill=GOLD_LIGHT)
    draw.text((LEFT_W+PAD,24), f"{act_label}  |  {loc_name}", font=F["sub"], fill=(160,155,130))
    draw.text((LEFT_W+PAD,39), f"Hex {px},{py}  |  Recon: {recon_radius}", font=F["tiny"], fill=(110,108,95))
    if player_stats:
        sx = LEFT_W+PAD+225
        draw.text((sx,9),  f"HP {player_stats.get('hp','?')}/{player_stats.get('max_hp','?')}",
                  font=F["sub"], fill=(170,215,130))
        draw.text((sx,25), f"ATK {player_stats.get('atk','?')}  DEF {player_stats.get('def','?')}  SPD {player_stats.get('spd','?')}",
                  font=F["tiny"], fill=(140,155,180))

    grid_x = LEFT_W+PAD
    grid_y = HDR_H+PAD

    # Left panel
    draw.rectangle([0,HDR_H,LEFT_W-1,IMG_H], outline=(40,35,12), width=1)
    draw.line([(LEFT_W-1,HDR_H),(LEFT_W-1,IMG_H)], fill=FRAME_GOLD, width=2)
    _draw_left_minimap(img, draw, LEFT_PAD, grid_y+18, hex_rows, player_addr, F)

    draw.rectangle([grid_x-2,grid_y-2,grid_x+GRID_W+2,grid_y+GRID_H+2], fill=(8,8,14))

    label_queue = []
    for dy in range(-half, half+1):
        for dx in range(-half, half+1):
            wx, wy = px+dx, py+dy
            gx, gy = dx+half, dy+half
            tx2    = grid_x+gx*TILE; ty2 = grid_y+gy*TILE
            a      = addr(wx, wy); h = hex_map.get(a)
            dist   = max(abs(dx),abs(dy)); in_r = dist<=recon_radius
            isp    = (dx==0 and dy==0)

            if isp:
                terrain = h.get("terrain","jungle") if h else "jungle"
                _draw_tile(draw, tx2, ty2, terrain, TILE, True)
                _draw_player(draw, tx2, ty2)
                continue

            fog = not h or (not h.get("is_explored") and not in_r)
            if fog:
                draw.rectangle([tx2,ty2,tx2+TILE-1,ty2+TILE-1], fill=FOG, outline=FOG_LINE)
                for i in range(4):
                    fx = tx2+int(_n(tx2,ty2,i*11)*(TILE-4))+2
                    fy = ty2+int(_n(tx2+1,ty2,i*11)*(TILE-4))+2
                    draw.ellipse([fx,fy,fx+1,fy+1], fill=(38,38,52))
                continue

            terrain  = h.get("terrain","jungle") if h else "jungle"
            explored = h.get("is_explored",False) or in_r
            is_named = h.get("is_named_location",False) if h else False
            _draw_tile(draw, tx2, ty2, terrain, TILE, explored)

            if a in sat_set and in_r:
                _draw_enemy(draw, tx2, ty2)
            elif is_named:
                _draw_named(draw, tx2, ty2, terrain, F["sym"])
                loc_label = h.get("location_name","") if h else ""
                if loc_label:
                    label_queue.append((tx2+TILE//2, ty2+TILE+1, loc_label))

    # Grid lines
    for gx in range(VIEW+1):
        draw.line([(grid_x+gx*TILE,grid_y),(grid_x+gx*TILE,grid_y+GRID_H)], fill=(0,0,0), width=1)
    for gy in range(VIEW+1):
        draw.line([(grid_x,grid_y+gy*TILE),(grid_x+GRID_W,grid_y+gy*TILE)], fill=(0,0,0), width=1)

    draw.rectangle([grid_x-2,grid_y-2,grid_x+GRID_W+1,grid_y+GRID_H+1], outline=FRAME_GOLD, width=2)
    for cx2,cy2 in [(grid_x-2,grid_y-2),(grid_x+GRID_W+1,grid_y-2),
                    (grid_x-2,grid_y+GRID_H+1),(grid_x+GRID_W+1,grid_y+GRID_H+1)]:
        draw.ellipse([cx2-3,cy2-3,cx2+3,cy2+3], fill=GOLD_DIM, outline=FRAME_GOLD)

    for (lcx, lty, ll) in label_queue:
        if lty > grid_y+GRID_H-2: lty = grid_y+GRID_H-20
        _draw_location_label(draw, lcx, lty, ll, F["micro"])

    # Moves bar
    if moves_left is not None and moves_max:
        _draw_moves_bar(draw, grid_x, grid_y+GRID_H+6, GRID_W-80, moves_left, moves_max, F["tiny"])

    # Right panel
    rpx = grid_x+GRID_W+PAD
    draw.line([(rpx-1,HDR_H),(rpx-1,IMG_H)], fill=FRAME_GOLD, width=2)
    _draw_compass(draw, rpx+RIGHT_W//2, grid_y+26, 22, F["compass"])

    lsy = grid_y+58
    draw.line([(rpx+4,lsy-4),(rpx+RIGHT_W-4,lsy-4)], fill=FRAME_GOLD, width=1)
    draw.text((rpx+4,lsy),   "TERRAIN", font=F["tiny"], fill=GOLD_LIGHT)
    draw.text((rpx+4,lsy+11),"Gold ring = Named", font=F["tiny"], fill=GOLD_DIM)

    lstart = lsy+24
    terrain_list = list(TERRAINS.items())
    for idx,(key,info) in enumerate(terrain_list):
        by   = lstart+idx*(LEG_TILE+5)
        mini = Image.new("RGB",(LEG_TILE,LEG_TILE),BG)
        md   = ImageDraw.Draw(mini)
        _draw_tile(md, 0, 0, key, LEG_TILE, True)
        img.paste(mini, (rpx+4,by))
        draw.rectangle([rpx+3,by-1,rpx+4+LEG_TILE,by+LEG_TILE], outline=BORDER.get(key,(40,40,40)), width=1)
        draw.text((rpx+4+LEG_TILE+5,by+LEG_TILE//2-4), info["label"], font=F["tiny"], fill=(185,180,160))

    extra_y = lstart+len(terrain_list)*(LEG_TILE+5)+8
    draw.line([(rpx+4,extra_y-4),(rpx+RIGHT_W-4,extra_y-4)], fill=FRAME_GOLD, width=1)

    def _extra(by, mini_img, label, border):
        img.paste(mini_img,(rpx+4,by))
        draw.rectangle([rpx+3,by-1,rpx+4+LEG_TILE,by+LEG_TILE], outline=border, width=1)
        draw.text((rpx+4+LEG_TILE+5,by+LEG_TILE//2-4), label, font=F["tiny"], fill=(185,180,160))

    m  = Image.new("RGB",(LEG_TILE,LEG_TILE),FOG); md=ImageDraw.Draw(m)
    md.rectangle([0,0,LEG_TILE-1,LEG_TILE-1],fill=FOG,outline=FOG_LINE)
    _extra(extra_y, m, "Fog of War", FOG_LINE)

    m2 = Image.new("RGB",(LEG_TILE,LEG_TILE),TERRAINS["jungle"]["base"]); md2=ImageDraw.Draw(m2)
    _draw_tile(md2,0,0,"jungle",LEG_TILE,True)
    cx2,cy2=LEG_TILE//2,LEG_TILE//2
    for r2 in range(8,5,-1): md2.ellipse([cx2-r2,cy2-r2,cx2+r2,cy2+r2],outline=GOLD_LIGHT)
    md2.ellipse([cx2-5,cy2-5,cx2+5,cy2+5],fill=(255,225,40),outline=(180,140,0))
    md2.ellipse([cx2-2,cy2-2,cx2+2,cy2+2],fill=(80,50,0))
    _extra(extra_y+LEG_TILE+5, m2, "You (@)", (180,140,0))

    m3 = Image.new("RGB",(LEG_TILE,LEG_TILE),TERRAINS["jungle"]["base"]); md3=ImageDraw.Draw(m3)
    _draw_tile(md3,0,0,"jungle",LEG_TILE,True)
    ecx,ecy=LEG_TILE//2,LEG_TILE//2
    md3.ellipse([ecx-7,ecy-7,ecx+7,ecy+7],fill=(185,25,25),outline=(100,0,0))
    md3.line([(ecx-4,ecy-4),(ecx+4,ecy+4)],fill=(255,180,180),width=2)
    md3.line([(ecx+4,ecy-4),(ecx-4,ecy+4)],fill=(255,180,180),width=2)
    _extra(extra_y+(LEG_TILE+5)*2, m3, "Satsuma (!)", (100,0,0))

    m4 = Image.new("RGB",(LEG_TILE,LEG_TILE),TERRAINS["castle"]["base"]); md4=ImageDraw.Draw(m4)
    _draw_tile(md4,0,0,"castle",LEG_TILE,True)
    ncx,ncy=LEG_TILE//2,LEG_TILE//2
    md4.ellipse([ncx-7,ncy-7,ncx+7,ncy+7],outline=GOLD_LIGHT,width=2)
    md4.text((ncx+1,ncy+1),"S",font=F["leg_sym"],fill=(0,0,0),anchor="mm")
    md4.text((ncx,  ncy),  "S",font=F["leg_sym"],fill=(255,245,180),anchor="mm")
    _extra(extra_y+(LEG_TILE+5)*3, m4, "Named Loc", FRAME_GOLD)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return discord.File(buf, filename="map.png")


def render_region_map(hex_rows: list, player_addr: str) -> "discord.File | None":
    if not PILLOW_OK:
        return None
    CELL=5; mw=60*CELL; mh=120*CELL; HDR=44; LEG=30
    F=_load_fonts()
    img_w=mw+PAD*2; img_h=mh+PAD*2+HDR+LEG
    img=Image.new("RGB",(img_w,img_h),BG); draw=ImageDraw.Draw(img)
    px,py=parse(player_addr)
    hex_map={r["address"]:r for r in hex_rows}
    draw.rectangle([0,0,img_w,HDR],fill=(14,14,22))
    draw.line([(0,HDR-1),(img_w,HDR-1)],fill=FRAME_GOLD,width=2)
    draw.text((PAD,7),  "REGION MAP — RYUKYU",font=F["title"],fill=GOLD_LIGHT)
    draw.text((PAD,24), f"Position: {px},{py}  |  Bright box = Current View",font=F["tiny"],fill=(140,135,115))
    mx=PAD; my=HDR+PAD
    for x in range(60):
        for y in range(120):
            a=f"{x},{y}"; h=hex_map.get(a)
            cx=mx+x*CELL; cy=my+y*CELL; x2=cx+CELL-1; y2=cy+CELL-1
            if not h or not h.get("is_explored"):
                draw.rectangle([cx,cy,x2,y2],fill=FOG)
            else:
                col=TERRAIN_COLORS_MINI.get(h.get("terrain","jungle"),(28,72,28))
                draw.rectangle([cx,cy,x2,y2],fill=col)
    for loc,(nx,ny) in NAMED_LOCATIONS.items():
        a=f"{nx},{ny}"; h=hex_map.get(a)
        if h and h.get("is_explored"):
            cx2=mx+nx*CELL+CELL//2; cy2=my+ny*CELL+CELL//2
            draw.ellipse([cx2-3,cy2-3,cx2+3,cy2+3],fill=(255,200,60),outline=(180,140,0))
            label=loc.replace("_"," ").title()
            lx2=cx2+6 if nx<40 else cx2-6; anchor="lm" if nx<40 else "rm"
            draw.text((lx2+1,cy2+1),label,font=F["micro"],fill=(0,0,0),anchor=anchor)
            draw.text((lx2,  cy2),  label,font=F["micro"],fill=(255,240,150),anchor=anchor)
    half=VIEW//2
    vx1=mx+max(0,px-half)*CELL; vy1=my+max(0,py-half)*CELL
    vx2=mx+min(60,px+half+1)*CELL; vy2=my+min(120,py+half+1)*CELL
    draw.rectangle([vx1,vy1,vx2,vy2],outline=(200,200,60),width=2)
    pcx=mx+px*CELL+CELL//2; pcy=my+py*CELL+CELL//2
    for r2 in range(6,3,-1): draw.ellipse([pcx-r2,pcy-r2,pcx+r2,pcy+r2],outline=GOLD_LIGHT)
    draw.ellipse([pcx-3,pcy-3,pcx+3,pcy+3],fill=(255,225,40),outline=(180,140,0))
    draw.rectangle([mx-2,my-2,mx+mw+1,my+mh+1],outline=FRAME_GOLD,width=2)
    leg_y=my+mh+6
    draw.rectangle([0,leg_y,img_w,img_h],fill=(12,12,20))
    draw.line([(0,leg_y),(img_w,leg_y)],fill=FRAME_GOLD,width=1)
    items=[((255,225,40),"@ You"),((255,200,60),"o Named Location"),((200,200,60),"  Current View"),(FOG,"  Unexplored")]
    lx2=PAD
    for col,label in items:
        draw.rectangle([lx2,leg_y+8,lx2+10,leg_y+20],fill=col,outline=(80,70,30))
        draw.text((lx2+14,leg_y+6),label,font=F["tiny"],fill=(180,175,155))
        lx2+=len(label)*5+24
    buf=io.BytesIO(); img.save(buf,format="PNG",optimize=True); buf.seek(0)
    return discord.File(buf,filename="region_map.png")


async def render_viewport(guild_id: int, owner_id: int) -> "discord.File | None":
    player = await db.get_player(guild_id, owner_id)
    if not player: return None
    a      = player.get("current_hex","30,85")
    recon  = player.get("recon",8); radius = max(2, recon//3)
    px, py = parse(a)
    hexes  = await db.get_viewport_hexes(guild_id, owner_id, px, py)
    units  = await db.get_satsuma_units(guild_id, owner_id)
    h_row  = await db.get_hex(guild_id, owner_id, a)
    loc    = (h_row.get("location_name") or a) if h_row else a
    spd    = player.get("spd",8); mx = moves_for_spd(spd)
    counters = await db.get_trait_counters(guild_id, owner_id, "mc")
    ml     = max(0, mx - counters.get("moves_this_turn",0))
    from utils.embeds import act_label as al
    return render_map(a, hexes, units, radius,
        act_label=al(player.get("current_act",1)), loc_name=loc,
        player_stats={"hp":player.get("hp",60),"max_hp":player.get("max_hp",60),
                      "atk":player.get("atk",8),"def":player.get("def",8),"spd":spd},
        moves_left=ml, moves_max=mx)


async def render_region(guild_id: int, owner_id: int) -> "discord.File | None":
    player = await db.get_player(guild_id, owner_id)
    if not player: return None
    a      = player.get("current_hex","30,85")
    px, py = parse(a)
    hexes  = await db.get_viewport_hexes(guild_id, owner_id, px, py, half=60)
    return render_region_map(hexes, a)


def generate_viewport(player_addr, hex_rows, satsuma_units, recon_radius=3, viewport=17):
    px, py  = parse(player_addr); half = viewport//2
    hex_map = {r["address"]:r for r in hex_rows}
    sat_map = {u["hex_address"]:u for u in satsuma_units if u.get("is_active")}
    TC = {"coastal_beach":"~","jungle":"%","village":"V","mountain_pass":"^","farmland":".",
          "ruins":"#","river_ford":"=","hilltop":"n","dense_bamboo":"|","sacred_grove":"*",
          "swamp":"m","cliff_edge":"X","port_town":"P","castle":"S","cave":"O","camp":"C"}
    lines = []
    for dy in range(-half, half+1):
        row = []
        for dx in range(-half, half+1):
            wx, wy = px+dx, py+dy
            if not in_bounds(wx,wy): row.append(" "); continue
            if dx==0 and dy==0: row.append("@"); continue
            a = addr(wx,wy); dist=max(abs(dx),abs(dy)); h=hex_map.get(a)
            if not h or (not h.get("is_explored") and dist>recon_radius): row.append("·"); continue
            ch = TC.get(h.get("terrain","jungle"),".")
            if a in sat_map and dist<=recon_radius: ch="!"
            row.append(ch)
        lines.append(" ".join(row))
    return "```\n"+"\n".join(lines)+"\n```"


async def seed_player_map(guild_id: int, owner_id: int):
    rows = []
    for x in range(60):
        for y in range(120):
            a = addr(x,y); terrain = _terrain_for(x,y)
            is_named, loc_name = False, None
            for loc,(lx,ly) in NAMED_LOCATIONS.items():
                if lx==x and ly==y:
                    is_named=True; loc_name=loc.replace("_"," ").title()
                    terrain=_named_terrain(loc); break
            rows.append((guild_id,owner_id,a,terrain,"neutral",False,is_named,loc_name))
    await db.bulk_insert_hexes(guild_id, owner_id, rows)
    sx, sy = NAMED_LOCATIONS["cave_of_refuge"]
    explore = [addr(sx+dx,sy+dy) for dx in range(-3,4) for dy in range(-3,4) if in_bounds(sx+dx,sy+dy)]
    await db.bulk_set_explored(guild_id, owner_id, explore)


def _terrain_for(x: int, y: int) -> str:
    if y <= 20:   pool = ["mountain_pass","mountain_pass","dense_bamboo","jungle","hilltop","ruins"]
    elif y <= 60: pool = ["jungle","jungle","farmland","dense_bamboo","sacred_grove","village","ruins","swamp","river_ford"]
    elif y <= 100:pool = ["farmland","jungle","village","ruins","swamp","dense_bamboo","hilltop"]
    else:         pool = ["coastal_beach","coastal_beach","port_town","farmland","village"]
    if y==70 and 15<=x<=50: return "river_ford" if x==32 else "jungle"
    return random.choice(pool)


def _named_terrain(loc: str) -> str:
    if "castle" in loc or "shuri" in loc: return "castle"
    if "port" in loc or "naha" in loc:    return "port_town"
    if "village" in loc or "town" in loc: return "village"
    if "cave" in loc:                     return "cave"
    if "peninsula" in loc or "point" in loc or "cape" in loc: return "coastal_beach"
    if "camp" in loc:                     return "camp"
    if "farmstead" in loc:                return "farmland"
    return "jungle"


async def explore_around(guild_id: int, owner_id: int, hex_addr: str, radius: int):
    px, py  = parse(hex_addr)
    explore = [addr(px+dx,py+dy) for dx in range(-radius,radius+1)
               for dy in range(-radius,radius+1) if in_bounds(px+dx,py+dy)]
    await db.bulk_set_explored(guild_id, owner_id, explore)