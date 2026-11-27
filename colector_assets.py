import os
import json
import urllib.request
import urllib.error
from datetime import datetime

# Rutas principales del proyecto y del catálogo
PATH_RAIZ = r"C:\Proyectos\GodotPro-Catalog-Index"
PATH_JSON = os.path.join(PATH_RAIZ, "catalogo.json")
PATH_ASSETS = os.path.join(PATH_RAIZ, "assets")
PATH_PERSONAJES = os.path.join(PATH_ASSETS, "personajes")
PATH_TEXTURAS = os.path.join(PATH_ASSETS, "texturas")
URL_BASE_GITHUB = "https://raw.githubusercontent.com/Vulgarcin/GodotPro-Catalog-Index/main"

# Topes masivos configurables para evitar que el catálogo crezca sin control
MAX_ENTIDADES_CATALOGO = 5000
MAX_TEXTURAS_CATALOGO = 5000

# Repositorios públicos de GitHub para absorción automática (casas/castillos/edificios, personas y animales)
REPOS_GITHUB_PUBLICOS = [
    "kayquer/kit-cidade-lowpoly",
    "kayquer/scitizia-pessoas-64",
    "Vuena/free-low-poly-animals-cc0",
    "KhronosGroup/glTF-Sample-Models",
    "pmndrs/three-stdlib",
]

# Extensiones admitidas para bloques 3D y texturas
EXTENSIONES_3D = (".tscn", ".scn", ".res", ".glb", ".gltf", ".obj", ".fbx")
EXTENSIONES_TEXTURA = (".png", ".jpg", ".jpeg", ".webp")


