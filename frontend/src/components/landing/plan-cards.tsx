"use client";

import { Check } from "lucide-react";
import {
    DEFAULT_ACTIVE_MONTHS,
    MAX_PRICED_MONITORS,
    PLANS,
    SETUP_FEE,
    formatEurosCompact,
    type Plan,
    type PlanId,
} from "@/lib/landing-pricing";
import { announcePlan } from "@/lib/landing-contact";

const FEATURES: Record<PlanId, (plan: Plan) => string[]> = {
    basico: (plan) => [
        `Hasta ${plan.includedMonitors} monitores`,
        `Monitor adicional: ${formatEurosCompact(plan.extraMonitorFee)} al mes`,
        `${plan.managers} (adicional: ${formatEurosCompact(plan.extraManagerFee)} al mes)`,
        "Parte diario del responsable incluido",
        "Módulos aparte",
    ],
    escuela: (plan) => [
        `Hasta ${plan.includedMonitors} monitores`,
        `Monitor adicional: ${formatEurosCompact(plan.extraMonitorFee)} al mes`,
        `${plan.managers} (adicional: ${formatEurosCompact(plan.extraManagerFee)} al mes)`,
        "Parte diario del responsable incluido",
        "Cuadrante compartido e Informes incluidos",
    ],
    grande: (plan) => [
        `Hasta ${plan.includedMonitors} monitores incluidos`,
        `Más de ${MAX_PRICED_MONITORS} monitores: Pista Negra, a consultar`,
        plan.managers,
        "Parte diario del responsable incluido",
        "Cuadrante compartido e Informes incluidos",
    ],
};

const TRACK_DOT_CLASS: Record<PlanId, string> = {
    basico: "bg-green-600",
    escuela: "bg-blue-600",
    grande: "bg-red-600",
};

export function PlanCards() {
    return (
        <div>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                {PLANS.map((plan) => (
                    <article
                        key={plan.id}
                        className={`relative flex flex-col gap-5 rounded-2xl border p-6 ${
                            plan.recommended ? "border-2 border-indigo-600 shadow-lg" : "border-slate-200 bg-white"
                        }`}
                    >
                        {plan.recommended && (
                            <span className="absolute -top-3 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full bg-indigo-600 px-3 py-1 text-xs font-semibold text-white">
                                Recomendado
                            </span>
                        )}

                        <div className="flex items-center gap-2.5">
                            <span aria-hidden className={`h-3 w-3 rounded-full ${TRACK_DOT_CLASS[plan.id]}`} />
                            <h3 className="text-2xl font-bold">{plan.name}</h3>
                        </div>

                        <div>
                            <p className="text-3xl font-extrabold tabular-nums">
                                {formatEurosCompact(plan.monthly)}
                                <span className="text-sm font-normal text-slate-500">/mes</span>
                            </p>
                            <p className="text-sm text-slate-600">
                                Ejemplo, {DEFAULT_ACTIVE_MONTHS} meses: {formatEurosCompact(plan.monthly * DEFAULT_ACTIVE_MONTHS)}
                            </p>
                            <p className="text-sm text-slate-600">
                                Mantenimiento: {formatEurosCompact(plan.maintenanceFee)} por mes inactivo
                            </p>
                        </div>

                        <ul className="flex flex-col gap-3 text-base leading-normal">
                            {FEATURES[plan.id](plan).map((item) => (
                                <li key={item} className="flex gap-3">
                                    <Check aria-hidden className="mt-0.5 h-5 w-5 flex-none text-emerald-600" strokeWidth={2.4} />
                                    {item}
                                </li>
                            ))}
                        </ul>

                        <a
                            href="#contacto"
                            onClick={() => announcePlan(plan.id)}
                            aria-label={`Quiero este plan: ${plan.name}`}
                            className={`mt-auto min-h-11 inline-flex items-center justify-center rounded-[10px] px-5 py-3 font-semibold ${
                                plan.recommended
                                    ? "bg-slate-900 text-white hover:bg-slate-800"
                                    : "border border-slate-300 hover:bg-slate-50"
                            }`}
                        >
                            Quiero este plan
                        </a>
                    </article>
                ))}
            </div>

            <div className="mt-6 flex flex-col gap-2 text-sm text-slate-600">
                <p>
                    Todos los importes son sin IVA, por mes activo. Tú eliges qué meses activas la escuela y se factura por mes
                    natural completo. Sin permanencia.
                </p>
                <p>Puesta en marcha única: {formatEurosCompact(SETUP_FEE)} en todos los planes.</p>
                <p>
                    Mantenimiento fuera de temporada: en los meses inactivos no hay acceso, pero la escuela conserva todos sus datos y
                    al volver no paga nueva puesta en marcha. Además, conserva su precio la temporada siguiente.
                </p>
                <p>Informes a medida: bajo consulta.</p>
            </div>
        </div>
    );
}
