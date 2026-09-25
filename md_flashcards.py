#!/usr/bin/env python3
import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None


VOCAB_FILE_NAMES = {"spanish_vocabulary.md"}
VERB_FILE_NAMES = {"spanish_verb_conjugations.md"}
OTHER_WORDS_FILE_NAMES = {"otherwords.md"}
CHAPTER_PREFIXES = {"## Unidad ", "### "}


def normalize_text(value: str) -> str:
    value = value.replace("**", "").replace("_", "").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def normalize_chapter_name(value: str) -> str:
    cleaned = normalize_text(value)
    if " --- " in cleaned:
        cleaned = cleaned.split(" --- ", 1)[0]
    return cleaned


def get_chapter_name(raw_line: str, file_name: str):
    line = raw_line.strip()
    if line.startswith("## "):
        return normalize_chapter_name(line[3:])
    if line.startswith("### "):
        return normalize_chapter_name(line[4:])
    if file_name == "spanish_verb_conjugations.md":
        return "Verb tables"
    return "General"


def parse_vocab_rows(file_path: Path):
    entries = []
    current_chapter = "General"

    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("## "):
            current_chapter = normalize_chapter_name(stripped[3:])
            continue
        if stripped.startswith("### "):
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("-") or "---" in stripped:
            continue
        if stripped.startswith("Español") or stripped.startswith("English") or stripped.startswith("Polski"):
            continue

        cells = re.split(r"\s{2,}", stripped)
        cells = [normalize_text(cell) for cell in cells if cell.strip()]
        if len(cells) == 1 and entries and entries[-1]["type"] == "vocab":
            previous_es = entries[-1].get("es", "")
            if previous_es.rstrip().endswith("/") or previous_es.rstrip().endswith(" / la") or previous_es.rstrip().endswith(" / el"):
                entries[-1]["es"] = f"{previous_es} {cells[0]}".strip()
                continue

        if len(cells) < 2:
            continue

        if cells[0].lower() in {"español", "english", "polski"}:
            continue

        if len(cells) >= 3:
            es, en, pl = cells[0], cells[1], cells[2]
            entries.append({
                "type": "vocab",
                "chapter": current_chapter,
                "es": es,
                "en": en,
                "pl": pl,
            })
        else:
            es, en = cells[0], cells[1]
            entries.append({
                "type": "vocab",
                "chapter": current_chapter,
                "es": es,
                "en": en,
                "pl": "",
            })
    return entries


def parse_verb_rows(file_path: Path):
    entries = []
    current_verb = None
    current_chapter = "Verb tables"

    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        if stripped.startswith("## "):
            current_chapter = normalize_chapter_name(stripped[3:])
            continue

        if stripped.startswith("### "):
            current_verb = normalize_text(stripped[4:])
            continue

        if stripped.startswith("Person") or stripped.startswith("Español"):
            continue

        if "-----" in stripped or "---" in stripped:
            continue

        person_match = re.match(
            r"^(yo|tú|él / ella / usted|nosotros/as|vosotros/as|ellos / ellas / ustedes)\s{2,}\*\*(.+?)\*\*$",
            stripped,
        )
        if not person_match or current_verb is None:
            continue

        person = person_match.group(1)
        form = normalize_text(person_match.group(2))
        entries.append({
            "type": "verb",
            "chapter": current_chapter,
            "verb": current_verb,
            "person": person,
            "form": form,
        })

    return entries


def parse_other_words_rows(file_path: Path):
    entries = []
    current_chapter = "General"

    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        if stripped.endswith(":"):
            current_chapter = normalize_chapter_name(stripped[:-1])
            continue

        if stripped.startswith("Lista para estudiar"):
            continue

        if "—" not in stripped and " - " not in stripped:
            if stripped.startswith("Verbos para practicar"):
                current_chapter = normalize_chapter_name(stripped[:-1])
            continue

        # "es — en" or "es — en — pl"
        separator = "—" if "—" in stripped else " - "
        parts = [normalize_text(part) for part in stripped.split(separator, 2)]
        es, en = parts[0], parts[1]
        pl = parts[2] if len(parts) > 2 else ""
        if not es or not en:
            continue

        entries.append({
            "type": "vocab",
            "chapter": current_chapter,
            "es": es,
            "en": en,
            "pl": pl,
        })

    return entries


def load_entries(file_names):
    entries = []
    for name in file_names:
        file_path = Path(name)
        if not file_path.exists():
            continue

        if file_path.name in VERB_FILE_NAMES:
            entries.extend(parse_verb_rows(file_path))
        elif file_path.name in VOCAB_FILE_NAMES:
            entries.extend(parse_vocab_rows(file_path))
        elif file_path.name in OTHER_WORDS_FILE_NAMES:
            entries.extend(parse_other_words_rows(file_path))
    return entries


def filter_entries(entries, chapter=None, include_vocab=True, include_verbs=True):
    filtered = []
    for item in entries:
        if chapter is not None and item.get("chapter") != chapter:
            continue
        if item["type"] == "vocab" and include_vocab:
            filtered.append(item)
        elif item["type"] == "verb" and include_verbs:
            filtered.append(item)
    return filtered


def list_chapters(entries):
    chapters = []
    seen = set()
    for item in entries:
        chapter = item.get("chapter")
        if chapter and chapter not in seen:
            chapters.append(chapter)
            seen.add(chapter)
    return chapters


