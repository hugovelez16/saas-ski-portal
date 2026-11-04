"""Paridad de calculo entre `crud.calculate_dynamic_work_log` (referencia) y el motor de `src/` (PR-18.0).

La rejilla combina:
- Unidad y duracion: hours con duration_hours, hours con cruce de medianoche (22:00-02:00), hours en el
  mismo dia (09:15-17:45), days de un solo dia, days de varios dias y fixed. Siempre se pasan start_date
  y end_date, tambien para hours y fixed.
- is_gross verdadero y falso.
- 0, 1 o 3 impuestos de empresa.
- Modificadores (MODIFIERS): override de impuestos del miembro ausente, None, None por clave, igual a la
  empresa, distinto de la empresa y solo en el miembro, combinados con extras fijos y por unidad, con la
  opcion activada y desactivada en extra_data["opciones"]. Los overrides "igual" y "distinto" se omiten
  con 0 impuestos de empresa porque no aportan nada.
- Importe manual (`amount` / `net_amount`): crud devuelve bruto = neto = importe, duracion 0 y no aplica
  impuestos (tax_applied = {}).

Entradas: 6 formas x 2 is_gross x (4 + 7 + 7) modificadores = 216 de rejilla, mas 4 manuales = 220.

Tolerancia: abs 0.01 en net_amount, gross_amount y duration. tax_applied se compara por clave y como float.
La tolerancia no se relaja: las entradas que no cumplen quedan fallando y se reportan.

Divergencias de redondeo entre ambos motores (documentadas, no ocultadas):
- crud trabaja en float sin redondear; src redondea a 0.01 el importe base, los extras, el bruto y el neto.
  La rejilla usa tarifas de 2 decimales, duraciones en multiplos de 0.25 h y extras por unidad de 1.50 y
  2.00 con duraciones de horas o dias enteros, de forma que los productos base y extra tienen como mucho
  2 decimales. Las tasas tienen hasta 4 decimales (0.0648); el redondeo de src en el bruto y en el neto
  aporta como mucho 0.005 por paso, dentro de la tolerancia. Esto es un analisis previo: se confirmara al
  ejecutar la rejilla con el motor de src ya adaptado.
- WorkDuration.calculate (src) redondea la duracion en horas a 2 decimales; crud no. Las horas de la rejilla
  son exactas en 2 decimales (minutos 00, 15, 30 o 45). Un intervalo como 10:00-10:20 (0.333 h) divergeria
  en el importe; no se incluye en la rejilla.
- Importe manual 12.345: crud devuelve 12.345 y src 12.35 (ROUND_HALF_UP). Diferencia 0.005, dentro de
  la tolerancia.
"""

import copy
from dataclasses import dataclass, replace
from datetime import date, time, timedelta
from decimal import Decimal
from typing import Any, Optional

import crud
import pytest
from domain.services.work_log_calculation_service import WorkLogCalculationService
from domain.value_objects.rate_definition import RateDefinition
from domain.value_objects.tax_configuration import TaxConfiguration
from domain.value_objects.work_duration import WorkDuration, WorkUnit

TOLERANCIA = 0.01
MINIMO_ENTRADAS = 60

D0 = date(2026, 1, 10)

# Forma de la jornada: (unidad, campos propios del log, duracion esperada en horas/dias/1 para fixed).
FORMAS: dict[str, tuple[str, dict[str, Any], float]] = {
    "hours-duration_hours": ("hours", {"duration_hours": 4.5}, 4.5),
    "hours-cruce-medianoche": ("hours", {"start_time": time(22, 0), "end_time": time(2, 0)}, 4.0),
    "hours-mismo-dia": ("hours", {"start_time": time(9, 15), "end_time": time(17, 45)}, 8.5),
    "days-un-dia": ("days", {}, 1.0),
    "days-varios": ("days", {"end_date": D0 + timedelta(days=4)}, 5.0),
    "fixed": ("fixed", {}, 1.0),
}

TARIFA_BASE = {"hours": 12.5, "days": 80.0, "fixed": 150.0}

EXTRAS_DEF = {
    "dieta": {"value": 10.0, "per_unit": False},
    "nocturno": {"value": 1.5, "per_unit": True},
}

# Variante de extras: (extras definidos en la tarifa del miembro, opciones en extra_data).
EXTRAS_VARIANTES: dict[str, tuple[dict[str, Any], dict[str, bool]]] = {
    "sin_extras": ({}, {}),
    "fijo_on": (EXTRAS_DEF, {"dieta": True, "nocturno": False}),
    "unidad_on": (EXTRAS_DEF, {"dieta": False, "nocturno": True}),
    "ambos_on": (EXTRAS_DEF, {"dieta": True, "nocturno": True}),
    "ambos_off": (EXTRAS_DEF, {}),
}

# Impuestos de empresa por numero de impuestos: 0, 1 y 3. Nombres libres.
IMPUESTOS_EMPRESA: dict[int, dict[str, float]] = {
    0: {},
    1: {"IRPF": 0.15},
    3: {"IRPF": 0.15, "Seguridad Social": 0.0648, "Otros impuestos": 0.02},
}

