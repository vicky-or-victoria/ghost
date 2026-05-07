# Map Render
# Detailed square-grid overworld map renderer using Pillow.
# Legend panel shows actual rendered tile samples, not just color swatches.

import math, random, io
import discord
import utils.db as db

try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_OK = True
except ImportError:
    PILLOW_OK = False

FONT_BOLD = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"

TILE     = 32
VIEW     = 15
PAD      = 12
HDR_H    = 60
LEG_TILE = 24

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

BORDER = {k: tuple(max(0,c-30) for c in v["dark"]) for k,v in TERRAINS.items()}

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


def addr(x:int,y:int)->str: return f"{x},{y}"
def parse(a:str)->tuple: p=a.split(","); return int(p[0]),int(p[1])
def in_bounds(x:int,y:int)->bool: return 0<=x<60 and 0<=y<120
def _n(x,y,s=0): return ((x*1847+y*2311+s*997)%256)/255.0
def _cl(v): return max(0,min(255,int(v)))


def _draw_tile(draw, tx, ty, terrain, size=TILE, explored=True):
    t      = TERRAINS.get(terrain, TERRAINS["jungle"])
    base,acc,dark = t["base"],t["acc"],t["dark"]
    border = BORDER.get(terrain,(20,20,20))
    x2,y2  = tx+size-1, ty+size-1
    draw.rectangle([tx,ty,x2,y2], fill=base, outline=border)
    if not explored:
        return

    if terrain in ("jungle","dense_bamboo"):
        for i in range(6 if size>=TILE else 3):
            ex=tx+int(_n(tx,ty,i*7)*(size-6))+3
            ey=ty+int(_n(tx+1,ty,i*7)*(size-6))+3
            r=max(1,2+int(_n(tx,ty+1,i)*2))
            c=tuple(_cl(b*(0.75+_n(tx,ty,i)*0.5)) for b in acc)
            draw.ellipse([ex-r,ey-r,ex+r,ey+r], fill=c)
        if size>=TILE:
            for i in range(2):
                ex=tx+int(_n(tx,ty,i*13+5)*(size-8))+4
                draw.line([(ex,ty+size-6),(ex,ty+size-2)],fill=dark,width=1)

    elif terrain=="farmland":
        step=max(3,size//8)
        for fy in range(ty+3,ty+size-2,step):
            draw.line([(tx+2,fy),(tx+size-3,fy)],fill=acc,width=2)
        for fx in range(tx+size//4,tx+size-4,size//3):
            draw.line([(fx,ty+2),(fx,ty+size-3)],fill=dark,width=1)

    elif terrain in ("mountain_pass","hilltop"):
        h2=size//3; mx=tx+size//2
        draw.polygon([(mx,ty+3),(mx-h2+2,ty+h2*2-2),(mx+h2-2,ty+h2*2-2)],fill=acc,outline=dark)
        draw.polygon([(mx,ty+3),(mx-3,ty+8),(mx+3,ty+8)],fill=(225,225,235))

    elif terrain in ("river_ford","swamp"):
        step=max(4,size//6)
        for wy2 in range(ty+3,ty+size-2,step):
            pts=[(wx2,wy2+int(math.sin((wx2+wy2)*0.5)*2)) for wx2 in range(tx+1,tx+size-1,2)]
            if len(pts)>=2: draw.line(pts,fill=acc,width=2)

    elif terrain=="coastal_beach":
        for i in range(6 if size>=TILE else 3):
            ex=tx+int(_n(tx,ty,i+20)*(size-4))+2
            ey=ty+int(_n(tx+2,ty,i+20)*(size-4))+2
            draw.ellipse([ex,ey,ex+2,ey+2],fill=acc)
        draw.rectangle([tx+1,ty+size-5,tx+size-2,ty+size-2],fill=(80,130,185))

    elif terrain in ("ruins","castle"):
        bs=max(4,size//5)
        for bx in range(tx+2,tx+size-3,bs+2):
            for by in range(ty+2,ty+size-3,bs-1):
                draw.rectangle([bx,by,bx+bs,by+bs-2],fill=acc,outline=dark)

    elif terrain in ("village","camp"):
        mx,my=tx+size//2,ty+size//2+1; hw=max(4,size//6)
        draw.rectangle([mx-hw,my-1,mx+hw,my+hw+1],fill=acc,outline=dark)
        draw.polygon([(mx-hw-1,my-1),(mx,my-hw-2),(mx+hw+1,my-1)],fill=base,outline=dark)
        draw.rectangle([mx-2,my+hw//2,mx+2,my+hw+1],fill=dark)

    elif terrain=="sacred_grove":
        cx,cy=tx+size//2,ty+size//2; r=size//3
        draw.ellipse([cx-r,cy-r,cx+r,cy+r],fill=acc,outline=dark)
        draw.ellipse([cx-r//2,cy-r//2,cx+r//2,cy+r//2],fill=base,outline=dark)

    elif terrain=="port_town":
        draw.rectangle([tx+1,ty+size-7,tx+size-2,ty+size-2],fill=(55,95,150))
        step=max(4,size//6)
        for px2 in range(tx+3,tx+size-2,step):
            draw.line([(px2,ty+size-7),(px2,ty+size-2)],fill=(40,70,110),width=1)
        draw.rectangle([tx+2,ty+2,tx+size//2,ty+size-8],fill=acc,outline=dark)

    elif terrain=="cave":
        cx,cy=tx+size//2,ty+size//2+1; r=size//3
        draw.ellipse([cx-r,cy-r//2,cx+r,cy+r],fill=dark,outline=acc)
        ir=max(2,r-3)
        draw.ellipse([cx-ir,cy-ir//2,cx+ir,cy+ir],fill=(8,6,10))


def _draw_player(draw, tx, ty, size=TILE):
    cx,cy=tx+size//2,ty+size//2
    for r2 in range(10,6,-1):
        draw.ellipse([cx-r2,cy-r2,cx+r2,cy+r2],outline=GOLD_LIGHT)
    draw.ellipse([cx-6,cy-6,cx+6,cy+6],fill=(255,225,40),outline=(180,140,0))
    draw.ellipse([cx-2,cy-2,cx+2,cy+2],fill=(80,50,0))


def _draw_enemy(draw, tx, ty, size=TILE):
    cx,cy=tx+size//2,ty+size//2
    draw.ellipse([cx-7,cy-7,cx+7,cy+7],fill=(185,25,25),outline=(100,0,0))
    draw.line([(cx-4,cy-4),(cx+4,cy+4)],fill=(255,180,180),width=2)
    draw.line([(cx+4,cy-4),(cx-4,cy+4)],fill=(255,180,180),width=2)


def _draw_named(draw, tx, ty, terrain, fnt, size=TILE):
    cx,cy=tx+size//2,ty+size//2
    sym,col=SYMBOLS.get(terrain,("?", (255,255,255)))
    draw.ellipse([cx-8,cy-8,cx+8,cy+8],outline=GOLD_LIGHT,width=2)
    draw.text((cx+1,cy+1),sym,font=fnt,fill=(0,0,0),anchor="mm")
    draw.text((cx,  cy),  sym,font=fnt,fill=col,    anchor="mm")


def _draw_compass(draw, cx, cy, r, fnt):
    draw.ellipse([cx-r,cy-r,cx+r,cy+r],fill=(18,18,28),outline=GOLD_DIM)
    for angle,label,col in [(0,"N",GOLD_LIGHT),(90,"E",GOLD_DIM),(180,"S",GOLD_DIM),(270,"W",GOLD_DIM)]:
        rad=math.radians(angle-90)
        ex=cx+int((r-5)*math.cos(rad)); ey=cy+int((r-5)*math.sin(rad))
        lx=cx+int((r+5)*math.cos(rad)); ly=cy+int((r+5)*math.sin(rad))
        draw.line([(cx,cy),(ex,ey)],fill=col,width=1)
        draw.text((lx,ly),label,font=fnt,fill=col,anchor="mm")
    draw.ellipse([cx-2,cy-2,cx+2,cy+2],fill=GOLD_LIGHT)


def _make_mini(terrain:str, size:int=LEG_TILE) -> "Image.Image":
    """Render a mini tile sample for the legend."""
    mini=Image.new("RGB",(size,size),BG)
    md=ImageDraw.Draw(mini)
    _draw_tile(md,0,0,terrain,size,True)
    return mini


def _paste_legend_row(img, draw, bx, by, mini, label, border_col, fnt):
    img.paste(mini,(bx,by))
    draw.rectangle([bx-1,by-1,bx+LEG_TILE,by+LEG_TILE],outline=border_col,width=1)
    draw.text((bx+LEG_TILE+5,by+LEG_TILE//2-4),label,font=fnt,fill=(185,180,160))


def render_map(
    player_addr:str,
    hex_rows:list,
    satsuma_units:list,
    recon_radius:int=3,
    act_label:str="",
    loc_name:str="",
    player_stats:dict=None,
) -> "discord.File | None":
    if not PILLOW_OK:
        return None

    px,py   = parse(player_addr)
    hex_map = {r["address"]:r for r in hex_rows}
    sat_set = {u["hex_address"] for u in satsuma_units if u.get("is_active")}
    half    = VIEW//2

    grid_w = VIEW*TILE
    grid_h = VIEW*TILE

    # Legend panel sizing
    LEG_COLS    = 2
    LEG_ROWS    = (len(TERRAINS)+1)//2
    col_w_leg   = 108
    LEG_PANEL_W = LEG_COLS*col_w_leg + 16
    COMPASS_H   = 68
    EXTRA_ROWS  = 4   # fog, player, enemy, named
    leg_content_h = COMPASS_H + 32 + LEG_ROWS*(LEG_TILE+8) + 12 + EXTRA_ROWS*(LEG_TILE+8)

    img_w = PAD + grid_w + PAD + LEG_PANEL_W
    img_h = HDR_H + PAD + max(grid_h, leg_content_h) + PAD

    img  = Image.new("RGB",(img_w,img_h),BG)
    draw = ImageDraw.Draw(img)

    try:
        fnt_title   = ImageFont.truetype(FONT_BOLD,13)
        fnt_sub     = ImageFont.truetype(FONT_BOLD, 9)
        fnt_sym     = ImageFont.truetype(FONT_BOLD,11)
        fnt_tiny    = ImageFont.truetype(FONT_BOLD, 7)
        fnt_compass = ImageFont.truetype(FONT_BOLD, 8)
        fnt_leg_sym = ImageFont.truetype(FONT_BOLD, 9)
    except Exception:
        fnt_title=fnt_sub=fnt_sym=fnt_tiny=fnt_compass=fnt_leg_sym=ImageFont.load_default()

    # Header
    draw.rectangle([0,0,img_w,HDR_H],fill=(14,14,22))
    draw.line([(0,HDR_H-1),(img_w,HDR_H-1)],fill=FRAME_GOLD,width=2)
    for cx2,cy2 in [(4,4),(img_w-4,4)]:
        draw.ellipse([cx2-3,cy2-3,cx2+3,cy2+3],fill=GOLD_DIM)
    draw.text((PAD,7),   "OVERWORLD MAP",font=fnt_title,fill=GOLD_LIGHT)
    draw.text((PAD,24),  f"{act_label}  |  {loc_name}",font=fnt_sub,fill=(160,155,130))
    draw.text((PAD,39),  f"Hex {px},{py}  |  Recon: {recon_radius}",font=fnt_tiny,fill=(110,108,95))
    if player_stats:
        sx=PAD+215
        draw.text((sx,9),  f"HP {player_stats.get('hp','?')}/{player_stats.get('max_hp','?')}",font=fnt_sub,fill=(170,215,130))
        draw.text((sx,25), f"ATK {player_stats.get('atk','?')}  DEF {player_stats.get('def','?')}  SPD {player_stats.get('spd','?')}",font=fnt_tiny,fill=(140,155,180))

    grid_x = PAD
    grid_y = HDR_H+PAD

    draw.rectangle([grid_x-2,grid_y-2,grid_x+grid_w+2,grid_y+grid_h+2],fill=(8,8,14))

    # Tiles
    for dy in range(-half,half+1):
        for dx in range(-half,half+1):
            wx,wy=px+dx,py+dy
            gx,gy=dx+half,dy+half
            tx2=grid_x+gx*TILE; ty2=grid_y+gy*TILE
            a=addr(wx,wy); h=hex_map.get(a)
            dist=max(abs(dx),abs(dy)); in_r=dist<=recon_radius
            isp=(dx==0 and dy==0)

            if isp:
                terrain=h.get("terrain","jungle") if h else "jungle"
                _draw_tile(draw,tx2,ty2,terrain,TILE,True)
                _draw_player(draw,tx2,ty2)
                continue

            fog=not h or (not h.get("is_explored") and not in_r)
            if fog:
                draw.rectangle([tx2,ty2,tx2+TILE-1,ty2+TILE-1],fill=FOG,outline=FOG_LINE)
                for i in range(4):
                    fx=tx2+int(_n(tx2,ty2,i*11)*(TILE-4))+2
                    fy=ty2+int(_n(tx2+1,ty2,i*11)*(TILE-4))+2
                    draw.ellipse([fx,fy,fx+1,fy+1],fill=(38,38,52))
                continue

            terrain=h.get("terrain","jungle") if h else "jungle"
            explored=h.get("is_explored",False) or in_r
            is_named=h.get("is_named_location",False) if h else False
            _draw_tile(draw,tx2,ty2,terrain,TILE,explored)
            if a in sat_set and in_r: _draw_enemy(draw,tx2,ty2)
            elif is_named: _draw_named(draw,tx2,ty2,terrain,fnt_sym)

    # Grid lines
    for gx in range(VIEW+1):
        draw.line([(grid_x+gx*TILE,grid_y),(grid_x+gx*TILE,grid_y+grid_h)],fill=(0,0,0),width=1)
    for gy in range(VIEW+1):
        draw.line([(grid_x,grid_y+gy*TILE),(grid_x+grid_w,grid_y+gy*TILE)],fill=(0,0,0),width=1)

    # Gold frame
    draw.rectangle([grid_x-2,grid_y-2,grid_x+grid_w+1,grid_y+grid_h+1],outline=FRAME_GOLD,width=2)
    for cx2,cy2 in [(grid_x-2,grid_y-2),(grid_x+grid_w+1,grid_y-2),
                    (grid_x-2,grid_y+grid_h+1),(grid_x+grid_w+1,grid_y+grid_h+1)]:
        draw.ellipse([cx2-3,cy2-3,cx2+3,cy2+3],fill=GOLD_DIM,outline=FRAME_GOLD)

    # Location labels
    for dy in range(-half,half+1):
        for dx in range(-half,half+1):
            wx,wy=px+dx,py+dy; a=addr(wx,wy); h=hex_map.get(a)
            if not h or not h.get("is_named_location") or not h.get("location_name"): continue
            dist=max(abs(dx),abs(dy))
            if not h.get("is_explored") and dist>recon_radius: continue
            gx,gy=dx+half,dy+half
            lx=grid_x+gx*TILE+TILE//2; label=h["location_name"][:11]
            draw.text((lx+1,grid_y+gy*TILE-2),label,font=fnt_tiny,fill=(0,0,0),anchor="mb")
            draw.text((lx,  grid_y+gy*TILE-3),label,font=fnt_tiny,fill=(255,240,150),anchor="mb")

    # RIGHT PANEL
    rpx=grid_x+grid_w+PAD+4
    rpy=grid_y

    # Compass
    comp_cx=rpx+LEG_PANEL_W//2-4; comp_cy=rpy+28
    _draw_compass(draw,comp_cx,comp_cy,22,fnt_compass)

    # Legend header
    lsy=rpy+COMPASS_H
    draw.line([(rpx,lsy-4),(rpx+LEG_PANEL_W-6,lsy-4)],fill=FRAME_GOLD,width=1)
    draw.text((rpx+4,lsy),  "TERRAIN LEGEND", font=fnt_tiny, fill=GOLD_LIGHT)
    draw.text((rpx+4,lsy+11),"Gold ring = Named Location",font=fnt_tiny,fill=GOLD_DIM)

    # Terrain tiles in 2-column grid
    lstart=lsy+26
    terrain_list=list(TERRAINS.items())
    for idx,(key,info) in enumerate(terrain_list):
        col=idx%LEG_COLS; row=idx//LEG_COLS
        bx=rpx+4+col*col_w_leg; by=lstart+row*(LEG_TILE+8)
        mini=_make_mini(key,LEG_TILE)
        _paste_legend_row(img,draw,bx,by,mini,info["label"],BORDER.get(key,(40,40,40)),fnt_tiny)

    # Extra marker rows
    rows_terrain=(len(terrain_list)+1)//LEG_COLS
    extra_y=lstart+rows_terrain*(LEG_TILE+8)+12
    draw.line([(rpx+4,extra_y-4),(rpx+LEG_PANEL_W-6,extra_y-4)],fill=FRAME_GOLD,width=1)

    def _extra_row(img, draw, by, mini, label, border):
        _paste_legend_row(img,draw,rpx+4,by,mini,label,border,fnt_tiny)

    # Fog
    m=Image.new("RGB",(LEG_TILE,LEG_TILE),FOG)
    md=ImageDraw.Draw(m)
    md.rectangle([0,0,LEG_TILE-1,LEG_TILE-1],fill=FOG,outline=FOG_LINE)
    for i in range(4):
        fx=int(_n(5,8,i*11)*(LEG_TILE-4))+2; fy=int(_n(6,9,i*11)*(LEG_TILE-4))+2
        md.ellipse([fx,fy,fx+1,fy+1],fill=(38,38,52))
    _extra_row(img,draw,extra_y,m,"Fog of War",FOG_LINE)

    # Player
    m2=_make_mini("jungle",LEG_TILE)
    md2=ImageDraw.Draw(m2)
    cx2,cy2=LEG_TILE//2,LEG_TILE//2
    for r2 in range(8,5,-1): md2.ellipse([cx2-r2,cy2-r2,cx2+r2,cy2+r2],outline=GOLD_LIGHT)
    md2.ellipse([cx2-5,cy2-5,cx2+5,cy2+5],fill=(255,225,40),outline=(180,140,0))
    md2.ellipse([cx2-2,cy2-2,cx2+2,cy2+2],fill=(80,50,0))
    _extra_row(img,draw,extra_y+LEG_TILE+8,m2,"Your Position",(180,140,0))

    # Enemy
    m3=_make_mini("jungle",LEG_TILE)
    md3=ImageDraw.Draw(m3)
    ecx,ecy=LEG_TILE//2,LEG_TILE//2
    md3.ellipse([ecx-7,ecy-7,ecx+7,ecy+7],fill=(185,25,25),outline=(100,0,0))
    md3.line([(ecx-4,ecy-4),(ecx+4,ecy+4)],fill=(255,180,180),width=2)
    md3.line([(ecx+4,ecy-4),(ecx-4,ecy+4)],fill=(255,180,180),width=2)
    _extra_row(img,draw,extra_y+(LEG_TILE+8)*2,m3,"Satsuma Unit",(100,0,0))

    # Named location
    m4=_make_mini("castle",LEG_TILE)
    md4=ImageDraw.Draw(m4)
    ncx,ncy=LEG_TILE//2,LEG_TILE//2
    md4.ellipse([ncx-7,ncy-7,ncx+7,ncy+7],outline=GOLD_LIGHT,width=2)
    md4.text((ncx+1,ncy+1),"S",font=fnt_leg_sym,fill=(0,0,0),anchor="mm")
    md4.text((ncx,  ncy),  "S",font=fnt_leg_sym,fill=(255,245,180),anchor="mm")
    _extra_row(img,draw,extra_y+(LEG_TILE+8)*3,m4,"Named Location",FRAME_GOLD)

    # Panel border
    draw.rectangle([rpx-2,rpy-2,rpx+LEG_PANEL_W-2,rpy+grid_h+1],outline=FRAME_GOLD,width=1)

    buf=io.BytesIO()
    img.save(buf,format="PNG",optimize=True)
    buf.seek(0)
    return discord.File(buf,filename="map.png")


async def render_viewport(guild_id:int, owner_id:int) -> "discord.File | None":
    player=await db.get_player(guild_id,owner_id)
    if not player: return None
    a=player.get("current_hex","30,85")
    recon=player.get("recon",8); radius=max(2,recon//3)
    px,py=parse(a)
    hexes=await db.get_viewport_hexes(guild_id,owner_id,px,py)
    units=await db.get_satsuma_units(guild_id,owner_id)
    h_row=await db.get_hex(guild_id,owner_id,a)
    loc=(h_row.get("location_name") or a) if h_row else a
    from utils.embeds import act_label as al
    return render_map(a,hexes,units,radius,
        act_label=al(player.get("current_act",1)),loc_name=loc,
        player_stats={"hp":player.get("hp",60),"max_hp":player.get("max_hp",60),
                      "atk":player.get("atk",8),"def":player.get("def",8),"spd":player.get("spd",8)})


def generate_viewport(player_addr,hex_rows,satsuma_units,recon_radius=3,viewport=17):
    px,py=parse(player_addr); half=viewport//2
    hex_map={r["address"]:r for r in hex_rows}
    sat_map={u["hex_address"]:u for u in satsuma_units if u.get("is_active")}
    TC={"coastal_beach":"~","jungle":"%","village":"V","mountain_pass":"^","farmland":".",
        "ruins":"#","river_ford":"=","hilltop":"n","dense_bamboo":"|","sacred_grove":"*",
        "swamp":"m","cliff_edge":"X","port_town":"P","castle":"S","cave":"O","camp":"C"}
    lines=[]
    for dy in range(-half,half+1):
        row=[]
        for dx in range(-half,half+1):
            wx,wy=px+dx,py+dy
            if not in_bounds(wx,wy): row.append(" "); continue
            if dx==0 and dy==0: row.append("@"); continue
            a=addr(wx,wy); dist=max(abs(dx),abs(dy)); h=hex_map.get(a)
            if not h or (not h.get("is_explored") and dist>recon_radius): row.append("·"); continue
            ch=TC.get(h.get("terrain","jungle"),".")
            if a in sat_map and dist<=recon_radius: ch="!"
            row.append(ch)
        lines.append(" ".join(row))
    return "```\n"+"\n".join(lines)+"\n```"


async def seed_player_map(guild_id:int, owner_id:int):
    rows=[]
    for x in range(60):
        for y in range(120):
            a=addr(x,y); terrain=_terrain_for(x,y)
            is_named,loc_name=False,None
            for loc,(lx,ly) in NAMED_LOCATIONS.items():
                if lx==x and ly==y:
                    is_named=True; loc_name=loc.replace("_"," ").title()
                    terrain=_named_terrain(loc); break
            rows.append((guild_id,owner_id,a,terrain,"neutral",False,is_named,loc_name))
    await db.bulk_insert_hexes(guild_id,owner_id,rows)
    sx,sy=NAMED_LOCATIONS["cave_of_refuge"]
    explore=[addr(sx+dx,sy+dy) for dx in range(-3,4) for dy in range(-3,4) if in_bounds(sx+dx,sy+dy)]
    await db.bulk_set_explored(guild_id,owner_id,explore)


def _terrain_for(x:int,y:int)->str:
    if y<=20:   pool=["mountain_pass","mountain_pass","dense_bamboo","jungle","hilltop","ruins"]
    elif y<=60: pool=["jungle","jungle","farmland","dense_bamboo","sacred_grove","village","ruins","swamp","river_ford"]
    elif y<=100:pool=["farmland","jungle","village","ruins","swamp","dense_bamboo","hilltop"]
    else:       pool=["coastal_beach","coastal_beach","port_town","farmland","village"]
    if y==70 and 15<=x<=50: return "river_ford" if x==32 else "jungle"
    return random.choice(pool)


def _named_terrain(loc:str)->str:
    if "castle" in loc or "shuri" in loc: return "castle"
    if "port" in loc or "naha" in loc:    return "port_town"
    if "village" in loc or "town" in loc: return "village"
    if "cave" in loc:                     return "cave"
    if "peninsula" in loc or "point" in loc or "cape" in loc: return "coastal_beach"
    if "camp" in loc:                     return "camp"
    if "farmstead" in loc:                return "farmland"
    return "jungle"


async def explore_around(guild_id:int, owner_id:int, hex_addr:str, radius:int):
    px,py=parse(hex_addr)
    explore=[addr(px+dx,py+dy) for dx in range(-radius,radius+1)
             for dy in range(-radius,radius+1) if in_bounds(px+dx,py+dy)]
    await db.bulk_set_explored(guild_id,owner_id,explore)