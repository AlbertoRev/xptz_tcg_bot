"""Page composition for POKèPUTZU WEEKLY.

The five core spreads are drawn on measured A4 zones. Optional continuation
pages are inserted before the back cover when source material exceeds those
zones. Drawing and fitting stay deterministic when Gemini is unavailable.
"""
import math
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from src import editorial_news, rivista as R
from src.report import _eur, _t

W, H = R.W, R.H
BLUE, NAVY, RED, YELLOW, WHITE = R.BLU, R.INCHIOSTRO, R.ROSSO, R.SOLE, colors.white
M = 10 * mm
SCENE_DIR = Path(__file__).resolve().parent.parent / "editorial_scenes"


def _rect(c, x, top, w, h, fill=WHITE, alpha=.95, radius=3 * mm):
    c.saveState()
    c.setFillColor(fill)
    c.setFillAlpha(alpha)
    c.roundRect(x, H-top-h, w, h, radius, fill=1, stroke=0)
    c.restoreState()


def _poly(c, points, fill):
    p = c.beginPath()
    for i, (x, y) in enumerate(points):
        (p.moveTo if i == 0 else p.lineTo)(x, H-y)
    p.close()
    c.setFillColor(fill)
    c.drawPath(p, fill=1, stroke=0)


def _fit(text, w, h, font=R.TESTO, size=10, lead=None, color=NAVY,
         min_size=8.5, bold=False):
    """Measure a text block and return a paragraph that cannot cross its zone."""
    text = _t(str(text or ""))
    font = R.TESTO_B if bold else font
    for step in range(max(0,int((size-min_size)*2))+1):
        sz = max(min_size,size-step*.5)
        style = ParagraphStyle("measured", fontName=font, fontSize=sz,
                               leading=lead or sz*1.25, textColor=color)
        p = Paragraph(text, style)
        _, ph = p.wrap(w, h)
        if ph <= h: return p, ph
    # Source material may be arbitrarily long. Truncate only a secondary card
    # excerpt; the original record remains in the data and optional pages.
    plain = text.replace("<br/>", " ")
    lo, hi = 0, len(plain)
    while lo < hi:
        mid = (lo+hi+1)//2
        p = Paragraph(plain[:mid].rstrip()+"…", style)
        if p.wrap(w, h)[1] <= h: lo = mid
        else: hi = mid-1
    p = Paragraph(plain[:lo].rstrip()+"…", style)
    return p, p.wrap(w, h)[1]


def _text(c, text, x, top, w, h, size=10, font=R.TESTO, color=NAVY,
          min_size=8.5, bold=False):
    p, ph = _fit(text, w, h, font, size, color=color,
                 min_size=min_size, bold=bold)
    p.drawOn(c, x, H-top-ph)
    return ph


def _display(c, text, x, top, width, size=34, color=WHITE, max_lines=2):
    """Display type gets an actual width constraint and a readable floor."""
    text = str(text or "").upper()
    words = text.split()
    for sz in range(size, 16, -1):
        lines = []
        current = ""
        for word in words:
            candidate = (current+" "+word).strip()
            if R.pdfmetrics.stringWidth(candidate, R.TITOLO, sz) <= width:
                current = candidate
            else:
                if current: lines.append(current)
                current = word
        if current: lines.append(current)
        if len(lines) <= max_lines and all(R.pdfmetrics.stringWidth(line,R.TITOLO,sz)<=width for line in lines):
            break
    c.setFillColor(color)
    c.setFont(R.TITOLO, sz)
    for i, line in enumerate(lines[:max_lines]):
        c.drawString(x, H-top-(i+1)*sz*1.02, line)
    return len(lines[:max_lines])*sz*1.02


def _short_title(text, limit=5):
    words=str(text or "").split()
    if len(text or "") <= 54:
        return str(text or "")
    chosen=words[:limit]
    while len(chosen)>2 and chosen[-1].casefold().strip("’'.,:!") in {"di","del","della","a","al","con","per","ti","e"}:
        chosen.pop()
    return " ".join(chosen)