def inicializar_o_cargar_catalogo():
    """Carga el catálogo existente si es válido o crea una estructura nueva vacía."""
    if os.path.exists(PATH_JSON):
        try:
            with open(PATH_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "entities" in data:
                    data.setdefault("textures", [])
                    return data
        except Exception as err:
            print(f"Aviso: No se pudo leer catalogo.json previo ({err}). Se creará uno nuevo.")

    return {
        "catalog_version": datetime.now().strftime("%Y.%m.%d"),
        "source_repo": "https://github.com/Vulgarcin/GodotPro-Catalog-Index",
        "entities": [],
        "textures": [],
    }


def clasificar_asset(raiz, id_asset):
    """Clasifica un asset en categoría y subcategoría según su carpeta y nombre."""
    ruta_baja = raiz.lower()
    if any(k in ruta_baja or k in id_asset for k in (
        "personaje", "pj", "pessoa", "pessoas", "velho", "velha", "idoso", "idosa",
        "human", "character", "avatar", "man", "woman"
    )):
        return "Personajes", "Agentes"
    if any(k in ruta_baja or k in id_asset for k in (
        "gato", "cat", "mascota", "animal", "perro", "fauna", "dog", "bird", "horse", "cow", "sheep"
    )):
        return "Personajes", "Animales"
    if any(k in ruta_baja or k in id_asset for k in (
        "silla", "mesa", "chimenea", "mueble", "cama", "sofa", "mobiliario", "furniture"
    )):
        return "Mobiliario", "Interiores"
    if any(k in ruta_baja or k in id_asset for k in (
        "flora", "arbol", "arvore", "cesped", "planta", "arbusto"
    )):
        return "Naturaleza", "Flora"
    if any(k in ruta_baja or k in id_asset for k in (
        "carro", "carrito", "carroza", "vehiculo", "auto", "veiculo", "onibus"
    )):
        return "Vehiculos", "Transporte"
    if any(k in ruta_baja or k in id_asset for k in (
        "casa", "castillo", "edificio", "house", "castle", "building", "tower", "ciudad", "city"
    )):
        return "Estructuras", "GrandesEstructuras"
    return "Estructuras", "Construccion"


def escanear_y_actualizar_assets():
    """Escanea archivos locales y repositorios públicos sin duplicar ni superar los topes."""
    print("Supermaquina Colector: Iniciando escaneo de bloques 3D y texturas...")
    catalogo = inicializar_o_cargar_catalogo()
    entidades = catalogo.get("entities", [])
    texturas = catalogo.get("textures", [])

    # Conjuntos de control para impedir duplicados por id, ruta en caché o URL de descarga
    ids_existentes = {e.get("id") for e in entidades if e.get("id")}
    rutas_3d_existentes = {e.get("ruta_cache_godot") for e in entidades if e.get("ruta_cache_godot")}
    urls_3d_existentes = {e.get("url_descarga") for e in entidades if e.get("url_descarga")}
    rutas_tex_existentes = {t.get("ruta_cache_godot") for t in texturas if t.get("ruta_cache_godot")}
    urls_tex_existentes = {t.get("url_descarga") for t in texturas if t.get("url_descarga")}

    # Asegura que existan las carpetas base de trabajo
    for carpeta in (PATH_ASSETS, PATH_PERSONAJES, PATH_TEXTURAS):
        if not os.path.exists(carpeta):
            os.makedirs(carpeta)
            print(f"Supermaquina Colector: Carpeta creada en {carpeta}")

    nuevos_assets = 0
    nuevas_texturas = 0
    tope_alcanzado = False

    # 1. Escaneo local dentro del proyecto (omitiendo .git)
    for raiz, _, archivos in os.walk(PATH_RAIZ):
        if ".git" in raiz.split(os.sep):
            continue

        for archivo in archivos:
            archivo_bajo = archivo.lower()
            ruta_completa = os.path.join(raiz, archivo)
            ruta_relativa = os.path.relpath(ruta_completa, PATH_RAIZ).replace(os.sep, "/")

            if archivo_bajo.endswith(EXTENSIONES_3D):
                if len(entidades) >= MAX_ENTIDADES_CATALOGO:
                    tope_alcanzado = True
                    continue

                nombre_base, _ = os.path.splitext(archivo)
                id_base = nombre_base.lower().replace(" ", "_")
                ruta_cache = f"res://catalogo_cache/{ruta_relativa}"
                url_descarga = f"{URL_BASE_GITHUB}/{ruta_relativa}"

                if ruta_cache in rutas_3d_existentes or url_descarga in urls_3d_existentes:
                    continue

                id_asset = id_base
                contador = 2
                while id_asset in ids_existentes:
                    id_asset = f"{id_base}_{contador}"
                    contador += 1

                categoria, subcategoria = clasificar_asset(raiz, id_asset)
                es_muro = any(k in id_asset for k in ("muro", "pared", "tapiz"))
                requiere_perforacion = any(k in id_asset for k in ("ventana", "puerta", "escalera"))
                es_personaje = categoria == "Personajes"
                celdas_xyz = [1, 3, 0.2] if es_muro else [1, 1, 1]

                entidades.append({
                    "id": id_asset,
                    "categoria": categoria,
                    "subcategoria": subcategoria,
                    "nombre_visual": id_asset.replace("_", " ").title(),
                    "archivo": archivo,
                    "url_descarga": url_descarga,
                    "ruta_cache_godot": ruta_cache,
                    "origen": "local",
                    "propiedades_rejilla": {
                        "tamano_celdas_xyz": celdas_xyz,
                        "origen_pivote": [0.5, 0, 0.5],
                        "magnetico": not es_personaje,
                    },
                    "comportamiento_motor": {
                        "es_muro_elastico": es_muro,
                        "perforacion_automatica": requiere_perforacion,
                        "tipo_colision": "Muro_CSG" if (es_muro or requiere_perforacion) else ("Agente_Movil" if es_personaje else "Estatica_Solida"),
                    },
                })
                ids_existentes.add(id_asset)
                rutas_3d_existentes.add(ruta_cache)
                urls_3d_existentes.add(url_descarga)
                nuevos_assets += 1
                print(f"-> Indexado 3D: {id_asset} [{categoria} / {subcategoria}]")

            elif archivo_bajo.endswith(EXTENSIONES_TEXTURA):
                if len(texturas) >= MAX_TEXTURAS_CATALOGO:
                    tope_alcanzado = True
                    continue

                ruta_cache_tex = f"res://catalogo_cache/{ruta_relativa}"
                url_tex = f"{URL_BASE_GITHUB}/{ruta_relativa}"
                if ruta_cache_tex in rutas_tex_existentes or url_tex in urls_tex_existentes:
                    continue

                nombre_base, _ = os.path.splitext(archivo)
                id_tex = nombre_base.lower().replace(" ", "_")

                texturas.append({
                    "id": id_tex,
                    "archivo": archivo,
                    "url_descarga": url_tex,
                    "ruta_cache_godot": ruta_cache_tex,
                    "origen": "local",
                })
                rutas_tex_existentes.add(ruta_cache_tex)
                urls_tex_existentes.add(url_tex)
                nuevas_texturas += 1
                print(f"-> Indexada textura: {archivo}")

    # 2. Absorción automática desde repositorios públicos de GitHub (solo índices y URLs)
    for repo in REPOS_GITHUB_PUBLICOS:
        if len(entidades) >= MAX_ENTIDADES_CATALOGO and len(texturas) >= MAX_TEXTURAS_CATALOGO:
            tope_alcanzado = True
            break
        try:
            api_url = f"https://api.github.com/repos/{repo}/git/trees/HEAD?recursive=1"
            req = urllib.request.Request(api_url, headers={"User-Agent": "GodotPro-Catalog-Collector"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                for item in payload.get("tree", []):
                    if item.get("type") != "blob":
                        continue
                    ruta_remota = item.get("path", "")
                    baja_remota = ruta_remota.lower()
                    archivo_remoto = os.path.basename(ruta_remota)
                    nombre_base, _ = os.path.splitext(archivo_remoto)
                    id_base = nombre_base.lower().replace(" ", "_")
                    url_raw = f"https://raw.githubusercontent.com/{repo}/HEAD/{ruta_remota}"
                    ruta_cache_remota = f"res://catalogo_cache/remoto/{repo.replace('/', '_')}/{ruta_remota}"

                    if baja_remota.endswith(EXTENSIONES_3D):
                        if len(entidades) >= MAX_ENTIDADES_CATALOGO:
                            tope_alcanzado = True
                            break
                        if url_raw in urls_3d_existentes or ruta_cache_remota in rutas_3d_existentes:
                            continue

                        id_asset = id_base
                        contador = 2
                        while id_asset in ids_existentes:
                            id_asset = f"{id_base}_{contador}"
                            contador += 1

                        categoria, subcategoria = clasificar_asset(ruta_remota, id_asset)
                        es_muro = any(k in id_asset for k in ("muro", "pared", "tapiz"))
                        requiere_perforacion = any(k in id_asset for k in ("ventana", "puerta", "escalera"))
                        es_personaje = categoria == "Personajes"

                        entidades.append({
                            "id": id_asset,
                            "categoria": categoria,
                            "subcategoria": subcategoria,
                            "nombre_visual": id_asset.replace("_", " ").title(),
                            "archivo": archivo_remoto,
                            "url_descarga": url_raw,
                            "ruta_cache_godot": ruta_cache_remota,
                            "origen": f"github:{repo}",
                            "propiedades_rejilla": {
                                "tamano_celdas_xyz": [1, 3, 0.2] if es_muro else [1, 1, 1],
                                "origen_pivote": [0.5, 0, 0.5],
                                "magnetico": not es_personaje,
                            },
                            "comportamiento_motor": {
                                "es_muro_elastico": es_muro,
                                "perforacion_automatica": requiere_perforacion,
                                "tipo_colision": "Muro_CSG" if (es_muro or requiere_perforacion) else ("Agente_Movil" if es_personaje else "Estatica_Solida"),
                            },
                        })
                        ids_existentes.add(id_asset)
                        urls_3d_existentes.add(url_raw)
                        rutas_3d_existentes.add(ruta_cache_remota)
                        nuevos_assets += 1

                    elif baja_remota.endswith(EXTENSIONES_TEXTURA):
                        if len(texturas) >= MAX_TEXTURAS_CATALOGO:
                            tope_alcanzado = True
                            break
                        if url_raw in urls_tex_existentes or ruta_cache_remota in rutas_tex_existentes:
                            continue

                        texturas.append({
                            "id": id_base,
                            "archivo": archivo_remoto,
                            "url_descarga": url_raw,
                            "ruta_cache_godot": ruta_cache_remota,
                            "origen": f"github:{repo}",
                        })
                        urls_tex_existentes.add(url_raw)
                        rutas_tex_existentes.add(ruta_cache_remota)
                        nuevas_texturas += 1
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as err:
            print(f"Aviso: No se pudo consultar {repo} ({err}). Continuando con fuentes disponibles...")
        except Exception as err:
            print(f"Aviso inesperado al consultar {repo}: {err}")

    catalogo["entities"] = entidades
    catalogo["textures"] = texturas
    catalogo["limits"] = {
        "max_entities": MAX_ENTIDADES_CATALOGO,
        "max_textures": MAX_TEXTURAS_CATALOGO,
        "tope_alcanzado": tope_alcanzado,
    }

    if nuevos_assets > 0 or nuevas_texturas > 0:
        catalogo["catalog_version"] = datetime.now().strftime("%Y.%m.%d")
        with open(PATH_JSON, "w", encoding="utf-8") as f:
            json.dump(catalogo, f, indent=2, ensure_ascii=False)
        print(f"Listo! {nuevos_assets} bloques 3D y {nuevas_texturas} texturas nuevas guardados en catalogo.json.")
    else:
        print("El catalogo esta al dia. Mete modelos 3D o texturas o agrega repositorios para indexarlos.")

    if tope_alcanzado:
        print(f"Tope masivo alcanzado ({MAX_ENTIDADES_CATALOGO} entidades / {MAX_TEXTURAS_CATALOGO} texturas). No se añadieron extras.")


if __name__ == "__main__":
    try:
        escanear_y_actualizar_assets()
    except Exception as exc:
        print(f"Error crítico en Supermaquina Colector: {exc}")