def find_image_for_term(term: str, image_dir=None):
    if image_dir is None:
        image_dir = Path(__file__).resolve().parent / "images"
    if not isinstance(image_dir, Path):
        image_dir = Path(image_dir)

    cleaned = normalize_text(term).lower()
    cleaned = unicodedata.normalize("NFKD", cleaned)
    cleaned = "".join(ch for ch in cleaned if not unicodedata.combining(ch))
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")

    candidates = []
    if cleaned:
        candidates.extend([
            image_dir / f"{cleaned}.png",
            image_dir / f"{cleaned}.jpg",
            image_dir / f"{cleaned}.jpeg",
            image_dir / f"{cleaned}.gif",
            image_dir / f"{cleaned}.webp",
        ])

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def open_image_file(path):
    if not path:
        return False
    file_path = Path(path)
    if not file_path.exists():
        return False

    # Avoid launching desktop viewers in CLI study sessions on Linux because that can
    # crash the whole program before the answer prompt is shown.
    if sys.platform.startswith("linux"):
        return False

    try:
        if sys.platform.startswith("darwin"):
            completed = subprocess.run(["open", str(file_path)], check=False)
        elif sys.platform.startswith("win"):
            completed = subprocess.run(["cmd", "/c", "start", "", str(file_path)], check=False)
        else:
            completed = subprocess.run(["xdg-open", str(file_path)], check=False)
    except OSError:
        return False

    return completed.returncode == 0


