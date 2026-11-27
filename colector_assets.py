# ... existing code ...
PATH_RAIZ = r"C:\Proyectos\GodotPro-Catalog-Index"
PATH_JSON = os.path.join(PATH_RAIZ, "catalogo.json")
PATH_ASSETS = os.path.join(PATH_RAIZ, "assets")
PATH_PERSONAJES = os.path.join(PATH_ASSETS, "personajes")
PATH_TEXTURAS = os.path.join(PATH_ASSETS, "texturas")
URL_BASE_GITHUB = "https://raw.githubusercontent.com/Vulgarcin/GodotPro-Catalog-Index/main"

EXTENSIONES_3D = (".tscn", ".scn", ".res", ".glb", ".gltf", ".obj", ".fbx")
EXTENSIONES_TEXTURA = (".png", ".jpg", ".jpeg", ".webp")


def inicializar_o_cargar_catalogo():
    if os.path.exists(PATH_JSON):
        try:
            with open(PATH_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "entities" in data:
                    data.setdefault("textures", [])
                    return data
        except Exception:
            pass

    return {
        "catalog_version": datetime.now().strftime("%Y.%m.%d"),
        "source_repo": "https://github.com/Vulgarcin/GodotPro-Catalog-Index",
        "entities": [],
        "textures": [],
    }


def clasificar_asset(raiz, id_asset):
    ruta_baja = raiz.lower()
    if any(k in ruta_baja or k in id_asset for k in ("personaje", "pj", "gato", "mascota", "animal", "perro", "fauna")):
        return "Personajes", "Agentes"
    if any(k in ruta_baja or k in id_asset for k in ("silla", "mesa", "chimenea", "mueble", "cama", "sofa", "mobiliario", "furniture")):
        return "Mobiliario", "Interiores"
    if any(k in ruta_baja or k in id_asset for k in ("flora", "arbol", "cesped", "planta", "arbusto")):
        return "Naturaleza", "Flora"
    if any(k in ruta_baja or k in id_asset for k in ("carro", "carrito", "carroza", "vehiculo", "auto")):
        return "Vehiculos", "Transporte"
    return "Estructuras", "Construccion"


def escanear_y_actualizar_assets():
    print("Supermaquina Colector: Iniciando escaneo de bloques 3D y texturas...")
    catalogo = inicializar_o_cargar_catalogo()
    entidades = catalogo.get("entities", [])
    texturas = catalogo.get("textures", [])

    # Evita duplicados tanto por id como por ruta_cache_godot
    ids_existentes = {e.get("id") for e in entidades if e.get("id")}
    rutas_3d_existentes = {e.get("ruta_cache_godot") for e in entidades if e.get("ruta_cache_godot")}
    rutas_tex_existentes = {t.get("ruta_cache_godot") for t in texturas if t.get("ruta_cache_godot")}

    for carpeta in (PATH_ASSETS, PATH_PERSONAJES, PATH_TEXTURAS):
        if not os.path.exists(carpeta):
            os.makedirs(carpeta)
            print(f"Supermaquina Colector: Carpeta creada en {carpeta}")

    nuevos_assets = 0
    nuevas_texturas = 0

    for raiz, _, archivos in os.walk(PATH_RAIZ):
        # Evita escanear carpetas ocultas de git o caché interna si existiera
        if ".git" in raiz.split(os.sep):
            continue

        for archivo in archivos:
            archivo_bajo = archivo.lower()
            ruta_completa = os.path.join(raiz, archivo)
            ruta_relativa = os.path.relpath(ruta_completa, PATH_RAIZ).replace(os.sep, "/")

            if archivo_bajo.endswith(EXTENSIONES_3D):
                nombre_base, _ = os.path.splitext(archivo)
                id_base = nombre_base.lower().replace(" ", "_")
                ruta_cache = f"res://catalogo_cache/{ruta_relativa}"

                if ruta_cache in rutas_3d_existentes:
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
                url_descarga = f"{URL_BASE_GITHUB}/{ruta_relativa}"

                nueva_entidad = {
                    "id": id_asset,
                    "categoria": categoria,
                    "subcategoria": subcategoria,
                    "nombre_visual": id_asset.replace("_", " ").title(),
                    "archivo": archivo,
                    "url_descarga": url_descarga,
                    "ruta_cache_godot": ruta_cache,
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
                }

                entidades.append(nueva_entidad)
                ids_existentes.add(id_asset)
                rutas_3d_existentes.add(ruta_cache)
                nuevos_assets += 1
                print(f"-> Indexado 3D: {id_asset} [{categoria} / {subcategoria}]")

            elif archivo_bajo.endswith(EXTENSIONES_TEXTURA):
                ruta_cache_tex = f"res://catalogo_cache/{ruta_relativa}"
                if ruta_cache_tex in rutas_tex_existentes:
                    continue

                nombre_base, _ = os.path.splitext(archivo)
                id_tex = nombre_base.lower().replace(" ", "_")

                nueva_textura = {
                    "id": id_tex,
                    "archivo": archivo,
                    "url_descarga": f"{URL_BASE_GITHUB}/{ruta_relativa}",
                    "ruta_cache_godot": ruta_cache_tex,
                }

                texturas.append(nueva_textura)
                rutas_tex_existentes.add(ruta_cache_tex)
                nuevas_texturas += 1
                print(f"-> Indexada textura: {archivo}")

    catalogo["entities"] = entidades
    catalogo["textures"] = texturas

    if nuevos_assets > 0 or nuevas_texturas > 0:
        catalogo["catalog_version"] = datetime.now().strftime("%Y.%m.%d")
        with open(PATH_JSON, "w", encoding="utf-8") as f:
            json.dump(catalogo, f, indent=2, ensure_ascii=False)
        print(f"Listo! {nuevos_assets} bloques 3D y {nuevas_texturas} texturas nuevas guardados en catalogo.json.")
    else:
        print("El catalogo esta al dia. Mete modelos 3D o texturas para indexarlos.")


if __name__ == "__main__":
    escanear_y_actualizar_assets()
