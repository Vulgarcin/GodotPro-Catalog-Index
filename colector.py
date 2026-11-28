import os
import json
import urllib.request
import urllib.error
from datetime import datetime

# Rutas principales del proyecto y del catálogo
PATH_RAIZ = os.path.abspath(".")
PATH_JSON = os.path.join(PATH_RAIZ, "catalogo.json")
PATH_ASSETS = os.path.join(PATH_RAIZ, "assets")
PATH_PERSONAJES = os.path.join(PATH_ASSETS, "personajes")
PATH_TEXTURAS = os.path.join(PATH_ASSETS, "texturas")
URL_BASE_GITHUB = "https://raw.githubusercontent.com/Vulgarcin/GodotPro-Catalog-Index/main"

# Topes configurables para evitar que el catálogo crezca sin control
MAX_ENTIDADES_CATALOGO = 5000
MAX_TEXTURAS_CATALOGO = 5000
MAX_POLYHAVEN_MODELS = 250

# Repositorios públicos de GitHub con modelos modulares, animales, personajes y PBR
REPOS_GITHUB_PUBLICOS = [
    "Quaternius/Ultimate-Modular-Men-Pack",
    "Quaternius/Ultimate-Animated-Animal-Pack",
    "Quaternius/Ultimate-Modular-Sci-Fi-Pack",
    "KhronosGroup/glTF-Sample-Models",
    "KhronosGroup/glTF-Sample-Assets",
    "pmndrs/three-stdlib",
]

# Extensiones admitidas para modelos 3D, texturas y vistas previas
EXTENSIONES_3D = (".tscn", ".scn", ".res", ".glb", ".gltf", ".obj", ".fbx")
EXTENSIONES_TEXTURA = (".png", ".jpg", ".jpeg", ".webp")
EXTENSIONES_BINARIO = (".bin",)


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


def clasificar_asset(ruta, id_asset):
    """Clasifica un asset en categoría y subcategoría según su carpeta y nombre."""
    texto = f"{ruta} {id_asset}".lower()
    if any(k in texto for k in (
        "gato", "cat", "kitten", "felino", "mascota", "animal", "perro", "dog",
        "zorro", "fox", "fauna", "bird", "horse", "cow", "sheep", "wolf", "deer"
    )):
        return "Personajes", "Animales"
    if any(k in texto for k in (
        "personaje", "pj", "pessoa", "pessoas", "human", "character", "avatar",
        "man", "woman", "farmer", "granjero", "pilot", "piloto", "knight", "modular_men"
    )):
        return "Personajes", "Agentes"
    if any(k in texto for k in (
        "puerta", "door", "doorway", "ventana", "window", "escalera", "stairs"
    )):
        return "Estructuras", "Interactuables"
    if any(k in texto for k in (
        "silla", "chair", "mesa", "table", "chimenea", "mueble", "cama", "bed",
        "sofa", "couch", "mobiliario", "furniture", "cabinet", "shelf", "lamp", "lantern"
    )):
        return "Mobiliario", "Interiores"
    if any(k in texto for k in (
        "flora", "arbol", "tree", "arvore", "cesped", "grass", "planta", "plant",
        "arbusto", "bush", "fern", "rock", "roca", "potted"
    )):
        return "Naturaleza", "Flora"
    if any(k in texto for k in (
        "carro", "car", "carrito", "carroza", "vehiculo", "vehicle", "auto", "truck", "bus"
    )):
        return "Vehiculos", "Transporte"
    if any(k in texto for k in (
        "casa", "castillo", "edificio", "house", "castle", "building", "tower",
        "ciudad", "city", "wall", "muro", "pared", "roof", "techo", "floor", "piso"
    )):
        return "Estructuras", "GrandesEstructuras"
    return "Estructuras", "Construccion"


def limpiar_clave_busqueda(nombre_sin_ext):
    """Normaliza el nombre base quitando sufijos PBR comunes para emparejar modelos y texturas."""
    clave = nombre_sin_ext.lower().replace(" ", "_").replace("-", "_")
    sufijos_pbr = (
        "_diffuse", "_albedo", "_basecolor", "_base_color", "_color", "_col",
        "_normal", "_nor", "_nrm", "_roughness", "_rough", "_metallic", "_metal",
        "_ao", "_ambientocclusion", "_height", "_bump", "_orm", "_tex", "_texture",
        "_1k", "_2k", "_4k", "_diff"
    )
    for suf in sufijos_pbr:
        if clave.endswith(suf):
            clave = clave[: -len(suf)]
            break
    return clave


