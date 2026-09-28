"""Art director Gemini per POKEPUTZU WEEKLY."""
import json, os
from pathlib import Path
MODEL=os.getenv("GEMINI_MODEL","gemini-3.5-flash-lite")
SCHEMA={"type":"object","properties":{"region":{"type":"string"},"visual_direction":{"type":"string"},"palette":{"type":"array","items":{"type":"string"}},"radar_headline":{"type":"string"},"news_headlines":{"type":"array","items":{"type":"object","properties":{"group":{"type":"integer"},"headline":{"type":"string"},"summary":{"type":"string"}},"required":["group","headline","summary"]}},"pages":{"type":"array","items":{"type":"object","properties":{"page":{"type":"integer"},"layout":{"type":"string"},"hero_pokemon":{"type":"string"},"secondary_pokemon":{"type":"array","items":{"type":"string"}},"map":{"type":"string"},"ui":{"type":"string"},"notes":{"type":"string"}},"required":["page","layout","hero_pokemon","secondary_pokemon","map","ui","notes"]}}},"required":["region","visual_direction","palette","pages","radar_headline","news_headlines"]}
def _local_plan(issue_number,region,available_pokemon=None):
 layouts=[("cover","hoenn_map_01","pokedex"),("editorial","hoenn_map_02","dialogue"),("radar","hoenn_map_03","battle"),("thermometer","hoenn_map_01","trainer_card"),("market","hoenn_map_02","pokedex"),("deals_news","hoenn_map_03","dialogue"),("back_cover","hoenn_map_01","menu")]
 disponibili=list(available_pokemon or [])
 return {"region":region,"visual_direction":"Magazine illustrato moderno e dinamico: grandi artwork, mappe ambientali, gerarchia editoriale forte, forme diagonali e colore controllato; niente pixel, sprite, scanline o finte UI da videogioco.","palette":["blu editoriale","giallo caldo","rosso corallo","azzurro cielo","bianco caldo"],"pages":[{"page":i,"layout":a,"hero_pokemon":(disponibili[(i-1)%len(disponibili)] if disponibili else ""), "secondary_pokemon":[],"map":m,"ui":u,"notes":"Pokémon protagonista; composizione adattiva alla densità; niente pixel art, sprite o griglie da videogioco."} for i,(a,m,u) in enumerate(layouts,1)]}
def _normalize(plan,region):
 plan=dict(plan or {}); plan["region"]=region; pages=list(plan.get("pages") or [])[:7]; used=set(); out=[]
 for i,p in enumerate(pages,1):
  p=dict(p); hero=str(p.get("hero_pokemon",""))
  if hero.lower() in used: hero=""
  if hero: used.add(hero.lower())
  p.update(page=i,hero_pokemon=hero,secondary_pokemon=list(p.get("secondary_pokemon") or [])); out.append(p)
 plan["pages"]=out; return plan
def genera_piano(issue_number,region="hoenn",available_pokemon=None,content_titles=None,news_groups=None,radar_title=""):
 fallback=_local_plan(issue_number,region,available_pokemon); key=os.getenv("GEMINI_API_KEY")
 if not key: return fallback
 try:
  from google import genai
  from google.genai import types
  # The art direction is optional: an overloaded model must never stall the
  # weekly PDF for the full GitHub Actions job timeout.
  client=genai.Client(api_key=key,http_options=types.HttpOptions(timeout=20000))
  elenco=", ".join(available_pokemon or [])
  contenuti="; ".join(content_titles or [])
  notizie="\n".join(f"Gruppo {i}: " + " | ".join(f"{v.get('titolo','')} [{v.get('fonte','')}, {v.get('data','')}]" for v in group.get("voci",[]))
                      for i,group in enumerate(news_groups or []))
  prompt=f"""Sei l'art director di POKEPUTZU WEEKLY, magazine settimanale Pokémon TCG. Numero {issue_number}, regione protagonista {region}.
Progetta i cinque ruoli editoriali principali più cover e quarta su A4 VERTICALI. Il renderer aggiunge pagine di approfondimento quando i contenuti lo richiedono. Cerca la grammatica di un magazine illustrato: cover cinematografica, titoli display enormi, ribbon blu/rosso/giallo, mappe e paesaggi come sfondo full-bleed, pannelli bianchi solo per rendere leggibili testi e dati, artwork che entra nella composizione e infografiche editoriali.
NON usare pixel art, sprite, scanline, griglie, finte schermate Pokédex/battaglia o estetica da report aziendale. Scegli per ogni pagina un template visual, balanced o data-heavy in base alla quantità di contenuto. Tutte le pagine devono restare verticali.
Il Pokémon deve essere protagonista visivo, grande e associato alla pagina. Varia le composizioni e non ripetere hero Pokémon. La copertina dà priorità al titolo di apertura reale: abbina il soggetto e lo scenario al tema della notizia; per eventi della community usa l'allenatore e la città costiera, per creature nominate usa quella creatura se disponibile, per notizie generali usa l'iconografia di Hoenn. Il renderer applica questa scelta editoriale in modo deterministico anche quando il modello non è disponibile. Gli scenari originali di costa vulcanica, rovine aeree, città costiera e tramonto sono già disponibili: prevedi aree sicure per artwork e testo.
ASSET POKÉMON DISPONIBILI: {elenco}
CONTENUTI EDITORIALI: {contenuti}
RADAR, TITOLO ORIGINALE: {radar_title}
ARTICOLI RAGGRUPPATI PER TEMA (ogni titolo e fonte deve restare identificabile nel PDF):
{notizie}
Scrivi radar_headline di massimo 65 caratteri e una news_headlines per ogni gruppo, con indice group esatto, headline di massimo 65 caratteri e summary di massimo 140. Sintetizza soltanto fatti presenti nei titoli originali: non inventare date, prodotti, percentuali o annunci. Distingui eventi da uscite commerciali. Le fonti originali saranno stampate dal renderer sotto ogni sintesi.
Scegli gli hero solo dagli asset disponibili. Usa mappe/UI dichiarate dal sistema. Solo JSON conforme allo schema."""
  r=client.models.generate_content(model=MODEL,contents=prompt,config=types.GenerateContentConfig(response_mime_type="application/json",response_schema=SCHEMA,temperature=0.7))
  return _normalize(json.loads(r.text),region)
 except Exception as e:
  print(f"[art_director] fallback: {e}"); return fallback
def salva_piano_test(issue_number=1,region="hoenn",path="data/art_direction_test.json"):
 p=genera_piano(issue_number,region); Path(path).parent.mkdir(exist_ok=True); Path(path).write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding="utf-8"); return p