def _cover_headline(c, title, x, top, width, max_height=48*mm):
    """Keep the entire weekly lead dominant without overrunning the deck."""
    words=str(title or "").upper().split()
    remainder=""
    for size in range(44,17,-1):
        lines=[];current=""
        for word in words:
            candidate=(current+" "+word).strip()
            if R.pdfmetrics.stringWidth(candidate,R.TITOLO,size)<=width:
                current=candidate
            else:
                if current: lines.append(current)
                current=word
        if current: lines.append(current)
        height=len(lines)*size*1.04
        if height<=max_height and all(R.pdfmetrics.stringWidth(line,R.TITOLO,size)<=width for line in lines):
            break
    else:
        # Very long source titles keep their complete wording in the deck.
        visible=max(1,int(max_height/(size*1.04)))
        remainder=" ".join(lines[visible:])
        lines=lines[:visible];height=len(lines)*size*1.04
    c.setFillColor(YELLOW);c.setFont(R.TITOLO,size)
    for i,line in enumerate(lines):
        c.drawString(x,H-top-(i+1)*size*1.04,line)
    return height,remainder


def _ribbon(c, label, x, top, w, color=RED, font_size=10):
    h = 9*mm
    _poly(c, [(x,top),(x+w,top),(x+w-5*mm,top+h),(x-2*mm,top+h)], color)
    c.setFont(R.TITOLO, font_size)
    c.setFillColor(WHITE)
    c.drawString(x+3*mm, H-top-6.3*mm, label.upper())


def _scene(c, ctx, dark=False, role=None):
    """Use original illustrated scenes for feature pages, map for other roles."""
    c.setFillColor(colors.HexColor("#70BEDA"))
    c.rect(0, 0, W, H, fill=1, stroke=0)
    scene = SCENE_DIR / f"{role}.jpg" if role else None
    if scene and scene.is_file():
        from PIL import Image
        with Image.open(scene) as im:
            iw, ih = im.size
        scale=max(W/iw,H/ih)
        rw,rh=iw*scale,ih*scale
        c.drawImage(str(scene),(W-rw)/2,(H-rh)/2,rw,rh)
        if dark:
            c.saveState();c.setFillColor(colors.HexColor("#082747"));c.setFillAlpha(.10)
            c.rect(0,0,W,H,fill=1,stroke=0);c.restoreState()
        return
    path = R.ASSET_DIR / (ctx.get("pokemon_mondo", {}).get("map") or "")
    if not path.is_file(): path = R._topographic_map_path()
    try:
        from PIL import Image
        with Image.open(path) as im:
            iw, ih = im.size
        scale = max(W/iw, H/ih)
        rw, rh = iw*scale, ih*scale
        position = (.16,.5,.84)[(c.getPageNumber()-1)%3]
        c.drawImage(str(path), -(rw-W)*position, (H-rh)/2, rw, rh, mask="auto")
    except Exception: pass
    c.saveState()
    c.setFillColor(colors.HexColor("#173A5F") if dark else colors.HexColor("#C3F1F7"))
    c.setFillAlpha(.42 if dark else .27)
    c.rect(0,0,W,H,fill=1,stroke=0)
    c.restoreState()
    # A diagonal field anchors the bottom; it is behind the content.
    c.saveState(); c.setFillAlpha(.36)
    _poly(c,[(0,202*mm),(W,178*mm),(W,H),(0,H)],colors.HexColor("#0769A3"))
    c.restoreState()


def _hero(c, ctx, index, x, top, size, layer_alpha=1):
    assets=ctx.get("pokemon_mondo",{}).get("pokemon") or []
    plan=R._art_piano(ctx,index+1)
    name=plan.get("hero_asset") or (assets[index] if index<len(assets) else None)
    if not name: return
    c.saveState(); c.setFillAlpha(layer_alpha)
    R._immagine_asset(c,name,x,H-top,size)
    c.restoreState()


