"""Limites de lineas del backend (ADR-0007).

- Maximo 300 lineas por fichero en `backend/src/` y `backend/routers/`.
- Maximo 120 lineas por clase `*UseCase` (caso de uso).
- Los ficheros que ya superaban 300 lineas figuran en `limites_excepciones.json` con su
  numero de lineas como techo. La lista solo puede encoger: un fichero de la lista que
  crece falla, un fichero nuevo que supera el limite falla y una entrada que ya no hace
  falta (fichero inexistente o dentro del limite) debe retirarse.
"""

import ast
import json
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
EXCEPCIONES_PATH = Path(__file__).resolve().parent / "limites_excepciones.json"
DIRECTORIOS_MEDIDOS = ("src", "routers")
MAX_LINEAS_FICHERO = 300
MAX_LINEAS_CASO_DE_USO = 120


def _ficheros_medidos() -> dict[str, Path]:
    ficheros: dict[str, Path] = {}
    for directorio in DIRECTORIOS_MEDIDOS:
        for ruta in sorted((BACKEND_DIR / directorio).rglob("*.py")):
            ficheros[ruta.relative_to(BACKEND_DIR).as_posix()] = ruta
    return ficheros


def _lineas(ruta: Path) -> int:
    return len(ruta.read_text(encoding="utf-8").splitlines())


def _excepciones() -> dict[str, int]:
    return json.loads(EXCEPCIONES_PATH.read_text(encoding="utf-8"))


def test_ficheros_no_superan_el_limite_ni_crecen_las_excepciones():
    excepciones = _excepciones()
    errores = []
    for nombre, ruta in _ficheros_medidos().items():
        lineas = _lineas(ruta)
        if nombre in excepciones:
            if lineas > excepciones[nombre]:
                errores.append(f"{nombre}: {lineas} lineas, supera el techo registrado de {excepciones[nombre]}")
        elif lineas > MAX_LINEAS_FICHERO:
            errores.append(f"{nombre}: {lineas} lineas, supera el limite de {MAX_LINEAS_FICHERO} (ADR-0007)")
    assert not errores, "Limites de lineas incumplidos:\n" + "\n".join(errores)


def test_la_lista_de_excepciones_solo_contiene_ficheros_que_superan_el_limite():
    ficheros = _ficheros_medidos()
    obsoletas = []
    for nombre in _excepciones():
        if nombre not in ficheros:
            obsoletas.append(f"{nombre}: el fichero ya no existe, retirarlo de la lista")
        elif _lineas(ficheros[nombre]) <= MAX_LINEAS_FICHERO:
            obsoletas.append(f"{nombre}: ya cumple {MAX_LINEAS_FICHERO} lineas, retirarlo de la lista")
    assert not obsoletas, "Excepciones obsoletas:\n" + "\n".join(obsoletas)


def test_los_casos_de_uso_no_superan_el_limite():
    errores = []
    for nombre, ruta in _ficheros_medidos().items():
        arbol = ast.parse(ruta.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ClassDef) and nodo.name.endswith("UseCase"):
                lineas = (nodo.end_lineno or nodo.lineno) - nodo.lineno + 1
                if lineas > MAX_LINEAS_CASO_DE_USO:
                    errores.append(f"{nombre}: {nodo.name} tiene {lineas} lineas (limite {MAX_LINEAS_CASO_DE_USO})")
    assert not errores, "Casos de uso demasiado largos:\n" + "\n".join(errores)
