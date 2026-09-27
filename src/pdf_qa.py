"""QA strutturale per POKEPUTZU WEEKLY."""
from pathlib import Path

def check(path, expected_pages=7):
    result={"ok":False,"pages":0,"errors":[]}
    p=Path(path)
    if not p.exists() or p.stat().st_size<10000:
        result["errors"].append("PDF mancante o troppo piccolo"); return result
    try:
        import fitz
        doc=fitz.open(str(p)); result["pages"]=len(doc)
        if len(doc)!=expected_pages: result["errors"].append(f"pagine: {len(doc)} invece di {expected_pages}")
        for i,page in enumerate(doc):
            rect=page.rect; text=page.get_text("text").strip()
            if i not in (0,expected_pages-1) and len(text)<80: result["errors"].append(f"pagina {i+1}: testo troppo scarso")
            for block in page.get_text("blocks"):
                x0,y0,x1,y1=block[:4]
                if x0 < -2 or y0 < -2 or x1 > rect.width+2 or y1 > rect.height+2:
                    result["errors"].append(f"pagina {i+1}: testo fuori pagina"); break
        doc.close()
    except Exception as e: result["errors"].append(f"lettura PDF: {e}")
    result["ok"]=not result["errors"]; return result