def _footer(c, ctx, page):
    _poly(c,[(0,283*mm),(W,281*mm),(W,H),(0,H)],colors.HexColor("#06437A"))
    R._logo(c,11*mm,5*mm,30*mm,compact=True)
    c.setFillColor(WHITE); c.setFont(R.TESTO_B,8)
    c.drawRightString(W-9*mm,5*mm,f"N.{ctx['numero']}  /  {page}")


def _header(c, ctx, page, title, subtitle, scene_role=None):
    _scene(c,ctx,role=scene_role)
    _poly(c,[(0,0),(W,0),(W,39*mm),(0,43*mm)],colors.HexColor("#093F80"))
    _poly(c,[(0,43*mm),(W,39*mm),(W,42*mm),(0,46*mm)],YELLOW)
    _display(c,title,11*mm,5*mm,W-22*mm,44,WHITE,1)
    c.setFont(R.TESTO_B,9); c.setFillColor(WHITE)
    c.drawString(13*mm,H-37*mm,subtitle.upper())
    _footer(c,ctx,page)


def _feature_header(c, ctx, page, title, subtitle, scene_role):
    """Let the illustrated setting carry a feature page's display typography."""
    _scene(c,ctx,role=scene_role)
    c.saveState(); c.setFillAlpha(.76)
    _poly(c,[(0,0),(W,0),(W,35*mm),(0,52*mm)],colors.HexColor("#06396E"))
    c.restoreState()
    _display(c,title,10*mm,5*mm,W-20*mm,44,WHITE,1)
    _ribbon(c,subtitle,13*mm,40*mm,min(W-28*mm,132*mm),BLUE,9)


def _section(c, label, x, top, w, color=BLUE):
    _ribbon(c,label,x,top,w,color,9)


def _movement(c, row, x, top, w, color, rank, ctx=None):
    """One ranked movement with a proportional bar, not a tabular row."""
    _, data, period, value = row
    name=data.get("nome", "Prodotto")
    _rect(c,x,top,w,22*mm,WHITE,.94,2*mm)
    image_name = data.get("immagine_carta")
    image_path = R.ASSET_DIR / image_name if image_name else None
    if image_path and image_path.is_file():
        c.drawImage(str(image_path),x+2*mm,H-top-20.5*mm,12.5*mm,17.5*mm,
                    preserveAspectRatio=True,anchor="c")
    else:
        illustration=R._mondo_asset(ctx,"pokemon",rank-1)
        if illustration:
            R._immagine_asset(c,illustration,x+8*mm,H-top-10*mm,16*mm)
        else:
            R._logo(c,x+2*mm,H-top-18*mm,14*mm,compact=True)
    _text(c,name,x+17*mm,top+2.7*mm,w-42*mm,8*mm,9.2,R.TESTO_B)
    ref=data.get("immagine_carta_riferimento")
    if ref and image_path and image_path.is_file():
        marker="≈ " if ref.get("incerto",True) else "✓ "
        _text(c,f"{marker}{ref['set']} · {ref['numero']} · TCGdex",x+17*mm,top+11*mm,w-21*mm,5*mm,
              6.4,R.TESTO_B,BLUE,5.8)
    else:
        _text(c,"Illustrazione tematica",x+17*mm,top+11*mm,w-21*mm,5*mm,
              6.4,R.TESTO_B,BLUE,5.8)
    c.setFont(R.TESTO_B,9); c.setFillColor(color)
    c.drawRightString(x+w-3*mm,H-top-8*mm,f"{value:+.1f}%")
    c.setFillColor(colors.HexColor("#DBE4E9"))
    c.roundRect(x+17*mm,H-top-20*mm,w-22*mm,1.3*mm,.6*mm,stroke=0,fill=1)
    c.setFillColor(color)
    c.roundRect(x+17*mm,H-top-20*mm,max(8*mm,(w-22*mm)*min(abs(value),300)/300),1.3*mm,.6*mm,stroke=0,fill=1)