EMOJI_VISUALS = {
    "hola": "👋",
    "hello": "👋",
    "gracias": "🙏",
    "thank": "🙏",
    "adios": "👋",
    "goodbye": "👋",
    "por favor": "🙏",
    "please": "🙏",
    "perro": "🐶",
    "dog": "🐶",
    "gato": "🐱",
    "cat": "🐱",
    "casa": "🏠",
    "house": "🏠",
    "sol": "☀️",
    "sun": "☀️",
    "agua": "💧",
    "water": "💧",
    "mar": "🌊",
    "sea": "🌊",
    "manzana": "🍎",
    "apple": "🍎",
    "libro": "📖",
    "book": "📖",
    "mesa": "🪑",
    "table": "🪑",
    "silla": "🪑",
    "chair": "🪑",
    "arbol": "🌳",
    "tree": "🌳",
    "flor": "🌼",
    "flower": "🌼",
    "carro": "🚗",
    "car": "🚗",
    "auto": "🚗",
    "bus": "🚌",
    "telefono": "📱",
    "phone": "📱",
    "llamada": "📞",
    "call": "📞",
    "llamarse": "🗣️",
    "comida": "🍞",
    "food": "🍞",
    "pan": "🥖",
    "bread": "🥖",
    "amigo": "👫",
    "friend": "👫",
    "familia": "👨‍👩‍👧‍👦",
    "family": "👨‍👩‍👧‍👦",
    "escuela": "🏫",
    "school": "🏫",
    "clase": "📚",
    "class": "📚",
    "ciudad": "🏙️",
    "city": "🏙️",
    "calle": "🛣️",
    "street": "🛣️",
    "tren": "🚆",
    "train": "🚆",
    "metro": "🚇",
    "subway": "🚇",
    "avion": "✈️",
    "plane": "✈️",
    "vuelo": "✈️",
    "flight": "✈️",
    "playa": "🏖️",
    "beach": "🏖️",
    "lluvia": "🌧️",
    "rain": "🌧️",
    "nube": "☁️",
    "cloud": "☁️",
    "nombre": "📝",
    "name": "📝",
    "edad": "🎂",
    "age": "🎂",
    "pais": "🌍",
    "country": "🌍",
    "direccion": "📍",
    "address": "📍",
    "trabajar": "💼",
    "work": "💼",
    "estudiar": "📘",
    "study": "📘",
    "hablar": "💬",
    "speak": "💬",
    "vivir": "🏡",
    "live": "🏡",
    "leer": "📚",
    "read": "📚",
    "escribir": "✍️",
    "write": "✍️",
    "escuchar": "🎧",
    "listen": "🎧",
    "preguntar": "❓",
    "ask": "❓",
    "responder": "💡",
    "answer": "💡",
    "abrir": "🚪",
    "open": "🚪",
    "cerrar": "🔒",
    "close": "🔒",
    "blanco": "⚪",
    "white": "⚪",
    "rojo": "🔴",
    "red": "🔴",
    "azul": "🔵",
    "blue": "🔵",
    "verde": "🟢",
    "green": "🟢",
    "amarillo": "🟡",
    "yellow": "🟡",
    "negro": "⚫",
    "black": "⚫",
    "ventana": "🪟",
    "window": "🪟",
    "puerta": "🚪",
    "door": "🚪",
    "mapa": "🗺️",
    "map": "🗺️",
    "lapiz": "✏️",
    "pencil": "✏️",
    "boligrafo": "🖊️",
    "pen": "🖊️",
    "diccionario": "📘",
    "dictionary": "📘",
    "profesor": "👩‍🏫",
    "teacher": "👩‍🏫",
    "estudiante": "🎓",
    "student": "🎓",
    "doctor": "🩺",
    "nurse": "👩‍⚕️",
    "policia": "🚓",
    "police": "🚓",
    "buenos dias": "🌅",
    "buenas tardes": "🌇",
    "buenas noches": "🌙",
    "hasta luego": "👋",
    "hasta manana": "📅",
    "nos vemos": "👋",
    "muchas gracias": "🙏🙏",
    "de nada": "😊",
    "perdon": "🙇",
    "lo siento": "😔",
    "como estas": "🙂",
    "bien": "👍",
    "muy bien": "👍👍",
    "mal": "👎",
    "mas o menos": "🤷",
    "correo electronico": "📧",
    "nacionalidad": "🛂",
    "no se": "🤷",
    "no tengo idea": "🤷",
    "no lo se": "🤷",
    "lo sabia": "💡",
    "que significa": "❓",
    "espana": "🇪🇸",
    "polonia": "🇵🇱",
    "alemania": "🇩🇪",
    "francia": "🇫🇷",
    "italia": "🇮🇹",
    "portugal": "🇵🇹",
    "inglaterra": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "estados unidos": "🇺🇸",
    "mexico": "🇲🇽",
    "argentina": "🇦🇷",
    "colombia": "🇨🇴",
    "espanol espanola": "🇪🇸",
    "polaco polaca": "🇵🇱",
    "aleman alemana": "🇩🇪",
    "frances francesa": "🇫🇷",
    "italiano italiana": "🇮🇹",
    "portugues portuguesa": "🇵🇹",
    "ingles inglesa": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "estadounidense": "🇺🇸",
    "mexicano mexicana": "🇲🇽",
    "argentino argentina": "🇦🇷",
    "el profesor la": "🧑‍🏫",
    "profesora": "👩‍🏫",
    "el estudiante la": "🧑‍🎓",
    "alumno": "🧑‍🎓",
    "alumnos": "🧑‍🎓",
    "el medico la medica": "🧑‍⚕️",
    "el enfermero la": "🧑‍⚕️",
    "enfermera": "👩‍⚕️",
    "el abogado la abogada lawyer": "⚖️",
    "abogado": "⚖️",
    "el cocinero la cocinera": "🧑‍🍳",
    "el periodista la": "📰",
    "periodista": "📰",
    "el ingeniero la ingeniera": "🧑‍🔧",
    "el arquitecto la arquitecta": "📐",
    "el policia la policia police officer": "👮",
    "cuaderno": "📓",
    "tijeras": "✂️",
    "mochila": "🎒",
    "cartel": "🪧",
    "proyector": "📽️",
    "planta": "🪴",
    "repetir": "🔁",
    "naranja": "🟠",
    "rosa": "🩷",
    "gris": "🩶",
    "marron": "🟤",
    "morado": "🟣",
    "piso": "🏢",
    "dormitorio": "🛏️",
    "cama": "🛏️",
    "salon": "🛋️",
    "sofa": "🛋️",
    "sillon": "🛋️",
    "cocina": "🍳",
    "bano": "🛁",
    "ducha": "🚿",
    "comedor": "🍽️",
    "jardin": "🌷",
    "lampara": "💡",
    "television": "📺",
    "espejo": "🪞",
    "teclado": "⌨️",
    "pantalla": "🖥️",
    "cuadro": "🖼️",
    "llave llaves": "🔑",
    "ascensor": "🛗",
    "vater": "🚽",
    "chalet": "🏡",
    "fregadero": "🚰",
    "madera": "🪵",
    "cajon": "🗄️",
    "joven": "🧒",
    "mayor": "👴",
    "fuerte": "💪",
    "pelo": "💇",
    "rubio": "👱",
    "pelirrojo": "🧑‍🦰",
    "rizado": "🧑‍🦱",
    "ojos": "👀",
    "gafas": "👓",
    "barba": "🧔",
    "simpatico": "😊",
    "antipatico": "😠",
    "divertido": "😂",
    "serio": "😐",
    "tranquilo": "😌",
    "nervioso": "😬",
    "timido": "😳",
    "inteligente": "🧠",
    "alegre": "😄",
    "generoso": "🎁",
    "trabajador": "👷",
    "ropa": "👕",
    "camiseta": "👕",
    "camisa": "👔",
    "chaqueta": "🧥",
    "abrigo": "🧥",
    "pantalones": "👖",
    "vaqueros": "👖",
    "vestido": "👗",
    "zapatos": "👞",
    "botas": "👢",
    "zapatillas": "👟",
    "sombrero": "🎩",
    "gorra": "🧢",
    "bufanda": "🧣",
    "traje": "🤵",
    "cartera": "👛",
    "padres": "👪",
    "padre": "👨",
    "madre": "👩",
    "hijo": "👦",
    "hija": "👧",
    "marido": "🤵",
    "mujer": "👰",
    "abuelo": "👴",
    "abuela": "👵",
    "casado": "💍",
    "divorciado": "💔",
    "despertarse": "⏰",
    "ducharse": "🚿",
    "vestirse": "👕",
    "desayunar": "🥣",
    "ir al trabajo": "💼",
    "comer": "🍽️",
    "cenar": "🍽️",
    "acostarse": "🛌",
    "dormir": "😴",
    "hora": "🕐",
    "que hora es": "🕐",
    "es la una": "🕐",
    "son las dos": "🕑",
    "por la manana": "🌅",
    "por la tarde": "🌇",
    "por la noche": "🌙",
    "gustar": "👍",
    "encantar": "😍",
    "jugar": "🎮",
    "hacer deporte": "🏅",
    "correr": "🏃",
    "nadar": "🏊",
    "bailar": "💃",
    "cantar": "🎤",
    "viajar": "🧳",
    "cocinar": "🍳",
    "dibujar": "🎨",
    "pasear": "🚶",
    "montar en bicicleta": "🚴",
    "escuchar musica": "🎧",
    "ver la television": "📺",
    "ver una pelicula": "🎬",
    "leer un libro": "📖",
    "quedar con amigos": "👫",
    "ir al cine": "🍿",
    "ir de compras": "🛍️",
    "futbol": "⚽",
    "tenis": "🎾",
    "baloncesto": "🏀",
    "gimnasio": "🏋️",
    "cine": "🎬",
    "teatro": "🎭",
    "musica": "🎵",
    "juguete": "🧸",
    "pelota": "⚽",
    "muneca": "🪆",
    "rompecabezas": "🧩",
    "festivo": "🎉",
    "banco": "🏦",
    "farmacia": "💊",
    "supermercado": "🛒",
    "tienda": "🏪",
    "restaurante": "🍽️",
    "bar": "🍺",
    "hotel": "🏨",
    "hospital": "🏥",
    "estacion": "🚉",
    "aeropuerto": "🛫",
    "museo": "🏛️",
    "iglesia": "⛪",
    "parque": "🏞️",
    "oficina de correos": "🏤",
    "a la derecha": "➡️",
    "a la izquierda": "⬅️",
    "a la derecha de": "➡️",
    "a la izquierda de": "⬅️",
    "todo recto": "⬆️",
    "girar": "↪️",
    "cruzar": "🚸",
    "buscar": "🔍",
    "llegar": "🛬",
    "furgoneta": "🚐",
    "peluqueria": "💇",
    "panaderia": "🥖",
    "panadero": "🧑‍🍳",
    "naturaleza": "🌿",
    "rio": "🏞️",
    "montana": "⛰️",
    "bosque": "🌲",
    "isla": "🏝️",
    "desierto": "🏜️",
    "volcan": "🌋",
    "hierba": "🌱",
    "paisaje": "🏞️",
    "campo": "🌾",
    "arroz": "🍚",
    "pasta": "🍝",
    "carne": "🥩",
    "pollo": "🍗",
    "pescado": "🐟",
    "huevo": "🥚",
    "queso": "🧀",
    "leche": "🥛",
    "mantequilla": "🧈",
    "aceite": "🫒",
    "fruta": "🍇",
    "platano": "🍌",
    "la naranja": "🍊",
    "fresa": "🍓",
    "verdura": "🥦",
    "tomate": "🍅",
    "patata": "🥔",
    "cebolla": "🧅",
    "zanahoria": "🥕",
    "cafe": "☕",
    "te": "🍵",
    "zumo": "🧃",
    "desayuno": "🥐",
    "cena": "🍽️",
    "tener hambre": "😋",
    "tener sed": "🥤",
    "beber": "🥤",
    "postre": "🍰",
    "cuenta": "🧾",
    "la cuenta por favor": "🧾",
    "la carta": "📋",
    "carta": "✉️",
    "ternera": "🐄",
    "ver": "👀",
    "mirar": "👀",
    "oir": "👂",
    "comprar": "🛒",
    "pagar": "💳",
    "pensar": "🤔",
    "dar": "🎁",
    "decir": "🗣️",
    "saber": "🧠",
    "aprender": "📚",
    "entender": "💡",
    "ir": "🚶",
    "jabon": "🧼",
    "corazon": "❤️",
    "lengua idioma": "🗣️",
    "viaje": "🧳",
    "vacaciones": "🏖️",
    "billete": "🎫",
    "pasaporte": "🛂",
    "maleta": "🧳",
    "equipaje": "🧳",
    "autobus": "🚌",
    "coche": "🚗",
    "bicicleta": "🚲",
    "moto": "🏍️",
    "barco": "🚢",
    "taxi": "🚕",
    "anden": "🚉",
    "parada de autobus": "🚏",
    "turista": "📸",
    "reserva": "📅",
    "de ida y vuelta": "🔁",
    "reservar": "📅",
    "alojarse": "🏨",
    "hacer la maleta": "🧳",
    "esperar": "⏳",
    "vuelo": "✈️",
    "camping": "🏕️",
    "subir": "⬆️",
    "bajar": "⬇️",
    "tiempo": "🌦️",
    "que tiempo hace": "🌦️",
    "hace sol": "☀️",
    "hace calor": "🥵",
    "hace frio": "🥶",
    "hace viento": "💨",
    "hace buen tiempo": "🌤️",
    "hace mal tiempo": "⛈️",
    "llueve": "🌧️",
    "nieva": "🌨️",
    "esta nublado": "☁️",
    "nieve": "❄️",
    "viento": "💨",
    "tormenta": "⛈️",
    "temperatura": "🌡️",
    "primavera": "🌸",
    "verano": "☀️",
    "otono": "🍂",
    "invierno": "⛄",
    "cuerpo": "🧍",
    "cabeza": "🗣️",
    "cara": "🙂",
    "boca": "👄",
    "nariz": "👃",
    "oreja": "👂",
    "diente": "🦷",
    "brazo": "💪",
    "mano": "✋",
    "dedo": "☝️",
    "pierna": "🦵",
    "pie": "🦶",
    "estomago": "🫃",
    "salud": "🩺",
    "estar enfermo": "🤒",
    "estar cansado": "😩",
    "dolor": "🤕",
    "doler": "🤕",
    "me duele la cabeza": "🤕",
    "que te pasa": "😟",
    "resfriado": "🤧",
    "gripe": "🤧",
    "tos": "😷",
    "fiebre": "🌡️",
    "medicamento": "💊",
    "pastilla": "💊",
    "receta": "📝",
    "cita": "📅",
    "el la dentista": "🦷",
    "centro de salud": "🏥",
    "sano": "💪",
    "descansar": "🛌",
    "que te mejores": "💐",
    "garganta": "🗣️",
    "amigo": "👫",
    "si": "✅",
    "no": "❌",
    "bombero": "🧑‍🚒",
    "dinero": "💰",
    "periodico": "📰",
    "cientifico": "🧑‍🔬",
    "mecanico": "🧑‍🔧",
    "cartero": "📮",
    "piloto": "🧑‍✈️",
    "peluquero": "💇",
    "azafata": "🛫",
    "tener frio": "🥶",
    "tener calor": "🥵",
    "tener sueno": "😴",
    "tener fiebre": "🤒",
    "tener miedo": "😨",
    "tener mascota": "🐕",
    "refresco": "🥤",
    "nuevo": "🆕",
    "chino": "🇨🇳",
    "brasileno": "🇧🇷",
    "suizo": "🇨🇭",
    "canadiense": "🇨🇦",
    "belga": "🇧🇪",
    "ruso": "🇷🇺",
    "sudafricano": "🇿🇦",
    "escritor": "✍️",
    "laboratorio": "🧪",
    "oficina": "🏢",
    "correos": "🏤",
    "tribunal": "⚖️",
    "el la cantante": "🎤",
    "el la deportista": "🏅",
    "lavarse": "🧼",
    "maquillarse": "💄",
    "peinarse": "💇",
    "relajarse": "😌",
    "amar": "❤️",
    "bienvenido": "🤗",
    "encantado": "🤝",
    "mucho gusto": "🤝",
    "regular": "🤷",
    "famoso": "⭐",
    "hermanos": "👫",
    "abono de metro": "🚇",
    "ama de casa": "🏠",
    "donde": "📍",
    "de donde": "🌍",
    "no entiendo no comprendo": "😕",
    "puedes repetir": "🔁",
    "me llamo": "📝",
    "de donde eres": "🌍",
    "soy de": "🌍",
    "donde vives": "🏡",
    "vivo en": "🏡",
    "cuantos anos tienes": "🎂",
    "tengo anos": "🎂",
    "que idiomas hablas": "🗣️",
    "hablo": "🗣️",
    "mercado": "🧺",
    "pared": "🧱",
    "salir de casa": "🚪",
    "salir": "🚪",
    "empezar": "▶️",
    "terminar": "🏁",
    "volver": "🔙",
    "el primer plato": "🥣",
    "el segundo plato": "🍖",
    "donde esta": "📍",
    "a que hora acabas a que hora terminas": "🕐",
}


