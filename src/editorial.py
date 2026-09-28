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

from src import rivista as R
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
    return " ".join(words[:limit]) if len(text or "")>54 else str(text or "")


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
    R._logo(c,11*mm,5*mm,38*mm,compact=True)
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


def _section(c, label, x, top, w, color=BLUE):
    _ribbon(c,label,x,top,w,color,9)


def _movement(c, row, x, top, w, color, rank):
    """One ranked movement with a proportional bar, not a tabular row."""
    _, data, period, value = row
    name=data.get("nome", "Prodotto")
    _rect(c,x,top,w,22*mm,WHITE,.94,2*mm)
    c.setFillColor(color); c.setFont(R.TITOLO,18)
    c.drawString(x+3*mm,H-top-8*mm,f"{rank:02d}")
    _text(c,name,x+17*mm,top+2.7*mm,w-42*mm,10*mm,9.2,R.TESTO_B)
    c.setFont(R.TESTO_B,9); c.setFillColor(color)
    c.drawRightString(x+w-3*mm,H-top-8*mm,f"{value:+.1f}%")
    c.setFillColor(colors.HexColor("#DBE4E9"))
    c.roundRect(x+17*mm,H-top-18*mm,w-22*mm,2.4*mm,1*mm,stroke=0,fill=1)
    c.setFillColor(color)
    c.roundRect(x+17*mm,H-top-18*mm,max(8*mm,(w-22*mm)*min(abs(value),300)/300),2.4*mm,1*mm,stroke=0,fill=1)


def _cover(c,ctx):
    _scene(c,ctx,True,"cover")
    # Water and volcanic diagonal shapes frame the two foreground subjects.
    c.saveState();c.setFillAlpha(.18)
    _poly(c,[(0,108*mm),(57*mm,95*mm),(78*mm,224*mm),(0,230*mm)],BLUE)
    _poly(c,[(W,105*mm),(150*mm,119*mm),(133*mm,219*mm),(W,229*mm)],RED)
    c.restoreState()
    _hero(c,ctx,0,49*mm,157*mm,150*mm)
    assets=ctx.get("pokemon_mondo",{}).get("pokemon") or []
    if len(assets)>7: R._immagine_asset(c,assets[7],W-36*mm,H-169*mm,137*mm)
    else:
        ball=R._mondo_asset(ctx,"pokeball",0)
        if ball: R._immagine_asset(c,ball,W-35*mm,H-178*mm,80*mm)
    c.setFillColor(WHITE);c.setFont(R.TITOLO,14)
    c.drawString(8*mm,H-11*mm,f"N.{ctx['numero']}")
    c.setFont(R.TESTO_B,8);c.drawString(8*mm,H-17*mm,ctx.get("data_lunga","").upper())
    R._logo(c,8*mm,H-49*mm,W-16*mm)
    c.saveState();c.setFillAlpha(.83)
    _poly(c,[(0,220*mm),(W,206*mm),(W,H),(0,H)],colors.HexColor("#062A55"))
    c.restoreState()
    _ribbon(c,"IN PRIMO PIANO",10*mm,213*mm,72*mm,RED,12)
    title=ctx.get("apertura",{}).get("titolo","Il mondo Pokémon TCG")
    headline=_short_title(title)
    used=_display(c,headline,10*mm,225*mm,W-20*mm,43,YELLOW,2)
    deck=title if headline!=title else ctx.get("apertura",{}).get("sottotitolo","")
    _text(c,deck,12*mm,230*mm+used,W-24*mm,20*mm,10,R.TESTO_B,WHITE)
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
    for i,row in enumerate(ups): _movement(c,row,9*mm,(158+i*26)*mm,94*mm,colors.HexColor("#087E5E"),i+1)
    for i,row in enumerate(downs): _movement(c,row,107*mm,(158+i*26)*mm,94*mm,RED,i+1)
    _rect(c,9*mm,241*mm,138*mm,34*mm,WHITE,.95)
    _section(c,"FOCUS SETTIMANALE",11*mm,242*mm,80*mm)
    _text(c,ctx.get("apertura",{}).get("sottotitolo",""),13*mm,252*mm,129*mm,18*mm,9)
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
    _text(c,n.get("titolo",""),x+7*mm,top+5*mm,w-14*mm,h-20*mm,12,R.TITOLO,min_size=9)
    _text(c,f"{n.get('fonte','')}  ·  {n.get('data','')}",x+7*mm,top+h-13*mm,w-14*mm,9*mm,8,R.TESTO_B,color=BLUE)