def _cover(c,ctx):
    visual=ctx.get("cover_visual") or {}
    kind=visual.get("kind","market")
    _scene(c,ctx,True,visual.get("scene","cover"))
    # Water and volcanic diagonal shapes frame the two foreground subjects.
    c.saveState();c.setFillAlpha(.18)
    _poly(c,[(0,108*mm),(57*mm,95*mm),(78*mm,224*mm),(0,230*mm)],BLUE)
    _poly(c,[(W,105*mm),(150*mm,119*mm),(133*mm,219*mm),(W,229*mm)],RED)
    c.restoreState()
    if kind=="community":
        trainer=R._mondo_asset(ctx,"allenatori",0)
        if trainer: R._immagine_asset(c,trainer,50*mm,H-160*mm,145*mm)
        _hero(c,ctx,0,154*mm,157*mm,153*mm)
    elif kind=="sky":
        _hero(c,ctx,0,145*mm,156*mm,185*mm)
    else:
        _hero(c,ctx,0,44*mm,161*mm,177*mm)
    assets=ctx.get("pokemon_mondo",{}).get("pokemon") or []
    companion=visual.get("companion_asset",assets[7] if len(assets)>7 and kind=="market" else None)
    if companion and kind in ("legend","market"):
        R._immagine_asset(c,companion,W-32*mm,H-177*mm,157*mm)
    elif kind not in ("community","sky"):
        ball=R._mondo_asset(ctx,"pokeball",0)
        if ball: R._immagine_asset(c,ball,W-35*mm,H-178*mm,80*mm)
    c.saveState();c.setFillAlpha(.58)
    _poly(c,[(0,0),(80*mm,0),(72*mm,23*mm),(0,23*mm)],colors.HexColor("#082E5E"))
    c.restoreState()
    c.setFillColor(WHITE);c.setFont(R.TITOLO,14)
    c.drawString(8*mm,H-11*mm,f"N.{ctx['numero']}")
    c.setFont(R.TESTO_B,8);c.drawString(8*mm,H-17*mm,ctx.get("data_lunga","").upper())
    R._logo(c,8*mm,H-99*mm,170*mm)
    c.saveState();c.setFillAlpha(.83)
    _poly(c,[(0,220*mm),(W,206*mm),(W,H),(0,H)],colors.HexColor("#062A55"))
    c.restoreState()
    _ribbon(c,"IN PRIMO PIANO",10*mm,216*mm,72*mm,RED,12)
    title=ctx.get("apertura",{}).get("titolo","Il mondo Pokémon TCG")
    used,remainder=_cover_headline(c,title,10*mm,228*mm,W-20*mm)
    deck=(remainder+" · " if remainder else "")+ctx.get("apertura",{}).get("sottotitolo","")
    deck_top=228*mm+used+3*mm
    _text(c,deck,12*mm,deck_top,W-24*mm,H-deck_top-5*mm,10,R.TESTO_B,WHITE)
    c.showPage()