DISTINTO_RATE = 0.19
SOLO_MIEMBRO = {"Retencion extra": 0.05}

# (override de impuestos del miembro, variante de extras)
MODIFICADORES: list[tuple[str, str]] = [
    ("ausente", "sin_extras"),  # tax_overrides no existe en la tarifa
    ("null", "fijo_on"),  # tax_overrides = None
    ("valor_none", "unidad_on"),  # tax_overrides = {"IRPF": None}: None no sustituye
    ("igual", "ambos_on"),  # mismos valores que la empresa
    ("distinto", "ambos_off"),  # valores distintos a los de la empresa
    ("solo_miembro", "ambos_on"),  # clave que la empresa no define
    ("distinto", "unidad_on"),
]


@dataclass(frozen=True)
class Case:
    id: str
    unidad: str
    duracion: float
    log_data: dict[str, Any]
    user_rate: dict[str, Any]
    company_tax_config: dict[str, float]

    @property
    def manual(self) -> bool:
        return _importe_manual(self.log_data) is not None


def _importe_manual(log_data: dict[str, Any]) -> Optional[float]:
    """Mismo criterio que crud: `amount` tiene prioridad sobre `net_amount`."""
    valor = log_data.get("amount")
    if valor is None:
        valor = log_data.get("net_amount")
    return valor


def _override(kind: str, empresa: dict[str, float]) -> Optional[dict[str, Any]]:
    if kind == "null":
        return None
    if kind == "valor_none":
        return {"IRPF": None}
    if kind == "igual":
        return dict(empresa)
    if kind == "distinto":
        return {nombre: DISTINTO_RATE for nombre in empresa}
    if kind == "solo_miembro":
        return dict(SOLO_MIEMBRO)
    raise ValueError(f"override desconocido: {kind}")


def _caso(forma_id: str, is_gross: bool, n_impuestos: int, override_kind: str, extras_kind: str) -> Case:
    unidad, campos_forma, duracion = FORMAS[forma_id]
    empresa = IMPUESTOS_EMPRESA[n_impuestos]
    extras_def, opciones = EXTRAS_VARIANTES[extras_kind]

    user_rate: dict[str, Any] = {
        "base_rate": TARIFA_BASE[unidad],
        "is_gross": is_gross,
        "extras": copy.deepcopy(extras_def),
    }
    if override_kind != "ausente":
        user_rate["tax_overrides"] = _override(override_kind, empresa)

    log_data: dict[str, Any] = {
        "start_date": D0,
        "end_date": D0,
        **copy.deepcopy(campos_forma),
        "extra_data": {"opciones": dict(opciones)},
    }
    bruto = "bruto" if is_gross else "neto"
    return Case(
        id=f"{forma_id}|{bruto}|{n_impuestos}imp|{override_kind}|{extras_kind}",
        unidad=unidad,
        duracion=duracion,
        log_data=log_data,
        user_rate=user_rate,
        company_tax_config=dict(empresa),
    )


def _rejilla() -> list[Case]:
    casos: list[Case] = []
    for forma_id in FORMAS:
        for is_gross in (False, True):
            for n_impuestos in IMPUESTOS_EMPRESA:
                for override_kind, extras_kind in MODIFICADORES:
                    if n_impuestos == 0 and override_kind in {"igual", "distinto"}:
                        continue
                    casos.append(_caso(forma_id, is_gross, n_impuestos, override_kind, extras_kind))
    return casos


def _manuales() -> list[Case]:
    # Importe manual: el resto de la configuracion se fija para comprobar que no se aplica ningun impuesto.
    especificaciones = [
        ("hours-cruce-medianoche", True, 3, "solo_miembro", "ambos_on", "amount", 250.0),
        ("days-varios", False, 1, "null", "fijo_on", "net_amount", 99.99),
        ("fixed", False, 0, "ausente", "sin_extras", "amount", 0.0),
        # 12.345 se redondea a 12.35 en src (HALF_UP); diferencia 0.005, dentro de la tolerancia.
        ("hours-duration_hours", True, 3, "igual", "ambos_on", "amount", 12.345),
    ]
    casos = []
    for forma_id, is_gross, n_impuestos, override_kind, extras_kind, clave, importe in especificaciones:
        base = _caso(forma_id, is_gross, n_impuestos, override_kind, extras_kind)
        casos.append(
            replace(
                base,
                id=f"manual|{forma_id}|{n_impuestos}imp|{clave}={importe}",
                log_data={**base.log_data, clave: importe},
            )
        )
    return casos


GRID: list[Case] = _rejilla() + _manuales()
GRID_IDS: list[str] = [caso.id for caso in GRID]


def run_crud(case: Case) -> dict[str, Any]:
    """Ejecuta la referencia `crud.calculate_dynamic_work_log` y devuelve los campos comparados."""
    snap = crud.calculate_dynamic_work_log(
        dict(case.log_data),
        {"unit": case.unidad, "label": case.unidad, "fields": []},
        dict(case.user_rate),
        dict(case.company_tax_config),
    )
    # El snapshot de un importe manual no incluye tax_applied: no se aplican impuestos.
    return {
        "net_amount": snap["net_amount"],
        "gross_amount": snap["gross_amount"],
        "duration": snap["duration"],
        "tax_applied": dict(snap["snapshot"].get("tax_applied", {})),
    }