def _news(c,ctx,page):
    g=ctx["principale"]; news=g.get("notizie") or []; radar=g.get("radar") or []
    _header(c,ctx,page,"NOVITÀ","Tutte le news dal mondo Pokémon TCG")
    lead=radar[0] if radar else (news[0] if news else {"titolo":"Le novità della settimana"})
    _rect(c,8*mm,65*mm,W-16*mm,79*mm)
    _section(c,"NUOVE USCITE IN ARRIVO",10*mm,68*mm,96*mm,RED)
    lead_title=lead.get("titolo","")
    _display(c,_short_title(lead_title),13*mm,86*mm,106*mm,22,BLUE,3)
    _text(c,lead_title if len(lead_title)>54 else
          (lead.get("fonte") or "Date e dettagli da verificare"),
          13*mm,114*mm,99*mm,23*mm,9)
    _hero(c,ctx,2,159*mm,103*mm,88*mm)
    _section(c,"ANNUNCI UFFICIALI E SEGNALI",9*mm,150*mm,130*mm,BLUE)
    for i,n in enumerate(news[:3]):
        _news_card(c,n,9*mm,(163+i*34)*mm,139*mm,30*mm,RED if i==0 else BLUE)
    item=R._mondo_asset(ctx,"oggetti",0)
    if item: R._immagine_asset(c,item,178*mm,H-220*mm,70*mm)
    c.showPage()


def _analysis(c,ctx,page):
    g=ctx["principale"];focus=ctx.get("apertura") or {}
    _header(c,ctx,page,"ANALISI","Approfondimenti e strategie",scene_role="analysis")
    _rect(c,8*mm,65*mm,124*mm,68*mm,alpha=.92)
    _section(c,"CARTA / PRODOTTO PROTAGONISTA",10*mm,68*mm,116*mm,RED)
    title=focus.get("titolo","Analisi della settimana")
    _display(c,_short_title(title),12*mm,85*mm,113*mm,23,BLUE,3)
    _text(c,title if len(title)>54 else focus.get("sottotitolo",""),
          13*mm,112*mm,108*mm,17*mm,9)
    # The protagonist crosses the central horizon while data remains in a
    # measured safe zone on the left.
    _hero(c,ctx,3,160*mm,156*mm,145*mm)
    _rect(c,8*mm,143*mm,113*mm,75*mm,alpha=.93)
    _section(c,"DATI PRINCIPALI",10*mm,145*mm,82*mm)
    rows=R._top_rows(g,"singola",4)
    for i,row in enumerate(rows[:3]):
        y=(159+i*18)*mm
        _text(c,row[1].get("nome",""),13*mm,y,74*mm,11*mm,9,R.TESTO_B)
        c.setFillColor(BLUE if row[3]>=0 else RED);c.setFont(R.TITOLO,11)
        c.drawRightString(113*mm,H-y-7*mm,f"{row[3]:+.1f}%")
        c.setStrokeColor(colors.HexColor("#ACCBDC"));c.line(13*mm,H-y-14*mm,113*mm,H-y-14*mm)
    _rect(c,9*mm,226*mm,145*mm,48*mm,alpha=.94)
    _section(c,"PERCHÉ È IMPORTANTE",11*mm,228*mm,98*mm,RED)
    _text(c,R._battuta_iniziale(ctx),13*mm,241*mm,136*mm,27*mm,10)
    c.showPage()


