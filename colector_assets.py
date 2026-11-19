import os
import json
from datetime import datetime

PATH_RAIZ = r"C:\Proyectos\GodotPro-Catalog-Index"
PATH_JSON = os.path.join(PATH_RAIZ, "catalogo.json")
PATH_ASSETS = os.path.join(PATH_RAIZ, "assets")
URL_BASE_GITHUB = "https://githubusercontent.com"


def inicializar_o_cargar_catalogo():
    if os.path.exists(PATH_JSON):
        try:
            with open(PATH_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "entities" in data:
                    return data
        except Exception:
            pass

    return {
        "catalog_version": datetime.now().strftime("%Y.%m.%d"),
        "source_repo": "https://github.com",
        "entities": [],
    }


def clasificar_asset(raiz, id_asset):
    ruta_baja = raiz.lower()
    if any(k in ruta_baja or k in id_asset for k in ("silla", "mesa", "chimenea", "mueble", "cama", "sofa")):
        return "Mobiliario", "Interiores"
    if any(k in ruta_baja or k in id_asset for k in ("flora", "arbol", "cesped", "planta", "arbusto")):
        return "Naturaleza", "Flora"
    if any(k in ruta_baja or k in id_asset for k in ("fauna", "pj", "gato", "mascota", "animal", "perro")):
        return "Vivos", "Agentes"
    if any(k in ruta_baja or k in id_asset for k in ("carro", "carrito", "carroza", "vehiculo", "auto")):
        return "Vehiculos", "Transporte"
    return "Estructuras", "Construccion"


def escanear_y_actualizar_assets():
    print("Supermaquina Colector: Iniciando escaneo de bloques 3D...")
    catalogo = inicializar_o_cargar_catalogo()
    entidades_existentes = {e["id"]: e for e in catalogo.get("entities", [])}

    if not os.path.exists(PATH_ASSETS):
        os.makedirs(PATH_ASSETS)
        print(f"Supermaquina Colector: Carpeta creada en {PATH_ASSETS}")

    nuevos_assets = 0

    for raiz, _, archivos in os.walk(PATH_ASSETS):
        for archivo in archivos:
            if archivo.endswith((".tscn", ".scn", ".res", ".glb")):
                nombre_base, _ = os.path.splitext(archivo)
                id_asset = nombre_base.lower().replace(" ", "_")

                if id_asset in entidades_existentes:
                    continue

                categoria, subcategoria = clasificar_asset(raiz, id_asset)
                es_muro = any(k in id_asset for k in ("muro", "pared", "tapiz"))
                requiere_perforacion = any(k in id_asset for k in ("ventana", "puerta", "escalera"))

                celdas_xyz = [1, 3, 0.2]
                if not es_muro:
                    celdas_xyz = [1, 1, 1]

                ruta_relativa = os.path.relpath(os.path.join(raiz, archivo), PATH_ASSETS).replace(os.sep, "/")
                url_descarga = f"{URL_BASE_GITHUB}/{ruta_relativa}"

                nueva_entidad = {
                    "id": id_asset,
                    "categoria": categoria,
                    "subcategoria": subcategoria,
                    "nombre_visual": id_asset.replace("_", " ").title(),
                    "archivo": archivo,
                    "url_descarga": url_descarga,
                    "ruta_cache_godot": f"res://catalogo_cache/{ruta_relativa}",
                    "propiedades_rejilla": {
                        "tamano_celdas_xyz": celdas_xyz,
                        "origen_pivote": [0.5, 0, 0.5],
                        "magnetico": True,
                    },
                    "comportamiento_motor": {
                        "es_muro_elastico": es_muro,
                        "perforacion_automatica": requiere_perforacion,
                        "tipo_colision": "Muro_CSG" if (es_muro or requiere_perforacion) else "Estatica_Solida",
                    },
                }

                catalogo["entities"].append(nueva_entidad)
                nuevos_assets += 1
                print(f"-> Indexado: {id_asset} [{categoria} / {subcategoria}]")

    if nuevos_assets > 0:
        catalogo["catalog_version"] = datetime.now().strftime("%Y.%m.%d")
        with open(PATH_JSON, "w", encoding="utf-8") as f:
            json.dump(catalogo, f, indent=2, ensure_ascii=False)
        print(f"Listo! {nuevos_assets} bloques nuevos guardados en catalogo.json.")
    else:
        print("El catalogo esta al dia. Mete archivos (.tscn o .glb) en la carpeta 'assets' para indexarlos.")


if __name__ == "__main__":
    escanear_y_actualizar_assets()