def _market(c,ctx,page):
    g=ctx["principale"]
    _header(c,ctx,page,"MERCATO","Andamenti, trend e opportunità")
    _rect(c,8*mm,66*mm,W-16*mm,63*mm)
    _section(c,"L'ANDAMENTO GENERALE",10*mm,68*mm,89*mm)
    summary=ctx.get("sintesi") or []
    _text(c," ".join(summary[:2]) or "Seguiamo le variazioni del mercato Pokémon TCG.",13*mm,83*mm,86*mm,39*mm,10)
    _section(c,"SEGNALI DELLA SETTIMANA",107*mm,68*mm,91*mm,RED)
    rows=R._top_rows(g,"singola",6)
    for i,row in enumerate(rows[:3]):
        val=row[3]; col=colors.HexColor("#098D60") if val>=0 else RED
        c.setFillColor(col);c.setFont(R.TITOLO,11)
        c.drawString(111*mm,H-(84+i*13)*mm,f"{val:+.1f}%")
        _text(c,row[1].get("nome",""),138*mm,(77+i*13)*mm,57*mm,10*mm,8.5,R.TESTO_B)
    _section(c,"LE CARTE IN MOVIMENTO",9*mm,136*mm,112*mm,BLUE)
    ups=_signed_movements(g,1)
    downs=_signed_movements(g,-1)
    c.setFont(R.TITOLO,14);c.setFillColor(colors.HexColor("#087E5E"));c.drawString(11*mm,H-153*mm,"IN SALITA")
    c.setFillColor(RED);c.drawString(109*mm,H-153*mm,"IN DISCESA")
    for i,row in enumerate(ups): _movement(c,row,9*mm,(158+i*26)*mm,94*mm,colors.HexColor("#087E5E"),i+1,ctx)
    for i,row in enumerate(downs): _movement(c,row,107*mm,(158+i*26)*mm,94*mm,RED,i+1,ctx)
    _rect(c,9*mm,241*mm,138*mm,34*mm,WHITE,.95)
    _section(c,"FOCUS SETTIMANALE",11*mm,242*mm,80*mm)
    _text(c,"≈ Scansione più simile: set e numero sono indicati sotto la carta; stampa Cardmarket da verificare.",
          13*mm,252*mm,129*mm,18*mm,8.5)
    _hero(c,ctx,1,174*mm,247*mm,61*mm)
    c.showPage()


def _signed_movements(g,sign):
    """Rank each direction independently so a strong rise cannot hide falls."""
    found=[]
    groups=(g.get("classifiche") or {}).get("singola") or {}
    for period in (7,30,90,180):
        block=groups.get(str(period)) or {}
        for row in block.get("rialzi" if sign>0 else "ribassi") or []:
            value=(row.get("variazioni") or {}).get(str(period))
            if isinstance(value,(int,float)) and value*sign>0:
                found.append((abs(value),row,period,value))
    found.sort(key=lambda item:item[0],reverse=True)
    result=[];names=set()
    for item in found:
        name=item[1].get("nome")
        if name not in names: result.append(item); names.add(name)
        if len(result)==3: break
    return result


def _news_card(c,n,x,top,w,h,accent=RED):
    _rect(c,x,top,w,h)
    _poly(c,[(x,top),(x+4*mm,top),(x+4*mm,top+h),(x,top+h)],accent)
    sources=n.get("voci")
    if not sources:
        _text(c,n.get("titolo",""),x+7*mm,top+5*mm,w-14*mm,h-20*mm,12,R.TITOLO,min_size=9)
        _text(c,f"{n.get('fonte','')}  ·  {n.get('data','')}",x+7*mm,top+h-13*mm,w-14*mm,9*mm,8,R.TESTO_B,color=BLUE)
        return
    title_h=_text(c,n.get("titolo",""),x+7*mm,top+4*mm,w-14*mm,13*mm,13,R.TITOLO,min_size=10)
    cursor=top+5*mm+title_h
    if n.get("sommario") and h >= 39*mm:
        summary_h=_text(c,n["sommario"],x+7*mm,cursor,w-14*mm,9*mm,8.8)
        cursor+=summary_h+2*mm
    remaining=top+h-3*mm-cursor
    row_h=max(3.7*mm,min(7*mm,remaining/max(len(sources),1)))
    for i,source in enumerate(sources):
        y=cursor+i*row_h
        if y+3*mm>top+h: break
        label=f"{source.get('fonte','')} · {source.get('data','')}  |  {editorial_news.clean_title(source)}"
        _text(c,label,x+7*mm,y,w-14*mm,row_h,7.8,R.TESTO_B,color=BLUE,min_size=7)
        if source.get("link"):
            c.linkURL(source["link"],(x+7*mm,H-y-row_h,x+w-7*mm,H-y),relative=0)


