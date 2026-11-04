import {
    buildMailtoUrl,
    buildWhatsAppUrl,
    MONITOR_CONTACT_MESSAGE,
    MONITOR_WAITLIST_MESSAGE,
    MONITOR_WAITLIST_SUBJECT,
} from "@/lib/landing-contact";

const container = "mx-auto max-w-[1200px] px-6";
const sectionTitle = "text-[clamp(28px,3.4vw,40px)] font-extrabold leading-[1.1] tracking-tight";
const primaryButton =
    "inline-flex min-h-11 items-center justify-center rounded-full bg-slate-900 px-6 text-sm font-semibold text-white transition-colors hover:bg-slate-700";
const secondaryButton =
    "inline-flex min-h-11 items-center justify-center rounded-full border border-slate-300 bg-white px-6 text-sm font-semibold text-slate-900 transition-colors hover:border-slate-500";

export function MonitorSection() {
    return (
        <section id="monitor" className={`${container} scroll-mt-24 py-14`}>
            <div className="flex flex-col gap-7 rounded-[20px] border border-slate-200 bg-white p-6 sm:p-10">
                <div className="flex flex-col gap-4">
                    <p className="text-sm font-semibold uppercase tracking-wider text-slate-500">¿Eres monitor?</p>
                    <h2 className={sectionTitle}>Una versión gratuita para monitores, próximamente</h2>
                    <p className="max-w-[640px] text-base leading-relaxed text-slate-600">
                        Estamos preparando una versión para monitores. Todavía no está disponible y no hay registro
                        abierto. Si quieres que te tengamos en cuenta, apúntate a la lista de espera o escríbenos.
                    </p>
                </div>
                <div className="flex flex-wrap gap-3">
                    <a
                        href={buildMailtoUrl(MONITOR_WAITLIST_SUBJECT, MONITOR_WAITLIST_MESSAGE)}
                        className={primaryButton}
                    >
                        Apúntame a la lista de espera
                    </a>
                    <a
                        href={buildWhatsAppUrl(MONITOR_CONTACT_MESSAGE)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={secondaryButton}
                    >
                        Escríbeme sin compromiso
                    </a>
                </div>
                <div className="flex flex-col gap-2 border-t border-slate-200 pt-6">
                    <h3 className="text-lg font-bold text-slate-900">Recomiéndaselo a tu escuela</h3>
                    <p className="text-base leading-relaxed text-slate-600">
                        Si tu escuela todavía gestiona las clases con hojas de cálculo, enséñale esta página.
                    </p>
                    <a href="#precios" className="inline-flex min-h-11 items-center text-sm font-semibold text-slate-900 underline underline-offset-4">
                        Ver planes para escuelas
                    </a>
                </div>
            </div>
        </section>
    );
}
