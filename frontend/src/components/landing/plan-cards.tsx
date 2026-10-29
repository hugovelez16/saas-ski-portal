"use client";

import { Check } from "lucide-react";
import {
    EXTRAS,
    MAX_PRICED_MONITORS,
    OFF_SEASON_FEE,
    PLANS,
    SEASON_MONTHS,
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
        `Cuadrante compartido: ${formatEurosCompact(EXTRAS.sharedSchedule)} al mes (aparte)`,
        `Informes: ${formatEurosCompact(EXTRAS.reports)} al mes (aparte)`,
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
        `Más de ${MAX_PRICED_MONITORS} monitores: a consultar`,
        plan.managers,
        "Parte diario del responsable incluido",
        "Cuadrante compartido e Informes incluidos",
    ],
};

export function PlanCards() {
    return (
        <div>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                {PLANS.map((plan) => (
                    <article
                        key={plan.id}
                        className={`flex flex-col gap-5 rounded-2xl border p-6 ${
                            plan.recommended ? "border-2 border-indigo-600 shadow-lg" : "border-slate-200 bg-white"
                        }`}
                    >
                        {plan.recommended && (
                            <span className="self-start rounded-full bg-indigo-600 px-3 py-1 text-xs font-semibold text-white">
                                Recomendado
                            </span>
                        )}

                        <h3 className="text-2xl font-bold">{plan.name}</h3>

                        <div>
                            <p className="text-3xl font-extrabold tabular-nums">
                                {formatEurosCompact(plan.monthly)}
                                <span className="text-sm font-normal text-slate-500">/mes</span>
                            </p>
                            <p className="text-sm text-slate-600">
                                Temporada (5 meses): {formatEurosCompact(plan.monthly * SEASON_MONTHS)}
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
                <p>Todos los importes son sin IVA, por mes de temporada (diciembre a abril, 5 meses). Sin permanencia.</p>
                <p>Puesta en marcha única: {formatEurosCompact(SETUP_FEE)} en todos los planes.</p>
                <p>
                    Mantenimiento fuera de temporada: {formatEurosCompact(OFF_SEASON_FEE)} al mes (mayo a noviembre). Si la escuela se
                    mantiene hasta la temporada siguiente, no paga nueva puesta en marcha y conserva todos sus datos.
                </p>
                <p>Informes a medida: bajo consulta.</p>
            </div>
        </div>
    );
}