def _news(c,ctx,page):
    g=ctx["principale"]; news=g.get("notizie") or []; radar=g.get("radar") or []
    _header(c,ctx,page,"NOVITÀ","Tutte le news dal mondo Pokémon TCG")
    lead=radar[0] if radar else (news[0] if news else {"titolo":"Le novità della settimana"})
    _rect(c,8*mm,65*mm,W-16*mm,79*mm)
    lead_plain=editorial_news._plain(lead.get("titolo",""))
    label=("EVENTI E COMMUNITY" if any(word in lead_plain for word in ("popcon","fiera","torneo","festival"))
           else "NUOVE USCITE IN ARRIVO")
    _section(c,label,10*mm,68*mm,96*mm,RED)
    lead_title=lead.get("titolo","")
    _display(c,ctx.get("radar_headline") or editorial_news.fallback_headline(lead_title),13*mm,86*mm,106*mm,22,BLUE,3)
    _text(c,editorial_news.clean_title(lead) + " · " + (lead.get("fonte") or "Fonte da verificare"),
          13*mm,114*mm,99*mm,23*mm,9)
    _hero(c,ctx,2,159*mm,103*mm,88*mm)
    _section(c,"STORIE DELLA SETTIMANA",9*mm,150*mm,130*mm,BLUE)
    visible=news[:3]
    if visible:
        available=113*mm-(len(visible)-1)*2*mm
        weights=[max(1,len(n.get("voci") or [])) for n in visible]
        heights=[(available-len(visible)*25*mm)*weight/sum(weights)+25*mm for weight in weights]
        top=163*mm
        for i,(n,height) in enumerate(zip(visible,heights)):
            _news_card(c,n,9*mm,top,W-18*mm,height,RED if i==0 else BLUE)
            top+=height+2*mm
    c.showPage()


def _analysis(c,ctx,page):
    g=ctx["principale"];focus=ctx.get("apertura") or {}
    _feature_header(c,ctx,page,"ANALISI","Approfondimenti e strategie","analysis")
    # Paint the creature before the copy panels. Its silhouette can cross
    # the composition, but never obscure the headline or the measured data.
    _hero(c,ctx,3,167*mm,160*mm,190*mm)
    _rect(c,8*mm,68*mm,118*mm,64*mm,alpha=.92)
    _section(c,"SOTTO LA LENTE",10*mm,70*mm,106*mm,RED)
    title=focus.get("titolo","Analisi della settimana")
    _display(c,_short_title(title),12*mm,85*mm,113*mm,23,BLUE,3)
    _text(c,title if len(title)>54 else focus.get("sottotitolo",""),
          13*mm,112*mm,108*mm,17*mm,9)
    _rect(c,8*mm,146*mm,105*mm,73*mm,alpha=.93)
    _section(c,"SEGNALI DI MERCATO",10*mm,148*mm,94*mm)
    rows=R._top_rows(g,"singola",4)
    for i,row in enumerate(rows[:3]):
        y=(163+i*17)*mm
        _text(c,row[1].get("nome",""),13*mm,y,65*mm,11*mm,9,R.TESTO_B)
        c.setFillColor(BLUE if row[3]>=0 else RED);c.setFont(R.TITOLO,11)
        c.drawRightString(108*mm,H-y-7*mm,f"{row[3]:+.1f}%")
        c.setStrokeColor(colors.HexColor("#ACCBDC"));c.line(13*mm,H-y-14*mm,108*mm,H-y-14*mm)
    _rect(c,9*mm,234*mm,137*mm,42*mm,alpha=.94)
    _section(c,"PERCHÉ È IMPORTANTE",11*mm,236*mm,98*mm,RED)
    _text(c,R._battuta_iniziale(ctx),13*mm,248*mm,127*mm,23*mm,10)
    _footer(c,ctx,page)
    c.showPage()