def buscar_mejor_textura(id_base, carpeta_relativa, mapa_texturas_por_clave, mapa_texturas_por_carpeta):
    """Encuentra la textura principal (Albedo/Diffuse o coincidente) y texturas PBR asociadas."""
    clave_norm = limpiar_clave_busqueda(id_base)
    candidatas = []

    if clave_norm in mapa_texturas_por_clave:
        candidatas.extend(mapa_texturas_por_clave[clave_norm])

    if carpeta_relativa in mapa_texturas_por_carpeta:
        for tex in mapa_texturas_por_carpeta[carpeta_relativa]:
            if tex not in candidatas:
                candidatas.append(tex)

    if not candidatas and len(clave_norm) >= 4:
        for clave_tex, lista_tex in mapa_texturas_por_clave.items():
            if clave_norm in clave_tex or clave_tex in clave_norm:
                for tex in lista_tex:
                    if tex not in candidatas:
                        candidatas.append(tex)
                if len(candidatas) >= 6:
                    break

    if not candidatas:
        return "", []

    url_principal = candidatas[0]
    for url in candidatas:
        baja = url.lower()
        if any(tag in baja for tag in ("albedo", "diffuse", "diff", "basecolor", "base_color", "color", "_col")):
            url_principal = url
            break

    return url_principal, candidatas[:8]


