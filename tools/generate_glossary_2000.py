# tools/generate_glossary_2000.py
# Generates a large Spanish -> Guaraní glossary CSV with varied topics.
# Output file default: data/guarani_glossary_2000.csv
# Usage:
#   python tools/generate_glossary_2000.py
#   python tools/generate_glossary_2000.py --out data/myfile.csv --limit 2000

import csv
import random
from pathlib import Path
import argparse

random.seed(42)

def add_unique(rows, es, gn, note, seen):
    key = (es.strip().lower(), gn.strip().lower())
    if es and gn and key not in seen:
        rows.append((es.strip(), gn.strip(), note))
        seen.add(key)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/guarani_glossary_2000.csv")
    parser.add_argument("--limit", type=int, default=2000)
    args = parser.parse_args()

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    seen = set()

    # Core seeds (words and short phrases) — curated
    greetings = [
        ("Buenos días", "Ko'ẽ porã", "saludo"),
        ("Buenas tardes", "Ka'aru porã", "saludo"),
        ("Buenas noches", "Pyhare porã", "saludo"),
        ("Hola", "Maitei", "saludo"),
        ("¿Cómo estás?", "Mba'éichapa", "saludo/estado"),
        ("Estoy bien", "Iporã", "respuesta"),
        ("Gracias", "Aguyje", "cortesía"),
        ("Muchas gracias", "Aguyje eterei", "cortesía"),
        ("De nada", "Ndaipóri", "cortesía"),
        ("Por favor", "Ikatúpa", "cortesía"),
        ("Perdón", "Eñyrõ", "cortesía"),
        ("Nos vemos", "Jajohecha peve", "despedida"),
        ("Buen viaje", "Tape porã", "deseo"),
        ("Bienvenido", "Tereguahẽ porã", "bienvenida"),
    ]

    numbers = [
        ("Uno", "Peteĩ", "número"),
        ("Dos", "Mokõi", "número"),
        ("Tres", "Mbohapy", "número"),
        ("Cuatro", "Irundy", "número"),
        ("Cinco", "Po", "número"),
        ("Seis", "Poteĩ", "número"),
        ("Siete", "Pokõi", "número"),
        ("Ocho", "Poapy", "número"),
        ("Nueve", "Porundy", "número"),
        ("Diez", "Pa", "número"),
    ]

    colors = [
        ("Rojo", "Pytã"),
        ("Azul", "Hovy"),
        ("Negro", "Hũ"),
        ("Blanco", "Morotĩ"),
        ("Verde", "Hovyũ"),
        ("Amarillo", "Sa'yju"),
        ("Naranja", "Narã"),
        ("Violeta", "Hovyũ pytã"),
        ("Rosa", "Pytã asy"),
        ("Marrón", "Hũ sa'yju"),
    ]

    adjectives = [
        ("grande", "guasu"),
        ("pequeño", "michĩ"),
        ("bonito", "porã"),
        ("feo", "vai"),
        ("rápido", "pya'e"),
        ("lento", "mbeguemi"),
        ("nuevo", "pyahu"),
        ("viejo", "tuja"),
        ("caro", "hepy"),
        ("barato", "hepy'ỹ"),
        ("limpio", "potĩ"),
        ("sucio", "ky'a"),
        ("caliente", "haku"),
        ("frío", "ro'y"),
        ("fácil", "hasy'ỹ"),
        ("difícil", "hasý"),
        ("pesado", "pohy"),
        ("liviano", "vevúi"),
    ]

    animals = [
        ("Perro", "Jagua"), ("Gato", "Mbarakaja"), ("Pájaro", "Guyra"), ("Caballo", "Kavaju"),
        ("Vaca", "Vaka"), ("Cerdo", "Kure"), ("Gallina", "Ryguasu"), ("Pato", "Pato"),
        ("Pez", "Pira"), ("Tortuga", "Karaí"), ("Mono", "Karaí kavaju?"), ("Zorro", "Aguara"),
        ("Armadillo", "Tatu"), ("Yacaré", "Jakare"), ("Abeja", "Eíra"), ("Hormiga", "Tapi'í"),
        ("Mariposa", "Panambi"), ("Sapo", "Kururu"), ("Loro", "Tu'i"), ("Buho", "Urukure'a"),
        ("Águila", "Taguato"), ("Colibrí", "Mainumby"), ("Murciélago", "Mbopi"), ("Zorrino", "Suru"),
        ("Lechuza", "Mbopi'i"),
    ]

    foods = [
        ("Pan", "Mbujapé"), ("Leche", "Kamby"), ("Agua", "Y"), ("Carne", "So'o"),
        ("Maíz", "Avati"), ("Fruta", "Yva"), ("Yerba mate", "Ka'a"), ("Tereré", "Tereré"),
        ("Café", "Kafe"), ("Azúcar", "Azuka"), ("Sal", "Juky"), ("Arroz", "Arro"),
        ("Sopa", "Sopa"), ("Mandioca", "Mandi'o"), ("Queso", "Kesú"), ("Harina", "Harina"),
        ("Aceite", "Aceite"), ("Huevo", "Rupi'a"), ("Pollo", "Ryguasu so'o"), ("Tomate", "Tomáte"),
        ("Cebolla", "Sevolla"), ("Pimienta", "Kỹikĩ"), ("Ajo", "Ajo"), ("Naranja", "Narã yva"),
        ("Banana", "Pakova"), ("Manzana", "Yva pytã"), ("Uva", "Yva rykue"), ("Sandía", "Sandía"),
        ("Papaya", "Mamón"), ("Piña", "Karapepẽ"),
    ]

    fruits = [
        ("Manzana", "Yva pytã"), ("Pera", "Perá"), ("Uva", "Yva rykue"),
        ("Sandía", "Sandía"), ("Melón", "Melón"), ("Banana", "Pakova"),
        ("Naranja", "Narã yva"), ("Mandarina", "Mandarina"), ("Papaya", "Mamón"),
        ("Piña", "Karapepẽ"), ("Frutilla", "Frutilla"), ("Mango", "Mango"),
    ]

    vegetables = [
        ("Tomate", "Tomáte"), ("Cebolla", "Sevolla"), ("Papa", "Papa"),
        ("Zanahoria", "Zanahoria"), ("Lechuga", "Lechuga"), ("Repollo", "Repollo"),
        ("Pepino", "Pepino"), ("Ajo", "Ajo"), ("Pimiento", "Pimiẽta"),
        ("Calabaza", "Kurapepẽ"), ("Maíz", "Avati"), ("Poroto", "Kumanda"),
    ]

    body_parts = [
        ("Cabeza", "Akã"), ("Ojo", "Tesa"), ("Boca", "Juru"), ("Nariz", "Tĩ"),
        ("Oreja", "Apysa"), ("Mano", "Po"), ("Pie", "Py"), ("Brazo", "Jyva"),
        ("Pierna", "Tetyma"), ("Hombro", "Atukupe"), ("Espalda", "Atukupe kupe"),
        ("Corazón", "Py'a"), ("Estómago", "Tye"), ("Diente", "Tã"),
    ]

    household = [
        ("Casa", "Óga"), ("Puerta", "Okẽ"), ("Ventana", "Ovetã"), ("Mesa", "Atyha"),
        ("Silla", "Guapyha"), ("Cama", "Tupao"), ("Cocina", "Kokina"), ("Baño", "Jahuha"),
        ("Habitación", "Kotý"), ("Patio", "Kora"), ("Techo", "Apytere"), ("Piso", "Yvy"),
        ("Cuchillo", "Kuchillo"), ("Tenedor", "Tenédor"), ("Cuchara", "Kucharã"),
        ("Vaso", "Hy'áiha"), ("Plato", "Atyha'i"), ("Olla", "Kyguãi"),
    ]

    nature_places = [
        ("Río", "Ysyry"), ("Lago", "Ypa"), ("Selva", "Ka'aguasu"), ("Árbol", "Yvyra"),
        ("Tierra", "Yvy"), ("Fuego", "Tata"), ("Viento", "Yvytu"), ("Lluvia", "Ama"),
        ("Sol", "Kuarahy"), ("Luna", "Jasy"), ("Estrella", "Mbyja"),
        ("Camino", "Tape"), ("Ciudad", "Táva"), ("Campo", "Okára"), ("Iglesia", "Tupao"),
        ("Plaza", "Plása"), ("Mercado", "Merkádo"), ("Hospital", "Pohãno renda"), ("Escuela", "Mbo'ehao"),
    ]

    school = [
        ("Maestro", "Mbo'ehára"), ("Estudiante", "Temimbo'e"),
        ("Escuela", "Mbo'ehao"), ("Libro", "Kuatiarogue"),
        ("Cuaderno", "Kuatiakuéra"), ("Lápiz", "Yvyra'i haiha"),
        ("Lapicera", "Haiha"), ("Clase", "Mbo'epy"),
        ("Tarea", "Mba'apo róga"), ("Examen", "Porandu guasu"),
    ]

    family = [
        ("Padre", "Túva"), ("Madre", "Sy"), ("Hijo", "Ta'ýra"), ("Hija", "Rajy"),
        ("Esposo", "Ména"), ("Esposa", "Tembireko"), ("Abuelo", "Taitaguasu"),
        ("Abuela", "Jarýi"), ("Tío", "Tío"), ("Tía", "Tía"),
        ("Primo", "Prímo"), ("Prima", "Príma"), ("Amigo", "Angirũ"), ("Vecino", "Vecino"),
    ]

    verbs_basic = [
        ("Comer", "Karu"), ("Beber", "U"), ("Dormir", "Ke"), ("Caminar", "Guata"),
        ("Hablar", "Ñe'ẽ"), ("Escuchar", "Hendu"), ("Ver", "Hecha"),
        ("Leer", "Moñe'ẽ"), ("Escribir", "Hai"), ("Abrir", "Pe'a"),
        ("Cerrar", "Mboty"), ("Comprar", "Jogua"), ("Vender", "Ñemu"),
        ("Ir", "Ho"), ("Venir", "Ju"), ("Querer", "Potá"), ("Necesitar", "Tekotevẽ"),
        ("Saber", "Kuaa"), ("Recordar", "Mandu'a"), ("Olvidar", "Resarái"),
    ]

    # 1) Add core seeds
    for es, gn, note in greetings + numbers:
        add_unique(rows, es, gn, note, seen)

    for es, gn in colors:
        add_unique(rows, es, gn, "color", seen)

    for bank, tag in [
        (animals, "animal"),
        (foods, "alimento"),
        (fruits, "fruta"),
        (vegetables, "verdura"),
        (body_parts, "cuerpo"),
        (household, "hogar"),
        (nature_places, "lugar/naturaleza"),
        (school, "escuela"),
        (family, "familia"),
        (verbs_basic, "verbo"),
    ]:
        for es, gn in bank:
            add_unique(rows, es, gn, tag, seen)

    # 2) Generate combinations: animal + color  (e.g., "Perro negro" -> "Jagua hũ")
    for (es_a, gn_a) in animals:
        for (es_c, gn_c) in colors:
            add_unique(rows, f"{es_a} {es_c.lower()}", f"{gn_a} {gn_c}", "animal+color", seen)

    # 3) noun + adjective combos (household + adjectives, nature + adjectives)
    noun_sets = household + nature_places + foods + animals
    adj_short = adjectives[:10]  # keep it reasonable
    for (es_n, gn_n) in noun_sets:
        for (es_adj, gn_adj) in adj_short:
            add_unique(rows, f"{es_n} {es_adj}", f"{gn_n} {gn_adj}", "sintagma nominal", seen)

    # 4) possessives (Mi/Tu/Nuestro incl./excl.) for family nouns
    poss = [
        ("Mi", "Che"),
        ("Tu", "Nde"),
        ("Nuestro", "Ñande"),  # incl.
        ("Nuestro (excl.)", "Ore"),
    ]
    for (es_poss, gn_poss) in poss:
        for es_fam, gn_fam in family:
            add_unique(rows, f"{es_poss} {es_fam.lower()}", f"{gn_poss} {gn_fam}", "posesivo+familia", seen)

    # 5) simple phrase templates (safe)
    # Quiero + alimento  -> Aipota + alimento
    for es_food, gn_food in foods + fruits + vegetables:
        add_unique(rows, f"Quiero {es_food.lower()}", f"Aipota {gn_food}", "frase: deseo", seen)
    # Necesito + objeto/lugar -> Aikotevẽ + ...
    for es_n, gn_n in household + nature_places:
        add_unique(rows, f"Necesito {es_n.lower()}", f"Aikotevẽ {gn_n}", "frase: necesidad", seen)

    # 6) make sure we reach the requested limit; if over, trim deterministically
    # Shuffle lightly for variety, then cut
    random.shuffle(rows)
    target = args.limit
    if len(rows) < target:
        print(f"Generated {len(rows)} rows (< {target}). Still fine — import will work.")
    if len(rows) > target:
        rows = rows[:target]

    # Write CSV
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["es", "gn", "notes"])
        for es, gn, note in rows:
            w.writerow([es, gn, note])

    print(f"Saved: {out_path}  ({len(rows)} rows)")

if __name__ == "__main__":
    main()