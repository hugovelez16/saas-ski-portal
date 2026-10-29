"use client";

import { useState } from "react";

export const CONTACT_EMAIL = "hugo@vesotel.com";

const inputClass = "rounded-[10px] border border-slate-200 px-3 py-2.5 text-base font-normal focus:outline-none focus:ring-2 focus:ring-slate-400";

// Sin endpoint en el backend: el formulario abre el correo del usuario con los datos rellenados.
export function ContactForm() {
    const [accepted, setAccepted] = useState(false);

    const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        const data = new FormData(e.currentTarget);
        const subject = `Información para ${data.get("escuela") || "mi escuela"}`;
        const body = [
            `Nombre: ${data.get("nombre")}`,
            `Escuela: ${data.get("escuela")}`,
            `Número de monitores: ${data.get("monitores")}`,
            `Correo: ${data.get("email")}`,
            "",
            String(data.get("mensaje") || ""),
        ].join("\n");
        window.location.href = `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    };

    return (
        <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 rounded-2xl bg-white p-6 text-slate-900 sm:grid-cols-2 sm:p-7">
            <label className="flex flex-col gap-1.5 text-sm font-medium">
                Nombre
                <input name="nombre" type="text" autoComplete="name" required className={inputClass} />
            </label>
            <label className="flex flex-col gap-1.5 text-sm font-medium">
                Escuela
                <input name="escuela" type="text" autoComplete="organization" required className={inputClass} />
            </label>
            <label className="flex flex-col gap-1.5 text-sm font-medium">
                Número de monitores
                <input name="monitores" type="number" min={1} required className={inputClass} />
            </label>
            <label className="flex flex-col gap-1.5 text-sm font-medium">
                Correo electrónico
                <input name="email" type="email" autoComplete="email" required className={inputClass} />
            </label>
            <label className="flex flex-col gap-1.5 text-sm font-medium sm:col-span-2">
                Mensaje (opcional)
                <textarea name="mensaje" rows={3} className={`${inputClass} resize-y`} />
            </label>
            <label className="flex items-start gap-2.5 text-xs leading-relaxed text-slate-600 sm:col-span-2">
                <input type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)} required className="mt-0.5 h-4 w-4 flex-none" />
                Acepto la política de privacidad.
            </label>
            <button
                type="submit"
                disabled={!accepted}
                className="rounded-[10px] bg-slate-900 px-5 py-3.5 font-semibold text-white hover:bg-slate-800 disabled:opacity-50 sm:col-span-2"
            >
                Solicitar información
            </button>
        </form>
    );
}
