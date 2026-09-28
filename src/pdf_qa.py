"""QA strutturale per POKEPUTZU WEEKLY."""
from pathlib import Path

def check(path, expected_pages=None, image_audit=None):
    result={"ok":False,"pages":0,"errors":[]}
    p=Path(path)
    if not p.exists() or p.stat().st_size<10000:
        result["errors"].append("PDF mancante o troppo piccolo"); return result
    try:
        import fitz
        doc=fitz.open(str(p)); result["pages"]=len(doc)
        if expected_pages is not None and len(doc)!=expected_pages:
            result["errors"].append(f"pagine: {len(doc)} invece di {expected_pages}")
        if len(doc)<7: result["errors"].append(f"pagine insufficienti: {len(doc)}")
        for i,page in enumerate(doc):
            rect=page.rect; text=page.get_text("text").strip()
            if abs(rect.width-595.28)>1 or abs(rect.height-841.89)>1:
                result["errors"].append(f"pagina {i+1}: formato non A4 verticale")
            if i not in (0,len(doc)-1) and len(text)<80: result["errors"].append(f"pagina {i+1}: testo troppo scarso")
            for block in page.get_text("blocks"):
                x0,y0,x1,y1=block[:4]
                if x0 < -2 or y0 < -2 or x1 > rect.width+2 or y1 > rect.height+2:
                    result["errors"].append(f"pagina {i+1}: testo fuori pagina"); break
        if image_audit and len(doc) >= 5:
            market = doc[1].get_text("text")
            focus = doc[4].get_text("text").lower()
            if image_audit.get("card_approximate") and "≈" not in market:
                result["errors"].append("manca la didascalia delle scansioni inferite")
            if image_audit.get("product_approximate") and focus.count("foto simile") < 2:
                result["errors"].append("manca la didascalia delle foto di prodotto simili")
        doc.close()
    except Exception as e: result["errors"].append(f"lettura PDF: {e}")
    result["ok"]=not result["errors"]; return result


def render_review(path, output_dir):
    """Save the two pages containing real card and product imagery for QA."""
    import fitz
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with fitz.open(str(path)) as doc:
        for index in (1, 4):
            if index < len(doc):
                doc[index].get_pixmap(matrix=fitz.Matrix(1.25, 1.25), alpha=False).save(
                    str(output_dir / f"page_{index + 1}.png"))
