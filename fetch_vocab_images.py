#!/usr/bin/env python3
"""Download real pictures for vocab words from Wikipedia / Wikimedia Commons.

For every vocab term the English translation (or a hand-written override query)
is looked up:
  1. English Wikipedia article with that title -> its lead image,
  2. otherwise a Wikimedia Commons file search (bitmap photos only).
Images are saved as images/<key>.jpg, the generated placeholder <key>.png is
removed, and images/word_map.json + images/CREDITS.json are updated.
Lowercase override queries skip Wikipedia (they are descriptive photo searches).
Words with no result keep (or get) a generated placeholder card.
"""
import argparse
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

from download_vocab_images import create_card_image, normalize_image_key
from md_flashcards import load_entries

USER_AGENT = "SpanishStudyFlashcards/1.0 (personal study tool; python-requests)"
WIKI_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
THUMB_WIDTH = 500

# Search queries for words whose English translation is abstract or ambiguous.
# Keys are normalize_image_key(spanish term).
QUERY_OVERRIDES = {
    "hola": "waving hello",
    "buenos_dias": "sunrise morning",
    "buenas_tardes": "afternoon sun park",
    "buenas_noches": "night sky moon",
    "adios": "waving goodbye",
    "hasta_luego": "waving goodbye friends",
    "hasta_manana": "alarm clock",
    "nos_vemos": "friends meeting hug",
    "por_favor": "please sign",
    "gracias": "thank you card",
    "muchas_gracias": "thank you",
    "de_nada": "handshake",
    "perdon": "sorry",
    "lo_siento": "sad face",
    "que_tal": "friends talking",
    "como_estas": "conversation two people",
    "bien": "thumbs up",
    "muy_bien": "thumbs up smile",
    "mal": "thumbs down",
    "mas_o_menos": "Shrug",
    "el_nombre": "name tag",
    "el_apellido": "family name",
    "apellido": "family name",
    "la_edad": "birthday cake candles",
    "la_nacionalidad": "passport",
    "el_pais": "political world map",
    "la_direccion": "house number address",
    "el_correo_electronico": "email",
    "llamarse": "name tag hello my name is",
    "ser": "portrait person",
    "tener": "holding in hands",
    "vivir": "family home",
    "hablar": "people talking",
    "estudiar": "student studying books",
    "trabajar": "office work",
    "conocer": "people meeting handshake",
    "como_te_llamas": "name tag hello my name is",
    "me_llamo": "name tag hello my name is",
    "de_donde_eres": "globe",
    "soy_de": "globe",
    "donde_vives": "residential street houses",
    "vivo_en": "residential street houses",
    "cuantos_anos_tienes": "birthday cake candles",
    "tengo_anos": "birthday cake candles",
    "que_idiomas_hablas": "language flags",
    "hablo": "language flags",
    "espanol_espanola": "Flag of Spain",
    "polaco_polaca": "Flag of Poland",
    "aleman_alemana": "Flag of Germany",
    "frances_francesa": "Flag of France",
    "italiano_italiana": "Flag of Italy",
    "portugues_portuguesa": "Flag of Portugal",
    "ingles_inglesa": "Flag of England",
    "estadounidense": "Flag of the United States",
    "mexicano_mexicana": "Flag of Mexico",
    "argentino_argentina": "Flag of Argentina",
    "el_profesor_la": "Teacher",
    "profesora": "female teacher classroom",
    "el_estudiante_la": "Student",
    "estudiante": "female student university",
    "el_medico_la_medica": "Physician",
    "el_enfermero_la": "Nurse",
    "enfermera": "nurse hospital",
    "el_abogado_la_abogada_lawyer": "Lawyer",
    "el_camarero_la_camarera": "Waiting staff",
    "el_cocinero_la_cocinera": "Chef",
    "el_periodista_la": "Journalist",
    "periodista": "journalist microphone",
    "el_ingeniero_la_ingeniera": "Engineer",
    "el_arquitecto_la_arquitecta": "Architect",
    "el_policia_la_policia_police_officer": "Police officer",
    "el_secretario_la_secretaria": "Secretary",
    "el_dependiente_la": "Sales assistant",
    "dependienta": "shop assistant store",
    "la_clase": "Classroom",
    "el_profesor": "Teacher",
    "el_alumno": "Pupil",
    "alumnos": "pupils classroom",
    "la_goma": "Eraser",
    "borrador": "Eraser",
    "la_pizarra": "Blackboard",
    "el_cartel": "Poster",
    "cartel": "Poster",
    "la_planta": "Houseplant",
    "escribir": "Handwriting",
    "leer": "Reading",
    "escuchar": "Listening",
    "repetir": "repeat",
    "preguntar": "raising hand question classroom",
    "responder": "answer question classroom",
    "abrir": "open door",
    "cerrar": "closed door",
    "naranja": "Orange (colour)",
    "rosa": "Pink",
    "gris": "Grey",
    "marron": "Brown",
    "morado": "Purple",
    "el_piso": "Apartment",
    "la_habitacion": "Room",
    "el_salon": "Living room",
    "el_bano": "Bathroom",
    "el_comedor": "Dining room",
    "la_nevera": "Refrigerator",
    "estar": "person standing in room",
    "hay": "fruit bowl",
    "haber_hay": "fruit bowl",
    "aqui": "you are here sign",
    "alli": "pointing finger",
    "encima_de": "cat on top of table",
    "encima_de_sobre": "cat on top of table",
    "debajo_de": "cat under table",
    "delante_de": "car in front of house",
    "detras_de": "hiding behind tree",
    "al_lado_de": "two chairs side by side",
    "entre": "between two trees",
    "dentro_de": "cat inside box",
    "fuera_de": "cat outside box",
    "cerca_de": "near",
    "lejos_de": "far away road horizon",
    "alto": "tall man basketball",
    "bajo": "short person",
    "joven": "Youth",
    "mayor": "Old age",
    "guapo": "handsome man portrait",
    "guapa": "beautiful woman portrait",
    "delgado": "slim man",
    "gordo": "overweight man",
    "fuerte": "strong man weightlifting",
    "el_pelo": "Hair",
    "largo": "long hair",
    "corto": "short hair",
    "rubio": "Blond",
    "moreno": "black hair",
    "pelirrojo": "Red hair",
    "liso": "straight hair",
    "rizado": "curly hair",
    "los_ojos": "Eye",
    "llevar": "wearing hat",
    "las_gafas": "Glasses",
    "simpatico": "friendly smile",
    "antipatico": "angry face",
    "amable": "kindness helping",
    "divertido": "laughing friends",
    "serio": "serious face",
    "tranquilo": "calm lake",
    "nervioso": "nervous person",
    "timido": "shy child",
    "abierto": "open sign",
    "trabajador": "Worker",
    "inteligente": "Intelligence",
    "generoso": "giving gift",
    "alegre": "happy smile",
    "la_ropa": "Clothing",
    "el_jersey": "Sweater",
    "los_pantalones": "Trousers",
    "las_zapatillas": "Sneakers",
    "la_gorra": "Baseball cap",
    "el_hijo": "son boy father",
    "la_hija": "daughter girl mother",
    "el_hermano": "brothers boys",
    "la_hermana": "sisters girls",
    "el_marido": "Husband",
    "la_mujer": "Wife",
    "el_abuelo": "grandfather",
    "la_abuela": "grandmother",
    "el_tio": "Uncle",
    "la_tia": "Aunt",
    "el_primo": "Cousin",
    "la_prima": "Cousin",
    "el_nieto": "grandson grandfather",
    "la_nieta": "granddaughter grandmother",
    "casado": "wedding couple",
    "soltero": "man alone",
    "divorciado": "Divorce",
    "despertarse": "waking up alarm clock",
    "levantarse": "getting out of bed",
    "ducharse": "Shower",
    "vestirse": "getting dressed",
    "desayunar": "Breakfast",
    "salir_de_casa": "leaving house front door",
    "ir_al_trabajo": "Commuting",
    "empezar": "start line race",
    "terminar": "finish line",
    "comer": "Eating",
    "volver": "coming home",
    "cenar": "Dinner",
    "acostarse": "going to bed",
    "dormir": "Sleep",
    "la_hora": "Clock",
    "que_hora_es": "Clock",
    "es_la_una": "clock one o'clock",
    "son_las_dos": "clock two o'clock",
    "y_cuarto": "clock quarter past",
    "y_media": "clock half past",
    "menos_cuarto": "clock quarter to",
    "por_la_manana": "Morning",
    "por_la_tarde": "Afternoon",
    "por_la_noche": "Night",
    "el_tiempo_libre": "Leisure",
    "gustar": "Like button",
    "encantar": "Heart",
    "preferir": "choice",
    "querer": "desire",
    "poder": "Ability",
    "jugar": "Play (activity)",
    "hacer_deporte": "Sport",
    "correr": "Running",
    "nadar": "Swimming",
    "bailar": "Dance",
    "cantar": "Singing",
    "viajar": "Travel",
    "cocinar": "Cooking",
    "dibujar": "Drawing",
    "pasear": "Walking",
    "montar_en_bicicleta": "Cycling",
    "escuchar_musica": "Headphones",
    "ver_la_television": "watching television",
    "ver_una_pelicula": "Movie theater",
    "leer_un_libro": "Reading",
    "quedar_con_amigos": "Friendship",
    "ir_al_cine": "Movie theater",
    "ir_de_compras": "Shopping",
    "el_futbol": "Association football",
    "el_baloncesto": "Basketball",
    "el_gimnasio": "Gym",
    "el_cine": "Movie theater",
    "el_teatro": "Theatre",
    "la_calle": "Street",
    "la_plaza": "Town square",
    "el_centro": "City centre",
    "el_barrio": "Neighbourhood",
    "barrio": "Neighbourhood",
    "el_banco": "Bank",
    "la_farmacia": "Pharmacy (shop)",
    "la_tienda": "Retail",
    "el_bar": "Bar (establishment)",
    "la_estacion": "Train station",
    "la_iglesia": "Church (building)",
    "el_parque": "Park",
    "la_oficina_de_correos": "Post office",
    "a_la_derecha": "right arrow sign",
    "a_la_izquierda": "left arrow sign",
    "a_la_derecha_de": "right arrow sign",
    "a_la_izquierda_de": "left arrow sign",
    "todo_recto": "straight ahead road",
    "cruzar": "Pedestrian crossing",
    "girar": "turn sign road",
    "seguir": "road continue",
    "llegar": "arrival airport",
    "buscar": "Magnifying glass",
    "donde_esta": "Map",
    "como_se_va_a": "Signpost",
    "la_naturaleza": "Nature",
    "el_mar": "Sea",
    "la_catarata": "Waterfall",
    "la_comida": "Food",
    "el_pescado": "Fish as food",
    "el_aceite": "Olive oil",
    "la_naranja": "Orange (fruit)",
    "la_verdura": "Vegetable",
    "la_patata": "Potato",
    "el_agua": "Drinking water",
    "el_te": "Tea",
    "el_zumo": "Juice",
    "tener_hambre": "Hunger",
    "tener_sed": "Thirst",
    "pedir": "ordering food restaurant waiter",
    "tomar": "drinking coffee",
    "beber": "Drinking",
    "la_carta": "Menu",
    "el_primer_plato": "Soup",
    "el_segundo_plato": "Main course",
    "el_postre": "Dessert",
    "la_cuenta": "restaurant bill receipt",
    "que_desea": "waiter restaurant",
    "para_mi": "restaurant order",
    "quiero": "pointing finger shop",
    "la_cuenta_por_favor": "restaurant bill receipt",
    "hacer": "Construction",
    "ir": "walking",
    "venir": "come here gesture",
    "deber": "Duty",
    "saber": "Knowledge",
    "decir": "Speech",
    "dar": "giving gift",
    "poner": "putting books on shelf",
    "traer": "carrying box",
    "ver": "Visual perception",
    "mirar": "binoculars",
    "oir": "Hearing",
    "comprar": "Shopping",
    "pagar": "Payment",
    "necesitar": "Need",
    "encontrar": "found keys",
    "salir": "Exit sign",
    "pensar": "The Thinker",
    "creer": "Belief",
    "recordar": "Memory",
    "aprender": "Learning",
    "entender": "Understanding",
    "pared": "Wall",
    "suelo": "Floor",
    "llave_llaves": "Key (lock)",
    "ventilador": "Fan (machine)",
    "estanteria": "Bookcase",
    "cajon": "Drawer (furniture)",
    "armario": "Wardrobe",
    "el_armario": "Wardrobe",
    "sotano": "Basement",
    "pasillo": "Hallway",
    "teclado": "Computer keyboard",
    "pantalla": "Computer monitor",
    "cuadro": "Painting",
    "sabana": "Bed sheet",
    "cartera": "Wallet",
    "traje": "Suit",
    "cepillo": "Hairbrush",
    "peine": "Comb",
    "pelota": "Ball",
    "muneca": "Doll",
    "rompecabezas": "Jigsaw puzzle",
    "taller": "Auto mechanic workshop",
    "furgoneta": "Van",
    "lengua_idioma": "Language",
    "corazon": "Heart",
    "abogado": "Lawyer",
    "peluqueria": "Beauty salon",
    "panaderia": "Bakery",
    "panadero": "Baker",
    "perchero": "Coat rack",
    "campo": "Countryside",
    "festivo": "Public holiday",
    "ternera": "Veal",
    "ascensor": "Elevator",
    "duplex": "Duplex (building)",
    "planta_baja": "ground floor building entrance",
    "fregadero": "Sink",
    "alfombra": "Carpet",
    "vater": "Toilet",
    "chalet": "Single-family detached home",
    "chalet_adosado": "Terraced house",
    "piso_compartido": "Roommate",
    "antiguo": "Antique",
    "moderno": "Modern architecture",
    "alrededores": "Suburb",
    "salon_comedor": "living room dining room",
    "terraza": "Terrace (building)",
    "madera": "Wood",
    "enorme": "Giant sequoia",
    "afueras": "Suburb",
    "hierba": "Grass",
    "paisaje": "Landscape",
    "sillon": "Armchair",
    "carta": "Letter (message)",
    "no_se": "Shrug",
    "no_tengo_idea": "Shrug",
    "no_lo_se": "Shrug",
    "lo_sabia": "idea light bulb",
    "no_la_sabia": "surprised face",
    "que_significa": "Dictionary",
    "a_que_hora_acabas_a_que_hora_terminas": "Clock",
}

