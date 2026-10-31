"use client";

import { useState } from "react";
import {
    DEFAULT_ACTIVE_MONTHS,
    EXTRAS,
    MAX_PRICED_MONITORS,
    MONTHS_PER_YEAR,
    PLANS,
    cheapestPlan,
    formatEuros,
    formatEurosCompact,
    getPlan,
    quote,
    type PlanId,
} from "@/lib/landing-pricing";
import { announcePlan } from "@/lib/landing-contact";

const MAX_EXTRA_MANAGERS = 20;

export function PricingCalculator() {
    const [planId, setPlanId] = useState<PlanId>("escuela");
    const [monitors, setMonitors] = useState(20);
    const [sharedSchedule, setSharedSchedule] = useState(false);
    const [reports, setReports] = useState(false);
    const [extraManagers, setExtraManagers] = useState(0);
    const [activeMonths, setActiveMonths] = useState(DEFAULT_ACTIVE_MONTHS);

    const plan = getPlan(planId);
    const q = quote({ planId, monitors, extraManagers, sharedSchedule, reports, activeMonths });
    // Solo se pasan los extras cuyos controles estan visibles para el plan actual.
    const cheapest = cheapestPlan(monitors, {
        sharedSchedule: planId === "basico" ? sharedSchedule : false,
        reports: planId === "basico" ? reports : false,
        extraManagers: planId !== "grande" ? extraManagers : 0,
    });
    const overLimit = monitors > MAX_PRICED_MONITORS;

    return (
        <div className="flex flex-col gap-5 rounded-2xl bg-slate-900 p-6 text-white sm:p-8">
            <h3 className="text-xl font-bold">Calcula tu cuota</h3>

            <fieldset className="flex flex-col gap-1 border-0 p-0">
                <legend className="mb-1 text-sm text-slate-300">Plan</legend>
                {PLANS.map((option) => (
                    <label key={option.id} className="flex min-h-11 cursor-pointer items-center gap-3 text-sm">
                        <input
                            type="radio"
                            name="calc-plan"
                            value={option.id}
                            checked={planId === option.id}
                            onChange={() => setPlanId(option.id)}
                            className="h-5 w-5 accent-indigo-300"
                        />
                        {option.name} · {formatEurosCompact(option.monthly)} al mes
                    </label>
                ))}
            </fieldset>

            <div className="flex flex-col gap-3">
                <div className="flex items-baseline justify-between">
                    <label htmlFor="calc-monitors" className="text-sm text-slate-300">
                        Número de monitores
                    </label>
                    <span className="text-3xl font-extrabold tabular-nums text-white">
                        {overLimit ? `Más de ${MAX_PRICED_MONITORS}` : monitors}
                    </span>
                </div>
                <input
                    id="calc-monitors"
                    type="range"
                    min={1}
                    max={MAX_PRICED_MONITORS + 1}
                    value={monitors}
                    aria-valuetext={overLimit ? `Más de ${MAX_PRICED_MONITORS}` : String(monitors)}
                    onChange={(e) => setMonitors(Number(e.target.value))}
                    className="h-7 w-full accent-indigo-300"
                />
            </div>

            <div className="flex flex-col gap-3">
                <div className="flex items-baseline justify-between">
                    <label htmlFor="calc-months" className="text-sm text-slate-300">
                        Meses activos al año
                    </label>
                    <span className="text-3xl font-extrabold tabular-nums text-white">{activeMonths}</span>
                </div>
                <input
                    id="calc-months"
                    type="range"
                    min={1}
                    max={MONTHS_PER_YEAR}
                    value={activeMonths}
                    aria-valuetext={`${activeMonths} ${activeMonths === 1 ? "mes" : "meses"}`}
                    onChange={(e) => setActiveMonths(Number(e.target.value))}
                    className="h-7 w-full accent-indigo-300"
                />
            </div>

            {cheapest !== null && (
                <div className="flex flex-col gap-2 rounded-[10px] bg-slate-800 p-4 text-sm">
                    <p>
                        Plan más barato para {monitors} monitores: {getPlan(cheapest).name}
                    </p>
                    {cheapest !== planId && (
                        <button
                            type="button"
                            onClick={() => setPlanId(cheapest)}
                            className="min-h-11 self-start rounded-[10px] border border-slate-500 px-4 py-2 font-semibold hover:bg-slate-700"
                        >
                            Usar {getPlan(cheapest).name}
                        </button>
                    )}
                </div>
            )}

            {planId === "grande" ? (
                <p className="text-sm text-slate-300">Responsables ilimitados incluidos en este plan.</p>
            ) : (
                <div className="flex flex-col gap-2">
                    <label htmlFor="calc-managers" className="text-sm text-slate-300">
                        Responsables adicionales ({formatEurosCompact(plan.extraManagerFee)} al mes cada uno)
                    </label>
                    <input
                        id="calc-managers"
                        type="number"
                        inputMode="numeric"
                        min={0}
                        max={MAX_EXTRA_MANAGERS}
                        step={1}
                        value={extraManagers}
                        onChange={(e) =>
                            setExtraManagers(Math.min(MAX_EXTRA_MANAGERS, Math.max(0, Math.floor(Number(e.target.value) || 0))))
                        }
                        className="min-h-11 w-full rounded-[10px] bg-white px-3 text-slate-900"
                    />
                </div>
            )}

            {planId === "basico" ? (
                <div className="flex flex-col">
                    <label className="flex min-h-11 cursor-pointer items-center gap-3 text-sm">
                        <input
                            type="checkbox"
                            checked={sharedSchedule}
                            onChange={(e) => setSharedSchedule(e.target.checked)}
                            className="h-5 w-5 accent-indigo-300"
                        />
                        Cuadrante compartido ({formatEurosCompact(EXTRAS.sharedSchedule)} al mes)
                    </label>
                    <label className="flex min-h-11 cursor-pointer items-center gap-3 text-sm">
                        <input
                            type="checkbox"
                            checked={reports}
                            onChange={(e) => setReports(e.target.checked)}
                            className="h-5 w-5 accent-indigo-300"
                        />
                        Informes ({formatEurosCompact(EXTRAS.reports)} al mes)
                    </label>
                </div>
            ) : (
                <p className="text-sm text-slate-300">Cuadrante compartido e Informes incluidos en este plan.</p>
            )}

            {q === null ? (
                <p className="text-sm text-slate-300">Más de {MAX_PRICED_MONITORS} monitores: a consultar.</p>
            ) : (
                <dl className="flex flex-col gap-2.5 border-t border-slate-700 pt-5 text-sm tabular-nums">
                    <div className="flex justify-between text-slate-300">
                        <dt>Cuota del plan</dt>
                        <dd>{formatEuros(q.base)}</dd>
                    </div>
                    {planId !== "grande" && (
                        <div className="flex justify-between text-slate-300">
                            <dt>
                                Monitores adicionales ({q.extraMonitors} x {formatEurosCompact(plan.extraMonitorFee)})
                            </dt>
                            <dd>{formatEuros(q.extraMonitorsCost)}</dd>
                        </div>
                    )}
                    {planId !== "grande" && (
                        <div className="flex justify-between text-slate-300">
                            <dt>
                                Responsables adicionales ({q.extraManagers} x {formatEurosCompact(plan.extraManagerFee)})
                            </dt>
                            <dd>{formatEuros(q.extraManagersCost)}</dd>
                        </div>
                    )}
                    <div className="flex justify-between text-slate-300">
                        <dt>Extras</dt>
                        <dd>{formatEuros(q.extras)}</dd>
                    </div>
                    <div className="flex items-baseline justify-between pt-1">
                        <dt className="font-semibold">Total al mes</dt>
                        <dd data-testid="total-monthly" aria-live="polite" className="text-3xl font-extrabold tracking-tight">
                            {formatEuros(q.monthly)}
                        </dd>
                    </div>
                    <div className="flex justify-between text-slate-300">
                        <dt>
                            Temporada ({q.activeMonths} {q.activeMonths === 1 ? "mes" : "meses"})
                        </dt>
                        <dd data-testid="total-season">{formatEuros(q.season)}</dd>
                    </div>
                    <div className="flex justify-between gap-4 text-slate-300">
                        <dt>Primera temporada, con puesta en marcha</dt>
                        <dd data-testid="total-first-season" className="font-semibold text-white">
                            {formatEuros(q.firstSeason)}
                        </dd>
                    </div>
                    {q.inactiveMonths > 0 && (
                        <div className="flex justify-between gap-4 text-slate-300">
                            <dt>
                                Mantenimiento opcional ({q.inactiveMonths} x {formatEurosCompact(plan.maintenanceFee)})
                            </dt>
                            <dd data-testid="total-maintenance">{formatEuros(q.maintenance)}</dd>
                        </div>
                    )}
                </dl>
            )}

            <a
                href="#contacto"
                onClick={() => announcePlan(overLimit ? "no-se" : planId)}
                className="min-h-11 inline-flex items-center justify-center rounded-[10px] bg-white px-5 py-3.5 text-center font-semibold text-slate-900 hover:bg-slate-100"
            >
                Quiero este plan
            </a>
            <p className="text-xs text-slate-400">
                Importes sin IVA. Precios de la temporada 2026-2027. Sin permanencia. Con mantenimiento en los meses inactivos no
                hay acceso, pero conservas todos tus datos y la siguiente temporada no pagas nueva puesta en marcha.
            </p>
        </div>
    );
}