def normalize_visual_term(term):
    text = normalize_text(str(term or "")).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_emoji_visual_for_term(term):
    text = normalize_visual_term(term)
    if not text:
        return None
    if text in EMOJI_VISUALS:
        return EMOJI_VISUALS[text]
    without_article = re.sub(r"^(el|la|los|las) ", "", text)
    if without_article in EMOJI_VISUALS:
        return EMOJI_VISUALS[without_article]
    if text in {"como te llamas", "que tal"}:
        return EMOJI_VISUALS.get("llamarse")
    return None


def has_emoji_visual(word):
    return get_emoji_visual_for_term(word) is not None


def generate_ascii_word_art(word, width=20):
    text = str(word).strip()
    if not text:
        return "(no word)"

    normalized = normalize_visual_term(text)
    for key, emoji in EMOJI_VISUALS.items():
        if key == normalized:
            return emoji
    visual = get_emoji_visual_for_term(text)
    if visual:
        return visual

    normalized_upper = text.upper()
    letters = {
        "A": ["  ███  ", " ████  ", "██   ██", "███████", "██   ██"],
        "B": ["██████ ", "██   ██", "██████ ", "██   ██", "██████ "],
        "C": [" █████ ", "██   ██", "██     ", "██   ██", " █████ "],
        "D": ["██████ ", "██   ██", "██   ██", "██   ██", "██████ "],
        "E": ["███████", "██     ", "█████  ", "██     ", "███████"],
        "F": ["███████", "██     ", "█████  ", "██     ", "██     "],
        "G": [" █████ ", "██   ██", "██     ", "██  ██ ", " █████ "],
        "H": ["██   ██", "██   ██", "███████", "██   ██", "██   ██"],
        "I": ["███████", "  ██  ", "  ██  ", "  ██  ", "███████"],
        "J": ["███████", "   ██ ", "   ██ ", "██ ██ ", " ███  "],
        "K": ["██   ██", "██  ██ ", "████   ", "██  ██ ", "██   ██"],
        "L": ["██     ", "██     ", "██     ", "██     ", "███████"],
        "M": ["██   ██", "████████", "██ █ ██", "██   ██", "██   ██"],
        "N": ["██   ██", "████  ██", "██ ██ ██", "██   ███", "██    ██"],
        "O": [" █████ ", "██   ██", "██   ██", "██   ██", " █████ "],
        "P": ["██████ ", "██   ██", "██████ ", "██     ", "██     "],
        "Q": [" █████ ", "██   ██", "██   ██", "██ ██ ", " ██████"],
        "R": ["██████ ", "██   ██", "██████ ", "██  ██ ", "██   ██"],
        "S": [" █████ ", "██   ██", " ███   ", "    ██ ", "██████ "],
        "T": ["███████", "  ██  ", "  ██  ", "  ██  ", "  ██  "],
        "U": ["██   ██", "██   ██", "██   ██", "██   ██", " █████ "],
        "V": ["██   ██", "██   ██", "██   ██", " ████ ", "  ██  "],
        "W": ["██   ██", "██   ██", "██ █ ██", "███████", "██   ██"],
        "X": ["██   ██", " ████ ", "  ██  ", " ████ ", "██   ██"],
        "Y": ["██   ██", " ████ ", "  ██  ", "  ██  ", "  ██  "],
        "Z": ["███████", "    ██ ", "   ██  ", "  ██   ", "███████"],
        " ": ["       ", "       ", "       ", "       ", "       "],
    }

    rows = ["" for _ in range(5)]
    for ch in normalized_upper:
        template = letters.get(ch, letters[" "])
        for i in range(5):
            rows[i] += template[i] + " "

    for i, row in enumerate(rows):
        rows[i] = row.rstrip()

    art = "\n".join(rows)
    banner = f"{normalized_upper}"
    if banner:
        border = "*" * max(len(banner) + 4, len(art.splitlines()[0]) if art.splitlines() else 0)
        return border + "\n* " + banner + " *\n" + art + "\n" + border
    return "[ASCII image unavailable]"


