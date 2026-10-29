"use client";

import { useState } from "react";
import Link from "next/link";
import { BASE_FEE, MAX_PRICED_MONITORS, MODULE_FEES, SEASON_MONTHS, formatEuros, quote } from "@/lib/landing-pricing";

export function PricingCalculator() {
    const [monitors, setMonitors] = useState(20);
    const [reports, setReports] = useState(false);
    const [teamDailyReport, setTeamDailyReport] = useState(false);

    const q = quote({ monitors, reports, teamDailyReport });

    return (
        <div className="flex flex-col gap-5 rounded-2xl bg-slate-900 p-6 text-white sm:p-8">
            <h3 className="text-xl font-bold">Calcula tu cuota</h3>

            <label className="flex flex-col gap-3 text-sm text-slate-300">
                <span className="flex items-baseline justify-between">
                    <span>Monitores</span>
                    <span className="text-3xl font-extrabold tabular-nums text-white">{monitors}</span>
                </span>
                <input
                    type="range"
                    min={1}
                    max={MAX_PRICED_MONITORS}
                    value={monitors}
                    onChange={(e) => setMonitors(Number(e.target.value))}
                    className="h-7 w-full accent-indigo-300"
                />
            </label>

            <div className="flex flex-col">
                <label className="flex min-h-11 cursor-pointer items-center gap-3 text-sm">
                    <input type="checkbox" checked={reports} onChange={(e) => setReports(e.target.checked)} className="h-5 w-5 accent-indigo-300" />
                    Módulo Informes ({MODULE_FEES.reports} €)
                </label>
                <label className="flex min-h-11 cursor-pointer items-center gap-3 text-sm">
                    <input type="checkbox" checked={teamDailyReport} onChange={(e) => setTeamDailyReport(e.target.checked)} className="h-5 w-5 accent-indigo-300" />
                    Parte diario del equipo ({MODULE_FEES.teamDailyReport} €)
                </label>
            </div>

            <dl className="flex flex-col gap-2.5 border-t border-slate-700 pt-5 text-sm tabular-nums">
                <div className="flex justify-between text-slate-300"><dt>Cuota base</dt><dd>{formatEuros(BASE_FEE)}</dd></div>
                <div className="flex justify-between text-slate-300"><dt>Monitores</dt><dd>{formatEuros(q.monitors)}</dd></div>
                <div className="flex justify-between text-slate-300"><dt>Módulos</dt><dd>{formatEuros(q.modules)}</dd></div>
                <div className="flex items-baseline justify-between pt-1">
                    <dt className="font-semibold">Total al mes</dt>
                    <dd className="text-3xl font-extrabold tracking-tight">{formatEuros(q.monthly)}</dd>
                </div>
                <div className="flex justify-between text-slate-300"><dt>Temporada ({SEASON_MONTHS} meses)</dt><dd>{formatEuros(q.season)}</dd></div>
                <div className="flex justify-between gap-4 text-slate-300">
                    <dt>Primera temporada, con puesta en marcha</dt>
                    <dd className="font-semibold text-white">{formatEuros(q.firstSeason)}</dd>
                </div>
            </dl>

            <Link href="#contacto" className="rounded-[10px] bg-white px-5 py-3.5 text-center font-semibold text-slate-900 hover:bg-slate-100">
                Pedir presupuesto
            </Link>
            <p className="text-xs text-slate-400">Importes sin IVA. Precios de la temporada 2026-2027.</p>
        </div>
    );
}