def _collector(c,ctx,page):
    g=ctx["principale"];occasions=g.get("occasioni") or []
    _header(c,ctx,page,"FOCUS COLLEZIONE","Le carte e i prodotti da tenere d'occhio")
    _rect(c,8*mm,64*mm,W-16*mm,128*mm)
    _section(c,"LA SELEZIONE DELLA SETTIMANA",10*mm,67*mm,119*mm)
    _text(c,"Prodotti e segnali osservati questa settimana, con prezzi e sconti da verificare per lingua e condizione.",13*mm,79*mm,W-28*mm,17*mm,9)
    assets=ctx.get("pokemon_mondo",{}).get("pokemon") or []
    for i in range(4):
        x=(12+i*49)*mm; y=100*mm
        _rect(c,x,y,45*mm,79*mm,colors.HexColor("#083F7B"),1,2*mm)
        _rect(c,x+2*mm,y+2*mm,41*mm,56*mm,colors.HexColor("#CEE8F1"),1,1*mm)
        if len(assets)>i+8:
            R._immagine_asset(c,assets[i+8],x+22.5*mm,H-y-30*mm,42*mm)
        else:
            item=R._mondo_asset(ctx,"oggetti" if i%2 else "pokeball",i)
            if item: R._immagine_asset(c,item,x+22.5*mm,H-y-30*mm,40*mm)
        item=occasions[i] if i<len(occasions) else {}
        label=item.get("nome") or f"Segnale {i+1}"
        _text(c,label,x+3*mm,y+59*mm,39*mm,14*mm,8.2,R.TESTO_B,WHITE,8)
        if item:
            c.setFillColor(YELLOW);c.setFont(R.TESTO_B,8)
            c.drawString(x+3*mm,H-y-76*mm,_eur(item.get("prezzo_minimo",0)))
    _rect(c,9*mm,199*mm,139*mm,72*mm)
    _section(c,"PERCHÉ COLLEZIONARE",11*mm,201*mm,93*mm,RED)
    _text(c,"Una selezione ragionata: confronta prezzo, disponibilità, lingua e stato prima di acquistare.",13*mm,215*mm,128*mm,40*mm,10)
    _hero(c,ctx,4,173*mm,234*mm,76*mm)
    c.showPage()


def _guide(c,ctx,page):
    g=ctx["principale"];car=g.get("carrello") or {}; proposals=car.get("proposte") or []
    _header(c,ctx,page,"GUIDA MERCATO","Consigli pratici per collezionisti",scene_role="guide")
    _rect(c,8*mm,66*mm,116*mm,98*mm,alpha=.91)
    _section(c,"STRATEGIA DELLA SETTIMANA",10*mm,69*mm,110*mm)
    advice=["Controlla lo storico dei prezzi", "Verifica lingua e condizioni", "Confronta le offerte reali", "Considera il rischio di ristampa"]
    for i,a in enumerate(advice):
        yy=88+i*17
        c.setFillColor(colors.HexColor("#0D8D69"));c.setFont(R.TITOLO,16);c.drawString(14*mm,H-yy*mm,"✓")
        _text(c,a,27*mm,(yy-5)*mm,89*mm,13*mm,10,R.TESTO_B)
    _rect(c,129*mm,66*mm,72*mm,98*mm,alpha=.91)
    _section(c,"RISCHIO",131*mm,69*mm,65*mm,RED)
    for i,(label,pct,col) in enumerate((("BASSO",.30,colors.HexColor("#1DAD6D")),("MEDIO",.53,YELLOW),("ALTO",.20,RED))):
        y=(91+i*22)*mm
        c.setFillColor(NAVY);c.setFont(R.TESTO_B,9);c.drawString(135*mm,H-y,label)
        c.setFillColor(colors.HexColor("#D9E4EB"));c.roundRect(135*mm,H-y-8*mm,58*mm,5*mm,2*mm,fill=1,stroke=0)
        c.setFillColor(col);c.roundRect(135*mm,H-y-8*mm,58*mm*pct,5*mm,2*mm,fill=1,stroke=0)
    trainer=R._mondo_asset(ctx,"allenatori",1)
    if trainer: R._immagine_asset(c,trainer,33*mm,H-225*mm,117*mm)
    _hero(c,ctx,5,67*mm,235*mm,81*mm)
    _rect(c,97*mm,182*mm,103*mm,90*mm,alpha=.93)
    _section(c,"CONSIGLIO DELL'ESPERTO",99*mm,185*mm,99*mm,BLUE)
    if proposals:
        text=f"Prima ipotesi: {proposals[0].get('nome','')}. Prezzo indicato: {_eur(proposals[0].get('prezzo',0))}. Controlla i dettagli dell'inserzione."
    else:
        text="Questa settimana conviene osservare i segnali. Un prezzo basso da solo non dimostra che l'acquisto sia una buona occasione."
    _text(c,text,102*mm,202*mm,93*mm,58*mm,11)
    c.showPage()