def display_image_in_terminal(path, max_width=40):
    if Image is None:
        print("(Image preview unavailable in this terminal.)")
        return

    image_path = Path(path)
    if not image_path.exists():
        print("(Image file not found.)")
        return

    try:
        with Image.open(image_path) as img:
            img = img.convert("L")
            width = min(img.width, max_width)
            height = max(1, int((img.height / img.width) * width * 0.5))
            img = img.resize((width, height))
            pixels = img.load()

            chars = "@%#*+=-:. "
            print()
            for y in range(img.height):
                line = []
                for x in range(img.width):
                    value = pixels[x, y]
                    index = int(value / 256 * len(chars))
                    index = min(len(chars) - 1, max(0, index))
                    line.append(chars[index])
                print("".join(line))
    except Exception:
        print("(Image preview unavailable in this terminal.)")


def display_color_image_in_terminal(path, max_width=60):
    """Draw a picture with 24-bit colour half-block characters (two pixels per cell)."""
    if Image is None:
        print("(Image preview unavailable in this terminal.)")
        return

    image_path = Path(path)
    if not image_path.exists():
        print("(Image file not found.)")
        return

    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            width = min(img.width, max_width)
            height = max(2, int((img.height / img.width) * width))
            height += height % 2
            img = img.resize((width, height))
            pixels = img.load()

            print()
            for y in range(0, height, 2):
                line = []
                for x in range(width):
                    top = pixels[x, y]
                    bottom = pixels[x, y + 1]
                    line.append(
                        f"\x1b[38;2;{top[0]};{top[1]};{top[2]}m"
                        f"\x1b[48;2;{bottom[0]};{bottom[1]};{bottom[2]}m▀"
                    )
                print("".join(line) + "\x1b[0m")
    except Exception:
        print("(Image preview unavailable in this terminal.)")