def absorber_poly_haven(entidades, texturas, ids_existentes, urls_3d_existentes, rutas_3d_existentes, urls_tex_existentes, rutas_tex_existentes):
    """Consulta la API pública de Poly Haven (CC0) para indexar modelos 3D .gltf, su .bin y sus texturas PBR."""
    nuevos_modelos = 0
    nuevas_tex = 0
    try:
        req = urllib.request.Request(
            "https://api.polyhaven.com/assets?t=models",
            headers={"User-Agent": "GodotPro-Catalog-Collector"}
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            catalogo_ph = json.loads(resp.read().decode("utf-8"))
    except Exception as err:
        print(f"Aviso: No se pudo consultar Poly Haven ({err}). Continuando...")
        return 0, 0

    for asset_id, meta in list(catalogo_ph.items())[:MAX_POLYHAVEN_MODELS]:
        if len(entidades) >= MAX_ENTIDADES_CATALOGO:
            break
        try:
            req_files = urllib.request.Request(
                f"https://api.polyhaven.com/files/{asset_id}",
                headers={"User-Agent": "GodotPro-Catalog-Collector"}
            )
            with urllib.request.urlopen(req_files, timeout=12) as resp_f:
                files_data = json.loads(resp_f.read().decode("utf-8"))
        except Exception:
            continue

        gltf_info = files_data.get("gltf", {}).get("1k", {}).get("gltf", {})
        url_gltf = gltf_info.get("url", "")
        if not url_gltf or url_gltf in urls_3d_existentes:
            continue

        include_map = gltf_info.get("include", {})
        archivos_vinculados = []
        url_textura_principal = ""

        for rel_path, inc_info in include_map.items():
            url_inc = inc_info.get("url", "")
            if not url_inc:
                continue
            baja_rel = rel_path.lower()
            if baja_rel.endswith(EXTENSIONES_TEXTURA) or baja_rel.endswith(EXTENSIONES_BINARIO):
                archivos_vinculados.append(url_inc)
                if baja_rel.endswith(EXTENSIONES_TEXTURA):
                    if any(tag in baja_rel for tag in ("diff", "albedo", "color", "base")) and not url_textura_principal:
                        url_textura_principal = url_inc

                    if len(texturas) < MAX_TEXTURAS_CATALOGO and url_inc not in urls_tex_existentes:
                        ruta_cache_tex = f"res://catalogo_cache/remoto/polyhaven/{asset_id}/{rel_path}"
                        texturas.append({
                            "id": f"{asset_id}_{os.path.splitext(os.path.basename(rel_path))[0]}".lower(),
                            "archivo": os.path.basename(rel_path),
                            "url_descarga": url_inc,
                            "ruta_cache_godot": ruta_cache_tex,
                            "origen": "polyhaven:cc0",
                        })
                        urls_tex_existentes.add(url_inc)
                        rutas_tex_existentes.add(ruta_cache_tex)
                        nuevas_tex += 1

        if not url_textura_principal:
            for u in archivos_vinculados:
                if u.lower().endswith(EXTENSIONES_TEXTURA):
                    url_textura_principal = u
                    break

        url_preview = f"https://cdn.polyhaven.com/asset_img/thumbs/{asset_id}.png?width=512"
        categorias_ph = " ".join(meta.get("categories", []))
        categoria, subcategoria = clasificar_asset(categorias_ph, asset_id)

        id_final = f"ph_{asset_id}".lower().replace(" ", "_")
        contador = 2
        while id_final in ids_existentes:
            id_final = f"ph_{asset_id}_{contador}".lower()
            contador += 1

        ruta_cache_gltf = f"res://catalogo_cache/remoto/polyhaven/{asset_id}/{asset_id}_1k.gltf"
        es_puerta = any(k in id_final for k in ("door", "puerta"))
        es_muro = any(k in id_final for k in ("wall", "muro", "pared"))
        es_personaje = categoria == "Personajes"

        entidades.insert(0, {
            "id": id_final,
            "categoria": categoria,
            "subcategoria": subcategoria,
            "nombre_visual": meta.get("name", asset_id.replace("_", " ").title()),
            "archivo": f"{asset_id}_1k.gltf",
            "url_descarga": url_gltf,
            "url_textura": url_textura_principal,
            "texturas_vinculadas": archivos_vinculados,
            "url_preview": url_preview,
            "ruta_cache_godot": ruta_cache_gltf,
            "origen": "polyhaven:cc0",
            "propiedades_rejilla": {
                "tamano_celdas_xyz": [1, 3, 0.2] if es_muro else [1, 1, 1],
                "origen_pivote": [0.5, 0, 0.5],
                "magnetico": not es_personaje,
            },
            "comportamiento_motor": {
                "es_muro_elastico": es_muro,
                "perforacion_automatica": es_puerta,
                "tipo_colision": "Muro_CSG" if (es_muro or es_puerta) else ("Agente_Movil" if es_personaje else "Estatica_Solida"),
            },
        })
        ids_existentes.add(id_final)
        urls_3d_existentes.add(url_gltf)
        rutas_3d_existentes.add(ruta_cache_gltf)
        nuevos_modelos += 1

    print(f"Poly Haven: +{nuevos_modelos} modelos PBR y +{nuevas_tex} texturas indexadas.")
    return nuevos_modelos, nuevas_tex


def escanear_y_actualizar_assets():
    """Escanea Poly Haven, archivos locales y repositorios públicos vinculando cada modelo con sus texturas."""
    print("Supermaquina Colector: Iniciando escaneo de modelos 3D realistas/modulares y vinculación de texturas...")
    catalogo = inicializar_o_cargar_catalogo()
    entidades = catalogo.get("entities", [])
    texturas = catalogo.get("textures", [])

    ids_existentes = {e.get("id") for e in entidades if e.get("id")}
    rutas_3d_existentes = {e.get("ruta_cache_godot") for e in entidades if e.get("ruta_cache_godot")}
    urls_3d_existentes = {e.get("url_descarga") for e in entidades if e.get("url_descarga")}
    rutas_tex_existentes = {t.get("ruta_cache_godot") for t in texturas if t.get("ruta_cache_godot")}
    urls_tex_existentes = {t.get("url_descarga") for t in texturas if t.get("url_descarga")}

    for carpeta in (PATH_ASSETS, PATH_PERSONAJES, PATH_TEXTURAS):
        if not os.path.exists(carpeta):
            os.makedirs(carpeta)

    nuevos_assets = 0
    nuevas_texturas = 0
    tope_alcanzado = False

    # 1. Absorber modelos fotorrealistas PBR desde Poly Haven (CC0) y ponerlos al inicio del catálogo
    ph_modelos, ph_tex = absorber_poly_haven(
        entidades, texturas, ids_existentes, urls_3d_existentes, rutas_3d_existentes, urls_tex_existentes, rutas_tex_existentes
    )
    nuevos_assets += ph_modelos
    nuevas_texturas += ph_tex

    # 2. Indexar texturas locales
    mapa_tex_local_clave = {}
    mapa_tex_local_carpeta = {}
    previews_locales = {}

    for raiz, _, archivos in os.walk(PATH_RAIZ):
        if ".git" in raiz.split(os.sep):
            continue
        carpeta_rel = os.path.relpath(raiz, PATH_RAIZ).replace(os.sep, "/")

        for archivo in archivos:
            if not archivo.lower().endswith(EXTENSIONES_TEXTURA):
                continue

            ruta_completa = os.path.join(raiz, archivo)
            ruta_relativa = os.path.relpath(ruta_completa, PATH_RAIZ).replace(os.sep, "/")
            nombre_base, _ = os.path.splitext(archivo)
            clave_norm = limpiar_clave_busqueda(nombre_base)
            url_tex = f"{URL_BASE_GITHUB}/{ruta_relativa}"
            ruta_cache_tex = f"res://catalogo_cache/{ruta_relativa}"

            previews_locales[nombre_base.lower().replace(" ", "_")] = url_tex
            mapa_tex_local_clave.setdefault(clave_norm, []).append(url_tex)
            mapa_tex_local_carpeta.setdefault(carpeta_rel, []).append(url_tex)

            if len(texturas) < MAX_TEXTURAS_CATALOGO and url_tex not in urls_tex_existentes and ruta_cache_tex not in rutas_tex_existentes:
                texturas.append({
                    "id": nombre_base.lower().replace(" ", "_"),
                    "archivo": archivo,
                    "url_descarga": url_tex,
                    "ruta_cache_godot": ruta_cache_tex,
                    "origen": "local",
                })
                urls_tex_existentes.add(url_tex)
                rutas_tex_existentes.add(ruta_cache_tex)
                nuevas_texturas += 1

    # 3. Indexar modelos 3D locales
    for raiz, _, archivos in os.walk(PATH_RAIZ):
        if ".git" in raiz.split(os.sep):
            continue
        carpeta_rel = os.path.relpath(raiz, PATH_RAIZ).replace(os.sep, "/")

        for archivo in archivos:
            if not archivo.lower().endswith(EXTENSIONES_3D):
                continue
            if len(entidades) >= MAX_ENTIDADES_CATALOGO:
                tope_alcanzado = True
                continue

            ruta_completa = os.path.join(raiz, archivo)
            ruta_relativa = os.path.relpath(ruta_completa, PATH_RAIZ).replace(os.sep, "/")
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
            es_muro = any(k in id_asset for k in ("muro", "pared", "wall"))
            requiere_perforacion = any(k in id_asset for k in ("ventana", "window", "puerta", "door", "escalera", "stairs"))
            es_personaje = categoria == "Personajes"

            url_textura, texturas_vinculadas = buscar_mejor_textura(
                id_base, carpeta_rel, mapa_tex_local_clave, mapa_tex_local_carpeta
            )
            url_preview = previews_locales.get(id_base, url_textura)

            entidades.append({
                "id": id_asset,
                "categoria": categoria,
                "subcategoria": subcategoria,
                "nombre_visual": id_asset.replace("_", " ").title(),
                "archivo": archivo,
                "url_descarga": url_descarga,
                "url_textura": url_textura,
                "texturas_vinculadas": texturas_vinculadas,
                "url_preview": url_preview,
                "ruta_cache_godot": ruta_cache,
                "origen": "local",
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
            rutas_3d_existentes.add(ruta_cache)
            urls_3d_existentes.add(url_descarga)
            nuevos_assets += 1

    # 4. Absorción automática desde repositorios públicos de GitHub
    for repo in REPOS_GITHUB_PUBLICOS:
        if len(entidades) >= MAX_ENTIDADES_CATALOGO and len(texturas) >= MAX_TEXTURAS_CATALOGO:
            tope_alcanzado = True
            break
        try:
            api_url = f"https://api.github.com/repos/{repo}/git/trees/HEAD?recursive=1"
            req = urllib.request.Request(api_url, headers={"User-Agent": "GodotPro-Catalog-Collector"})
            with urllib.request.urlopen(req, timeout=14) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                arbol_repo = payload.get("tree", [])

            mapa_repo_tex_clave = {}
            mapa_repo_tex_carpeta = {}
            mapa_repo_prev = {}

            for item in arbol_repo:
                if item.get("type") != "blob":
                    continue
                ruta_remota = item.get("path", "")
                if not ruta_remota.lower().endswith(EXTENSIONES_TEXTURA):
                    continue

                carpeta_remota = os.path.dirname(ruta_remota)
                archivo_remoto = os.path.basename(ruta_remota)
                nombre_base, _ = os.path.splitext(archivo_remoto)
                clave_norm = limpiar_clave_busqueda(nombre_base)
                url_raw = f"https://raw.githubusercontent.com/{repo}/HEAD/{ruta_remota}"
                ruta_cache_remota = f"res://catalogo_cache/remoto/{repo.replace('/', '_')}/{ruta_remota}"

                mapa_repo_prev[nombre_base.lower().replace(" ", "_")] = url_raw
                mapa_repo_tex_clave.setdefault(clave_norm, []).append(url_raw)
                mapa_repo_tex_carpeta.setdefault(carpeta_remota, []).append(url_raw)

                if len(texturas) < MAX_TEXTURAS_CATALOGO and url_raw not in urls_tex_existentes and ruta_cache_remota not in rutas_tex_existentes:
                    texturas.append({
                        "id": nombre_base.lower().replace(" ", "_"),
                        "archivo": archivo_remoto,
                        "url_descarga": url_raw,
                        "ruta_cache_godot": ruta_cache_remota,
                        "origen": f"github:{repo}",
                    })
                    urls_tex_existentes.add(url_raw)
                    rutas_tex_existentes.add(ruta_cache_remota)
                    nuevas_texturas += 1

            for item in arbol_repo:
                if item.get("type") != "blob":
                    continue
                ruta_remota = item.get("path", "")
                if not ruta_remota.lower().endswith(EXTENSIONES_3D):
                    continue
                if len(entidades) >= MAX_ENTIDADES_CATALOGO:
                    tope_alcanzado = True
                    break

                carpeta_remota = os.path.dirname(ruta_remota)
                archivo_remoto = os.path.basename(ruta_remota)
                nombre_base, _ = os.path.splitext(archivo_remoto)
                id_base = nombre_base.lower().replace(" ", "_")
                url_raw = f"https://raw.githubusercontent.com/{repo}/HEAD/{ruta_remota}"
                ruta_cache_remota = f"res://catalogo_cache/remoto/{repo.replace('/', '_')}/{ruta_remota}"

                if url_raw in urls_3d_existentes or ruta_cache_remota in rutas_3d_existentes:
                    continue

                id_asset = id_base
                contador = 2
                while id_asset in ids_existentes:
                    id_asset = f"{id_base}_{contador}"
                    contador += 1

                categoria, subcategoria = clasificar_asset(ruta_remota, id_asset)
                es_muro = any(k in id_asset for k in ("muro", "pared", "wall"))
                requiere_perforacion = any(k in id_asset for k in ("ventana", "window", "puerta", "door", "escalera", "stairs"))
                es_personaje = categoria == "Personajes"

                url_textura, texturas_vinculadas = buscar_mejor_textura(
                    id_base, carpeta_remota, mapa_repo_tex_clave, mapa_repo_tex_carpeta
                )
                url_preview = mapa_repo_prev.get(id_base, url_textura)

                entidades.append({
                    "id": id_asset,
                    "categoria": categoria,
                    "subcategoria": subcategoria,
                    "nombre_visual": id_asset.replace("_", " ").title(),
                    "archivo": archivo_remoto,
                    "url_descarga": url_raw,
                    "url_textura": url_textura,
                    "texturas_vinculadas": texturas_vinculadas,
                    "url_preview": url_preview,
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
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as err:
            print(f"Aviso: No se pudo consultar {repo} ({err}). Continuando...")
        except Exception as err:
            print(f"Aviso inesperado al consultar {repo}: {err}")

    # 5. Reordenar para que Poly Haven (los detallados con PBR) aparezcan primero en Godot
    entidades.sort(key=lambda e: 0 if e.get("origen") == "polyhaven:cc0" else 1)

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
        print(f"Listo! +{nuevos_assets} modelos 3D y +{nuevas_texturas} texturas guardados en catalogo.json.")
    else:
        print("El catálogo ya está actualizado.")


if __name__ == "__main__":
    try:
        escanear_y_actualizar_assets()
    except Exception as exc:
        print(f"Error crítico en colector.py: {exc}")