SKIP_TITLE_PATTERNS = re.compile(r"(logo|icon|symbol|diagram|map of|locator|coat of arms|\.svg)", re.I)


def default_query(english: str) -> str:
    text = str(english or "").strip()
    text = re.split(r"[/(]", text)[0].strip()
    text = re.sub(r"^to\s+", "", text, flags=re.I)
    text = text.rstrip(".?!…")
    return text or english


def iter_vocab_items(file_names=None):
    if file_names is None:
        file_names = ["spanish_vocabulary.md", "otherwords.md"]
    seen = set()
    for entry in load_entries(file_names):
        if entry.get("type") != "vocab":
            continue
        term = (entry.get("es") or "").strip()
        key = normalize_image_key(term)
        if not key or key in seen:
            continue
        seen.add(key)
        yield term, key, entry.get("en") or term


class Fetcher:
    def __init__(self, delay=1.0):
        self.delay = delay

    def _fetch(self, url):
        retries = 8
        for attempt in range(retries):
            time.sleep(self.delay)
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(request, timeout=60) as resp:
                    return resp.read()
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt == retries - 1:
                    raise
                retry_after = exc.headers.get("Retry-After", "")
                wait = int(retry_after) if retry_after.isdigit() else 10 * (attempt + 1)
                print(f"  (rate limited, waiting {wait}s)", flush=True)
                time.sleep(wait)

    def _get(self, url, params):
        return json.loads(self._fetch(f"{url}?{urllib.parse.urlencode(params)}"))

    def wikipedia_lead_image(self, title):
        data = self._get(WIKI_API, {
            "action": "query", "format": "json", "formatversion": 2,
            "titles": title, "redirects": 1,
            "prop": "pageimages|pageprops", "piprop": "thumbnail|name",
            "pithumbsize": THUMB_WIDTH,
        })
        pages = data.get("query", {}).get("pages", [])
        if not pages:
            return None
        page = pages[0]
        if page.get("missing") or "disambiguation" in page.get("pageprops", {}):
            return None
        thumb = page.get("thumbnail")
        name = page.get("pageimage", "")
        if not thumb or not name:
            return None
        if SKIP_TITLE_PATTERNS.search(name) and not title.lower().startswith("flag of"):
            return None
        return {
            "url": thumb["source"],
            "file": f"File:{name}",
            "page": f"https://en.wikipedia.org/wiki/{page['title'].replace(' ', '_')}",
        }

    def commons_search(self, query):
        """Search Commons; if nothing matches, retry with the query shortened word by word."""
        words = query.split()
        while words:
            found = self._commons_search_once(" ".join(words))
            if found:
                return found
            words = words[:-1]
        return None

    def _commons_search_once(self, query):
        data = self._get(COMMONS_API, {
            "action": "query", "format": "json", "formatversion": 2,
            "generator": "search", "gsrnamespace": 6, "gsrlimit": 20,
            "gsrsearch": f"{query} filetype:bitmap",
            "prop": "imageinfo", "iiprop": "url|mime",
            "iiurlwidth": THUMB_WIDTH,
        })
        pages = sorted(data.get("query", {}).get("pages", []), key=lambda p: p.get("index", 0))
        wanted = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 2]
        candidates = []
        for page in pages:
            if SKIP_TITLE_PATTERNS.search(page["title"]):
                continue
            info = (page.get("imageinfo") or [{}])[0]
            if info.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
                continue
            if not info.get("thumburl"):
                continue
            title = page["title"].lower()
            hits = sum(w in title for w in wanted)
            candidates.append((-hits, page.get("index", 0),
                               {"url": info["thumburl"], "file": page["title"], "page": info.get("descriptionurl")}))
        if not candidates:
            return None
        return min(candidates, key=lambda c: c[:2])[2]

    def file_license(self, file_title):
        data = self._get(COMMONS_API, {
            "action": "query", "format": "json", "formatversion": 2,
            "titles": file_title, "prop": "imageinfo", "iiprop": "extmetadata",
        })
        pages = data.get("query", {}).get("pages", [])
        meta = ((pages[0].get("imageinfo") or [{}])[0].get("extmetadata") or {}) if pages else {}
        strip = lambda v: re.sub(r"<[^>]+>", "", v or "").strip()
        return {
            "license": strip(meta.get("LicenseShortName", {}).get("value")),
            "author": strip(meta.get("Artist", {}).get("value")),
        }

    def download(self, url):
        return self._fetch(url)