def _continuation(c,ctx,page,title,records,kind):
    _header(c,ctx,page,title,"Approfondimenti della settimana")
    _section(c,"ALTRE SEGNALAZIONI",10*mm,68*mm,106*mm,RED)
    for i,record in enumerate(records):
        top=(81+i*30)*mm
        if kind=="news": _news_card(c,record,10*mm,top,W-20*mm,27*mm)
        else:
            _rect(c,10*mm,top,W-20*mm,27*mm)
            _text(c,record.get("nome",""),14*mm,top+4*mm,126*mm,16*mm,11,R.TESTO_B)
            _text(c,f"Offerta {_eur(record.get('prezzo_minimo',0))}  ·  Tendenza {_eur(record.get('prezzo_tendenza',0))}",14*mm,top+21*mm,153*mm,9*mm,8.5)
            c.setFillColor(RED);c.setFont(R.TITOLO,13)
            c.drawRightString(W-15*mm,H-top-12*mm,f"-{record.get('sconto',0):.1f}%")
    if len(records)<6:
        top=(86+len(records)*30)*mm
        height=275*mm-top
        if height>20*mm:
            _rect(c,10*mm,top,W-20*mm,height,WHITE,.92)
            _section(c,"DA TENERE D'OCCHIO",12*mm,top+2*mm,91*mm,BLUE)
            message=("Segui le fonti e verifica date e disponibilità prima di considerare un'uscita confermata."
                     if kind=="news" else
                     "Prezzi e sconti vanno verificati su Cardmarket: lingua, condizione e spedizione cambiano il risultato.")
            _text(c,message,15*mm,top+14*mm,129*mm,height-18*mm,9.5)
            item=R._mondo_asset(ctx,"oggetti",page)
            if item: R._immagine_asset(c,item,W-34*mm,H-top-height/2,35*mm)
    c.showPage()


def _back(c,ctx):
    _scene(c,ctx,role="back")
    c.saveState();c.setFillAlpha(.66)
    _poly(c,[(0,0),(W,0),(W,53*mm),(0,61*mm)],colors.HexColor("#043B75"))
    c.restoreState()
    _display(c,"IL SALUTO",10*mm,6*mm,W-20*mm,46,WHITE,1)
    R._logo(c,11*mm,H-82*mm,122*mm)
    _rect(c,11*mm,104*mm,112*mm,57*mm,WHITE,.94)
    _section(c,"ALLA PROSSIMA SETTIMANA",12*mm,106*mm,108*mm,BLUE)
    _text(c,"Continueremo a seguire uscite, movimenti e opportunità del mondo Pokémon TCG. Grazie per aver letto POKèPUTZU WEEKLY!",16*mm,121*mm,100*mm,34*mm,11)
    _hero(c,ctx,6,164*mm,217*mm,127*mm)
    trainer=R._mondo_asset(ctx,"allenatori",2)
    if trainer: R._immagine_asset(c,trainer,113*mm,H-223*mm,115*mm)
    c.saveState();c.setFillColor(colors.HexColor("#062A55"));c.setFillAlpha(.66)
    c.rect(0,0,W,21*mm,stroke=0,fill=1);c.restoreState()
    c.setFillColor(WHITE);c.setFont(R.TITOLO,13)
    c.drawString(13*mm,15*mm,f"N.{ctx['numero']}  ·  CI VEDIAMO AL PROSSIMO NUMERO")
    c.showPage()


def crea(percorso,ctx,compact=False):
    """Render the core story plus measured continuation pages as needed."""
    Path(percorso).parent.mkdir(parents=True,exist_ok=True)
    c=canvas.Canvas(str(percorso),pagesize=(W,H),pageCompression=1)
    c.setTitle(f"POKèPUTZU WEEKLY n. {ctx['numero']}")
    _cover(c,ctx)
    for i,draw in enumerate((_market,_news,_analysis,_collector,_guide),2):
        draw(c,ctx,i)
    page=7
    g=ctx["principale"]
    for kind,title,records,start in (("news","NOVITÀ",g.get("notizie") or [],3),
                                    ("offers","FOCUS COLLEZIONE",g.get("occasioni") or [],4)):
        for j in range(start,len(records),6):
            _continuation(c,ctx,page,title,records[j:j+6],kind)
            page+=1
    _back(c,ctx)
    c.save()
    ctx["_layout_profile"]={"mode":"editorial", "compact":False,"pages":page}