DISPLAY_MODES = ("text", "ascii", "emoji", "picture", "window")

VIEWER_DIR = Path(__file__).resolve().parent / "viewer"

VIEWER_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Flashcard picture</title>
<style>
  html, body { margin: 0; height: 100%; background: #111; color: #ccc; font: 20px sans-serif; }
  body { display: flex; align-items: center; justify-content: center; }
  img { max-width: 100vw; max-height: 100vh; object-fit: contain; }
</style>
</head>
<body>
<img id="card" alt="">
<p id="message">Waiting for the first card...</p>
<script>
  let current = null;
  function showCard(src) {
    if (src === current) return;
    current = src;
    const img = document.getElementById("card");
    const message = document.getElementById("message");
    if (src) {
      img.src = src;
      img.style.display = "";
      message.style.display = "none";
    } else {
      img.style.display = "none";
      message.textContent = "Quiz finished - you can close this tab.";
      message.style.display = "";
    }
  }
  function poll() {
    const script = document.createElement("script");
    script.src = "card.js?t=" + Date.now();
    script.onload = script.onerror = () => script.remove();
    document.body.appendChild(script);
  }
  setInterval(poll, 400);
  poll();
</script>
</body>
</html>
"""

_viewer_opened = False


def gui_environment():
    """Environment for launching desktop apps without VS Code snap leftovers.

    VS Code installed as a snap exports its own GTK/GIO/XDG paths; GTK viewers such
    as eog crash with symbol lookup errors when they inherit them.
    """
    env = dict(os.environ)
    for key in list(env):
        if key.endswith("_VSCODE_SNAP_ORIG"):
            base = key[: -len("_VSCODE_SNAP_ORIG")]
            original = env.pop(key)
            if original:
                env[base] = original
            else:
                env.pop(base, None)
    for key in list(env):
        if key.startswith(("SNAP", "GTK_", "GIO_", "GDK_PIXBUF")) or key in {"LOCPATH", "GSETTINGS_SCHEMA_DIR"}:
            env.pop(key)
        elif key.startswith("XDG_") and "/snap/" in env[key]:
            env.pop(key)
    return env


def write_viewer_card(path):
    VIEWER_DIR.mkdir(exist_ok=True)
    src = Path(path).resolve().as_uri() if path else None
    (VIEWER_DIR / "card.js").write_text(f"showCard({json.dumps(src)});\n", encoding="utf-8")


def launch_in_desktop(file_path):
    if sys.platform.startswith("win"):
        try:
            os.startfile(str(file_path))  # type: ignore[attr-defined]
        except OSError:
            return False
        return True

    command = ["open" if sys.platform.startswith("darwin") else "xdg-open", str(file_path)]
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=gui_environment(),
        )
    except OSError:
        return False
    time.sleep(0.5)
    return process.poll() in (None, 0)


def open_image_window(path):
    """Show a picture in one browser page that updates itself for every card.

    The page is opened only once per quiz, so the terminal keeps keyboard focus
    for all cards after the first one.
    """
    global _viewer_opened
    if not Path(path).exists():
        return False
    write_viewer_card(path)
    if _viewer_opened:
        return True

    page = VIEWER_DIR / "index.html"
    page.write_text(VIEWER_HTML, encoding="utf-8")
    if not launch_in_desktop(page):
        return False
    _viewer_opened = True
    print("(Pictures open in your browser. Click back into the terminal once; the page updates by itself for the next cards.)")
    return True


def close_image_window():
    global _viewer_opened
    if _viewer_opened:
        write_viewer_card(None)
    _viewer_opened = False


def has_visual_for_display(item, display, image_dir=None):
    word = item.get("es", "")
    if display == "emoji":
        return has_emoji_visual(word)
    if display in {"ascii", "picture", "window"}:
        return find_image_for_term(word, image_dir) is not None
    return True


def show_visual(word, display, image_dir=None):
    if display == "emoji":
        print(f"\n{get_emoji_visual_for_term(word)}")
        return
    image_path = find_image_for_term(word, image_dir)
    if image_path is None:
        print("(No matching image found in the images folder.)")
    elif display == "ascii":
        display_image_in_terminal(image_path)
    elif display == "window":
        if not open_image_window(image_path):
            print("(Could not open an image window; showing the picture in the terminal instead.)")
            display_color_image_in_terminal(image_path)
    else:
        display_color_image_in_terminal(image_path)


SPANISH_PUNCTUATION = "¿?¡!.,;:…"


def strip_accents(text):
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def answers_match(answer, expected, ignore_punctuation=False, ignore_accents=False):
    answer = answer.strip().lower()
    expected = expected.strip().lower()
    if ignore_accents:
        answer = strip_accents(answer)
        expected = strip_accents(expected)
    if ignore_punctuation:
        table = str.maketrans("", "", SPANISH_PUNCTUATION)
        answer = " ".join(answer.translate(table).split())
        expected = " ".join(expected.translate(table).split())
    return answer == expected


def prompt_for_vocab(item, display="text", image_dir=None, ignore_punctuation=False, ignore_accents=False):
    if display != "text":
        word = item.get("es", "")
        english = item.get("en", "")
        if english:
            print(f"\nEnglish: {english}")
        show_visual(word, display, image_dir)

        answer = input("Type the Spanish word shown in the image: ").strip().lower()
        if answers_match(answer, word, ignore_punctuation, ignore_accents):
            print("✅ Correct! Great job!")
            return True
        english_hint = f" (English: {english})" if english else ""
        print(f"❌ Incorrect. The correct answer was: {word}{english_hint}")
        return False

    if item.get("en"):
        label = "English"
        expected = item["en"]
    elif item.get("pl"):
        label = "Polski"
        expected = item["pl"]
    else:
        return False

    print(f"\nCard: {item['es']}")
    answer = input(f"{item['es']} -> {label}: ").strip().lower()
    if answers_match(answer, expected, ignore_punctuation, ignore_accents):
        print("✅ Correct! Great job!")
        return True

    print(f"❌ Incorrect. The correct answer was: {expected}")
    return False


def prompt_for_verb(item, ignore_punctuation=False, ignore_accents=False):
    print(f"\nCard: {item['verb']} ({item['person']})")
    answer = input(f"{item['verb']} ({item['person']}) -> ").strip().lower()
    if answers_match(answer, item["form"], ignore_punctuation, ignore_accents):
        print("✅ Correct! Great job!")
        return True
    print(f"❌ Incorrect. The correct answer was: {item['form']}")
    return False


def run_learn(entries, chapter=None, include_vocab=True, include_verbs=True):
    filtered = filter_entries(entries, chapter=chapter, include_vocab=include_vocab, include_verbs=include_verbs)
    if not filtered:
        raise SystemExit("No entries available for this chapter and mode.")

    for item in filtered:
        print(f"\n{item['chapter']}")
        if item["type"] == "vocab":
            print(f"Spanish: {item['es']}")
            print(f"English: {item['en']}")
            print(f"Polski: {item['pl']}")
        else:
            print(f"Verb: {item['verb']}")
            print(f"Person: {item['person']}")
            print(f"Form: {item['form']}")
        input("Press Enter to continue... ")


def run_quiz(entries, chapter=None, limit=None, include_vocab=True, include_verbs=True, display="text", image_dir=None, ignore_punctuation=False, ignore_accents=False):
    filtered = filter_entries(entries, chapter=chapter, include_vocab=include_vocab, include_verbs=include_verbs)
    if display != "text":
        filtered = [
            item for item in filtered
            if item.get("type") == "vocab" and has_visual_for_display(item, display, image_dir)
        ]

    if not filtered:
        raise SystemExit("No matching entries for the selected chapter and mode.")

    if limit is not None:
        filtered = filtered[:limit]

    random.shuffle(filtered)
    score = 0
    total = 0

    try:
        for item in filtered:
            total += 1
            if item["type"] == "vocab":
                score += int(prompt_for_vocab(item, display=display, image_dir=image_dir, ignore_punctuation=ignore_punctuation, ignore_accents=ignore_accents))
            else:
                score += int(prompt_for_verb(item, ignore_punctuation=ignore_punctuation, ignore_accents=ignore_accents))
    finally:
        close_image_window()

    print(f"\nFinal score: {score}/{total} ({(score / total * 100) if total else 0:.0f}%)")


def run_memorize(entries, chapter=None, limit=None, display="picture", image_dir=None, delay=4.0, rounds=None):
    """Loop through vocab cards as a slideshow: picture plus Spanish and English, no typing."""
    filtered = filter_entries(entries, chapter=chapter, include_vocab=True, include_verbs=False)
    if display != "text":
        filtered = [item for item in filtered if has_visual_for_display(item, display, image_dir)]
    if not filtered:
        raise SystemExit("No matching vocab entries for the selected chapter and display.")
    if limit is not None:
        filtered = filtered[:limit]

    shown = 0
    round_number = 0
    try:
        while rounds is None or round_number < rounds:
            round_number += 1
            cards = list(filtered)
            random.shuffle(cards)
            for position, item in enumerate(cards, 1):
                if display in {"ascii", "picture"}:
                    print("\x1b[2J\x1b[H", end="")
                print(f"\nRound {round_number} - card {position}/{len(cards)}  (Ctrl+C to stop)")
                if display != "text":
                    show_visual(item.get("es", ""), display, image_dir)
                print(f"\n  {item.get('es', '')}")
                if item.get("en"):
                    print(f"  English: {item['en']}")
                if item.get("pl"):
                    print(f"  Polski: {item['pl']}")
                shown += 1
                time.sleep(delay)
    except KeyboardInterrupt:
        pass
    finally:
        close_image_window()

    print(f"\nShown {shown} cards.")
    return shown


def main():
    parser = argparse.ArgumentParser(description="Quiz yourself on Spanish vocab and verb conjugations from markdown study files.")
    parser.add_argument("files", nargs="*", default=["spanish_vocabulary.md", "spanish_verb_conjugations.md", "otherwords.md"], help="Markdown files to study from.")
    parser.add_argument("--chapter", help="Study only one chapter: for example 'Unidad 1' or 'Verb tables'.")
    parser.add_argument("--limit", type=int, help="Number of cards to quiz on.")
    parser.add_argument("--mode", choices=["all", "vocab", "verbs"], default="all", help="Which study set to use.")
    parser.add_argument("--learn", action="store_true", help="Show answers directly instead of testing yourself.")
    parser.add_argument(
        "--display",
        choices=DISPLAY_MODES,
        default=None,
        help=(
            "How vocab cards are shown (default: text, or picture with --memorize): 'text' = Spanish word, type English; "
            "'emoji' = emoji, type Spanish; 'ascii' = photo as ASCII art, type Spanish; "
            "'picture' = colour photo in the terminal, type Spanish; "
            "'window' = photo in a browser page that updates for each card, type Spanish."
        ),
    )
    parser.add_argument("--image-mode", action="store_true", help="Same as --display picture.")
    parser.add_argument(
        "--memorize",
        action="store_true",
        help="Slideshow to memorize words: loops through pictures with the Spanish word and English meaning until Ctrl+C.",
    )
    parser.add_argument("--delay", type=float, default=4.0, help="Seconds per card in --memorize mode (default 4).")
    parser.add_argument(
        "--ignore-punctuation",
        action="store_true",
        help="Accept answers typed without punctuation such as ¿ ? ¡ ! . , (accents still count).",
    )
    parser.add_argument(
        "--ignore-accents",
        action="store_true",
        help="Accept answers typed without accents and ñ, e.g. 'adios' for 'adiós', 'manana' for 'mañana'.",
    )
    parser.add_argument("--image-dir", default="images", help="Folder containing matching image files for vocab cards.")
    parser.add_argument("--list-chapters", action="store_true", help="Print the available chapter names and exit.")
    args = parser.parse_args()

    entries = load_entries(args.files)
    if args.list_chapters:
        for chapter in list_chapters(entries):
            print(chapter)
        raise SystemExit(0)

    include_vocab = args.mode in {"all", "vocab"}
    include_verbs = args.mode in {"all", "verbs"}

    display = "picture" if args.image_mode else args.display
    if display is None:
        display = "picture" if args.memorize else "text"

    if args.memorize:
        run_memorize(
            entries,
            chapter=args.chapter,
            limit=args.limit,
            display=display,
            image_dir=Path(args.image_dir),
            delay=args.delay,
        )
    elif args.learn:
        run_learn(entries, chapter=args.chapter, include_vocab=include_vocab, include_verbs=include_verbs)
    else:
        run_quiz(
            entries,
            chapter=args.chapter,
            limit=args.limit,
            include_vocab=include_vocab,
            include_verbs=include_verbs,
            display=display,
            image_dir=Path(args.image_dir),
            ignore_punctuation=args.ignore_punctuation,
            ignore_accents=args.ignore_accents,
        )


if __name__ == "__main__":
    main()