def save_as_jpeg(content: bytes, target: Path):
    with Image.open(io.BytesIO(content)) as img:
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        else:
            img = img.convert("RGB")
        img.thumbnail((THUMB_WIDTH, THUMB_WIDTH))
        img.save(target, "JPEG", quality=85)


def main():
    parser = argparse.ArgumentParser(description="Download real pictures for Spanish vocab words.")
    parser.add_argument("--image-dir", default="images")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force", action="store_true", help="Re-download words that already have a .jpg")
    args = parser.parse_args()

    image_dir = Path(args.image_dir)
    image_dir.mkdir(parents=True, exist_ok=True)
    map_path = image_dir / "word_map.json"
    credits_path = image_dir / "CREDITS.json"
    word_map = {}
    new_credits = {}

    fetcher = Fetcher()
    items = list(iter_vocab_items())
    if args.limit is not None:
        items = items[: args.limit]

    failed = []
    for i, (term, key, english) in enumerate(items, 1):
        jpg = image_dir / f"{key}.jpg"
        png = image_dir / f"{key}.png"
        if jpg.exists() and not args.force:
            word_map[term] = jpg.name
            continue

        query = QUERY_OVERRIDES.get(key) or default_query(english)
        found = None
        try:
            # Capitalised overrides and plain translations are treated as Wikipedia article
            # titles; lowercase overrides are descriptive photo searches for Commons only.
            is_title = key not in QUERY_OVERRIDES or query[:1].isupper()
            found = (is_title and fetcher.wikipedia_lead_image(query)) or fetcher.commons_search(query)
            if found:
                save_as_jpeg(fetcher.download(found["url"]), jpg)
                new_credits[jpg.name] = {"term": term, "query": query, "source": found["page"],
                                     "file": found["file"], **fetcher.file_license(found["file"])}
        except Exception as exc:  # network or image errors: fall back to placeholder
            print(f"  ! {term}: {exc}", file=sys.stderr)
            found = None
            jpg.unlink(missing_ok=True)

        if found:
            png.unlink(missing_ok=True)
            word_map[term] = jpg.name
            print(f"[{i}/{len(items)}] {term} <- {query} ({found['file']})", flush=True)
        else:
            if not png.exists():
                create_card_image(term, png)
            word_map[term] = png.name
            failed.append(term)
            print(f"[{i}/{len(items)}] {term}: no image found for '{query}', using placeholder", flush=True)

    map_path.write_text(json.dumps(word_map, ensure_ascii=False, indent=2), encoding="utf-8")
    # Merge into the file on disk (it may have been edited while this run was going on).
    credits = json.loads(credits_path.read_text(encoding="utf-8")) if credits_path.exists() else {}
    credits.update(new_credits)
    credits_path.write_text(json.dumps(credits, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nDone: {len(items) - len(failed)} real images, {len(failed)} placeholders.")
    if failed:
        print("Placeholders:", ", ".join(failed))


if __name__ == "__main__":
    main()