def _collector(c,ctx,page):
    g=ctx["principale"];occasions=g.get("occasioni") or []
    _header(c,ctx,page,"FOCUS COLLEZIONE","Le carte e i prodotti da tenere d'occhio")
    _rect(c,8*mm,64*mm,W-16*mm,128*mm)
    _section(c,"LA SELEZIONE DELLA SETTIMANA",10*mm,67*mm,119*mm)
    _text(c,"Sigillati del catalogo Cardmarket. Prezzo minimo e sconto rispetto alla tendenza: verifica lingua, stato e inserzione.",13*mm,79*mm,W-28*mm,17*mm,9)
    if not occasions:
        _rect(c,13*mm,104*mm,W-26*mm,70*mm,colors.HexColor("#EAF3F8"))
        _text(c,"Questa settimana non emergono offerte sul sigillato che superino i filtri di prezzo.",
              19*mm,124*mm,W-38*mm,26*mm,13,R.TESTO_B)
    for i,item in enumerate(occasions[:4]):
        x=(12+i*49)*mm; y=99*mm
        _rect(c,x,y,45*mm,86*mm,colors.HexColor("#083F7B"),1,2*mm)
        _rect(c,x+2*mm,y+2*mm,41*mm,46*mm,WHITE,1,1*mm)
        path=R.ASSET_DIR / (item.get("immagine_prodotto") or "")
        if item.get("immagine_prodotto") and path.is_file():
            c.drawImage(str(path),x+4*mm,H-y-46*mm,37*mm,42*mm,
                        preserveAspectRatio=True,anchor="c")
            caption=("≈ Foto simile: " + item.get("immagine_riferimento", "")
                     if item.get("immagine_approssimata") else item.get("fonte_immagine", ""))
            _text(c,caption,x+3*mm,y+43*mm,39*mm,5*mm,6,R.TESTO_B,BLUE,5.5)
        else:
            illustration=R._mondo_asset(ctx,"pokemon",i)
            if illustration:
                R._immagine_asset(c,illustration,x+22*mm,H-y-23*mm,38*mm)
            else:
                R._logo(c,x+5*mm,H-y-42*mm,35*mm,compact=True)
            _text(c,"ILLUSTRAZIONE TEMATICA",x+3*mm,y+43*mm,39*mm,5*mm,
                  6,R.TESTO_B,BLUE,5.5)
        _text(c,item.get("nome") or "Prodotto",x+3*mm,y+50*mm,39*mm,18*mm,8.4,R.TESTO_B,WHITE,7.3)
        c.setFillColor(YELLOW);c.setFont(R.TESTO_B,9)
        c.drawString(x+3*mm,H-y-75*mm,_eur(item.get("prezzo_minimo")))
        c.setFillColor(WHITE);c.setFont(R.TESTO_B,7)
        c.drawRightString(x+42*mm,H-y-75*mm,f"-{item.get('sconto',0):.0f}%")
        if item.get("id"):
            url=f"https://www.cardmarket.com/Pokemon/Products?idProduct={int(item['id'])}"
            c.linkURL(url,(x,H-y-86*mm,x+45*mm,H-y),relative=0)
    _rect(c,9*mm,199*mm,139*mm,72*mm)
    _section(c,"PERCHÉ COLLEZIONARE",11*mm,201*mm,93*mm,RED)
    _text(c,"Ogni scheda rimanda al prodotto Cardmarket. La dicitura «foto simile» indica una confezione di riferimento diversa: controlla prodotto, formato e lingua prima di acquistare.",13*mm,215*mm,128*mm,40*mm,10)
    _hero(c,ctx,4,173*mm,234*mm,76*mm)
    c.showPage()