def run_src(case: Case) -> dict[str, Any]:
    """Ejecuta el motor de `src/` con los mismos datos de entrada que `run_crud`.

    `tax_applied` es None si CalculationSnapshot no expone ese atributo.
    """
    log = case.log_data
    rate = RateDefinition.from_dict(case.user_rate)
    tax_config = TaxConfiguration.from_dict(
        company_tax_config=case.company_tax_config,
        user_tax_overrides=rate.tax_overrides,
    )
    duration = WorkDuration.calculate(
        unit=WorkUnit(case.unidad),
        duration_hours=log.get("duration_hours"),
        start_time=log.get("start_time"),
        end_time=log.get("end_time"),
        start_date=log.get("start_date"),
        end_date=log.get("end_date"),
    )
    importe_manual = _importe_manual(log)
    snap = WorkLogCalculationService.calculate(
        duration=duration,
        rate_definition=rate,
        tax_configuration=tax_config,
        options=log.get("extra_data", {}).get("opciones", {}),
        manual_net_amount=None if importe_manual is None else Decimal(str(importe_manual)),
    )
    tax_applied = getattr(snap, "tax_applied", None)
    return {
        "net_amount": float(snap.net_amount),
        "gross_amount": float(snap.gross_amount),
        "duration": float(snap.duration),
        "tax_applied": None if tax_applied is None else {k: float(v) for k, v in tax_applied.items()},
    }


def esperado(case: Case) -> dict[str, Any]:
    """Oraculo independiente: calcula los importes con Decimal exacto a partir de la especificacion del caso."""
    if case.manual:
        importe = float(_importe_manual(case.log_data))
        return {"net_amount": importe, "gross_amount": importe, "duration": 0.0, "tax_applied": {}}

    duracion = Decimal(str(case.duracion))
    tarifa = Decimal(str(case.user_rate["base_rate"]))
    base = tarifa if case.unidad == "fixed" else duracion * tarifa

    opciones = case.log_data["extra_data"]["opciones"]
    extras = Decimal("0")
    for nombre, extra in case.user_rate.get("extras", {}).items():
        if opciones.get(nombre) is True:
            valor = Decimal(str(extra["value"]))
            extras += valor * duracion if extra["per_unit"] else valor

    overrides = {k: v for k, v in (case.user_rate.get("tax_overrides") or {}).items() if v is not None}
    impuestos = {k: Decimal(str(v)) for k, v in {**case.company_tax_config, **overrides}.items()}
    tasa = sum(impuestos.values(), Decimal("0"))

    if case.user_rate["is_gross"]:
        bruto = base + extras
        neto = bruto * (1 - tasa)
    else:
        neto = base + extras
        bruto = neto / (1 - tasa) if tasa < 1 else neto

    return {
        "net_amount": float(neto),
        "gross_amount": float(bruto),
        "duration": float(duracion),
        "tax_applied": {k: float(v) for k, v in impuestos.items()},
    }


def test_rejilla_tiene_al_menos_60_entradas():
    assert len(GRID) >= MINIMO_ENTRADAS
    assert len(set(GRID_IDS)) == len(GRID_IDS), "los ids de la rejilla deben ser unicos"


@pytest.mark.parametrize("case", GRID, ids=GRID_IDS)
def test_crud_coincide_con_oraculo(case: Case):
    """Comprueba la referencia por si sola: crud debe coincidir con el calculo independiente."""
    obtenido = run_crud(case)
    previsto = esperado(case)
    for campo in ("net_amount", "gross_amount", "duration"):
        assert obtenido[campo] == pytest.approx(previsto[campo], abs=TOLERANCIA), campo
    assert set(obtenido["tax_applied"]) == set(previsto["tax_applied"])
    for nombre, tasa in previsto["tax_applied"].items():
        assert obtenido["tax_applied"][nombre] == pytest.approx(tasa), nombre


@pytest.mark.parametrize("case", GRID, ids=GRID_IDS)
def test_importes_y_duracion_coinciden(case: Case):
    referencia = run_crud(case)
    motor = run_src(case)
    for campo in ("net_amount", "gross_amount", "duration"):
        assert motor[campo] == pytest.approx(referencia[campo], abs=TOLERANCIA), (
            f"{campo}: src={motor[campo]} crud={referencia[campo]}"
        )


@pytest.mark.parametrize("case", GRID, ids=GRID_IDS)
def test_tax_applied_coincide(case: Case):
    referencia = run_crud(case)["tax_applied"]
    motor = run_src(case)["tax_applied"]
    assert motor is not None, "CalculationSnapshot no expone el atributo tax_applied"
    assert set(motor) == set(referencia), f"claves: src={sorted(motor)} crud={sorted(referencia)}"
    for nombre, tasa in referencia.items():
        assert motor[nombre] == pytest.approx(tasa), f"tasa de '{nombre}': src={motor[nombre]} crud={tasa}"