def _guide(c,ctx,page):
    _feature_header(c,ctx,page,"GUIDA MERCATO","Consigli pratici per collezionisti","guide")
    _rect(c,8*mm,70*mm,115*mm,89*mm,alpha=.91)
    _section(c,"STRATEGIA DELLA SETTIMANA",10*mm,72*mm,110*mm)
    advice=["Controlla lo storico dei prezzi", "Verifica lingua e condizioni", "Confronta le offerte reali", "Considera il rischio di ristampa"]
    for i,a in enumerate(advice):
        yy=91+i*15
        c.setFillColor(colors.HexColor("#0D8D69"));c.setFont(R.TITOLO,16);c.drawString(14*mm,H-yy*mm,"✓")
        _text(c,a,27*mm,(yy-5)*mm,89*mm,13*mm,10,R.TESTO_B)
    _rect(c,129*mm,70*mm,72*mm,89*mm,alpha=.91)
    _section(c,"VERIFICA",131*mm,72*mm,65*mm,RED)
    for i,label in enumerate(("Stampa italiana", "Foto della confezione", "Prezzo filtrato per lingua")):
        _text(c,label,135*mm,(91+i*21)*mm,60*mm,16*mm,9.5,R.TESTO_B)
    trainer=R._mondo_asset(ctx,"allenatori",1)
    if trainer: R._immagine_asset(c,trainer,46*mm,H-230*mm,157*mm)
    _hero(c,ctx,5,70*mm,244*mm,115*mm)
    _rect(c,104*mm,184*mm,96*mm,89*mm,alpha=.93)
    _section(c,"PRIMA DI SCEGLIERE",106*mm,187*mm,91*mm,BLUE)
    text=("Il catalogo identifica il prodotto, ma il prezzo pubblico può includere più lingue. "
          "Per il prezzo italiano serve una verifica delle inserzioni nella lingua richiesta.")
    _text(c,text,109*mm,203*mm,84*mm,58*mm,11)
    _footer(c,ctx,page)
    c.showPage()


def _back(c,ctx):
    _scene(c,ctx,role="back")
    c.saveState();c.setFillAlpha(.74)
    _poly(c,[(0,0),(W,0),(W,37*mm),(0,49*mm)],colors.HexColor("#043B75"))
    c.restoreState()
    _display(c,"IL SALUTO",10*mm,3*mm,W-20*mm,51,WHITE,1)
    _ribbon(c,"GRAZIE PER AVERCI LETTO",12*mm,42*mm,123*mm,BLUE,10)
    _rect(c,10*mm,78*mm,113*mm,53*mm,WHITE,.94)
    _section(c,"ALLA PROSSIMA SETTIMANA",12*mm,80*mm,108*mm,BLUE)
    _text(c,"Continueremo a seguire uscite, movimenti e opportunità del mondo Pokémon TCG. Grazie per aver letto POKèPUTZU WEEKLY!",15*mm,98*mm,103*mm,28*mm,12)
    _hero(c,ctx,6,172*mm,205*mm,162*mm)
    trainer=R._mondo_asset(ctx,"allenatori",2)
    if trainer: R._immagine_asset(c,trainer,110*mm,H-223*mm,132*mm)
    c.saveState();c.setFillColor(colors.HexColor("#062A55"));c.setFillAlpha(.66)
    c.rect(0,0,W,21*mm,stroke=0,fill=1);c.restoreState()
    c.setFillColor(WHITE);c.setFont(R.TITOLO,13)
    c.drawString(13*mm,15*mm,f"N.{ctx['numero']}  ·  CI VEDIAMO AL PROSSIMO NUMERO")
    R._logo(c,W-52*mm,0,43*mm,compact=True)
    c.showPage()


def crea(percorso,ctx,compact=False):
    """Render seven fixed editorial roles, selecting the most relevant stories."""
    Path(percorso).parent.mkdir(parents=True,exist_ok=True)
    c=canvas.Canvas(str(percorso),pagesize=(W,H),pageCompression=1)
    c.setTitle(f"POKèPUTZU WEEKLY n. {ctx['numero']}")
    _cover(c,ctx)
    for i,draw in enumerate((_market,_news,_analysis,_collector,_guide),2):
        draw(c,ctx,i)
    _back(c,ctx)
    c.save()
    ctx["_layout_profile"]={"mode":"editorial", "compact":False,"pages":7}
