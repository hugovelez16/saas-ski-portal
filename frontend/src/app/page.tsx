import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { Check } from "lucide-react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { ContactForm } from "@/components/landing/contact-form";
import { MonitorSection } from "@/components/landing/monitor-section";
import { PlanCards } from "@/components/landing/plan-cards";
import { PricingCalculator } from "@/components/landing/pricing-calculator";
import { SessionRedirect } from "@/components/landing/session-redirect";
import { EXTRAS, PLANS, SETUP_FEE, formatEurosCompact, getPlan } from "@/lib/landing-pricing";

export const metadata: Metadata = {
    title: "Vesotel Jornadas: gestión de clases y monitores para escuelas de esquí",
    description: "Gestión de clases, horas e importes para escuelas de esquí de España. Planes desde 129 € al mes, sin permanencia.",
};

const container = "mx-auto max-w-[1200px] px-6";
const eyebrow = "text-[13px] font-semibold uppercase tracking-[0.08em] text-slate-500";
const sectionTitle = "text-[clamp(28px,3.4vw,40px)] font-extrabold leading-[1.1] tracking-tight";
const lead = "text-[17px] leading-relaxed text-slate-500";
const screenshotFrame = "overflow-hidden rounded-[14px] border border-slate-200 bg-white shadow-[0_16px_40px_rgba(15,23,42,0.10)]";

const comparison = [
    ["Asignar una clase", "Anotarla y avisar al monitor", "Se registra en la app, una a una o para varios monitores a la vez"],
    ["Consulta del monitor", "Manual, uno a uno", "La ve en cuanto entra en la app"],
    ["Total por monitor", "Sumar horas y hacer cuentas al cierre", "Calculado solo, por monitor y por periodo"],
    ["Suplementos y retenciones", "Se calculan a mano", "Se configuran y se aplican con su desglose: Seguridad Social, IRPF y otros"],
];

const pains = [
    "Apuntas las clases en una hoja, en el móvil o en papel, y avisas a cada monitor uno a uno.",
    "Al cerrar el mes sumas horas, días y suplementos por monitor, y repasas las retenciones a mano.",
    "Cuando un monitor pregunta por qué cobra lo que cobra, toca buscar clase por clase.",
];

const steps = [
    "Reunión corta para ver cómo organizáis las clases y cómo se paga cada una.",
    "Alta de la escuela, del responsable y de los monitores.",
    "Configuramos contigo tipos de clase, tarifas, suplementos y retenciones.",
    "Formación breve al responsable y acceso para los monitores.",
    "Un periodo en paralelo con tu método actual para comprobar que los totales coinciden.",
];

const faqs = [
    {
        q: "¿Quién puede ver los datos de la escuela?",
        a: "Cada escuela tiene sus datos separados de las demás. Dentro de la escuela, el responsable gestiona clases y tarifas, y cada monitor solo ve lo suyo.",
    },
    {
        q: "¿Los monitores tienen que instalar algo?",
        a: "No. Se accede desde el navegador del móvil o del ordenador con el usuario personal de cada monitor.",
    },
    {
        q: "¿Puedo cambiar una tarifa a mitad de temporada?",
        a: "Sí. Cada clase guarda la tarifa con la que se registró y la mantiene aunque la edites. La nueva tarifa solo se aplica a las clases que registres después, o si cambias el tipo de clase.",
    },
    {
        q: "¿Qué pasa con mis datos fuera de temporada?",
        a: `En los meses que no activas la escuela puedes pagar el mantenimiento: ${PLANS.map((plan) => `${formatEurosCompact(plan.maintenanceFee)} al mes en ${plan.name}`).join(", ")}. No hay acceso, pero la escuela conserva todos sus datos, al volver no paga nueva puesta en marcha y mantiene su precio la temporada siguiente. Si no la mantienes, al volver se hace una nueva puesta en marcha, sin los datos anteriores.`,
    },
    {
        q: "¿Qué es la puesta en marcha?",
        a: `Es un pago único de ${SETUP_FEE} € la primera temporada. Incluye la reunión inicial, el alta de la escuela, del responsable y de los monitores, la configuración de tipos de clase, tarifas, suplementos y retenciones, y una formación breve al responsable.`,
    },
    {
        q: "¿Qué pasa si la aplicación falla en plena temporada?",
        a: "El servicio incluye copias de seguridad diarias de la base de datos.",
    },
    {
        q: "¿Hay permanencia?",
        a: "No. La escuela puede cancelar cuando quiera. Los importes publicados no incluyen IVA.",
    },
];

function CheckList({ items, dark = false }: { items: string[]; dark?: boolean }) {
    return (
        <ul className="flex flex-col gap-3 text-base leading-normal">
            {items.map((item) => (
                <li key={item} className="flex gap-3">
                    <Check aria-hidden className={`mt-0.5 h-5 w-5 flex-none ${dark ? "text-emerald-300" : "text-emerald-600"}`} strokeWidth={2.4} />
                    {item}
                </li>
            ))}
        </ul>
    );
}

function Screenshot({ src, alt, priority = false }: { src: string; alt: string; priority?: boolean }) {
    return (
        <div className={screenshotFrame}>
            <Image src={src} alt={alt} width={1920} height={1200} priority={priority} className="block h-auto w-full" />
        </div>
    );
}

export default function LandingPage() {
    return (
        <div data-landing className="min-h-screen bg-slate-50 text-slate-900">
            <SessionRedirect />
            {/* Cabecera */}
            <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
                <div className={`${container} flex items-center justify-between gap-3 py-3.5`}>
                    <Link href="/" className="flex items-center gap-3">
                        <Image src="/logo.webp" alt="Vesotel" width={44} height={40} className="h-auto w-11" />
                        <span className="flex flex-col leading-tight">
                            <span className="text-[19px] font-extrabold">Vesotel</span>
                            <span className="hidden text-[13px] text-slate-500 sm:inline">Jornadas</span>
                        </span>
                    </Link>
                    <nav aria-label="Principal" className="flex items-center gap-2 text-[15px] font-medium">
                        <div className="hidden items-center gap-1 md:flex">
                            <a href="#funciones" className="p-3 text-slate-600 hover:text-slate-900">Funciones</a>
                            <a href="#precios" className="p-3 text-slate-600 hover:text-slate-900">Planes</a>
                            <a href="#preguntas" className="p-3 text-slate-600 hover:text-slate-900">Preguntas</a>
                        </div>
                        <Link
                            href="/login"
                            className="inline-flex min-h-11 items-center whitespace-nowrap rounded-[10px] border border-slate-200 bg-white px-4 font-semibold hover:bg-slate-50"
                        >
                            Acceder
                        </Link>
                        <a
                            href="#contacto"
                            className="inline-flex min-h-11 items-center whitespace-nowrap rounded-[10px] bg-slate-900 px-4 font-semibold text-white hover:bg-slate-800"
                        >
                            Pide una demo
                        </a>
                    </nav>
                </div>
            </header>

            <main>
                {/* Hero */}
                <section className="pb-14 pt-16 sm:pt-[72px]">
                    <div className={`${container} flex flex-col items-center gap-7 text-center`}>
                        <span className="rounded-full border border-indigo-100 bg-indigo-50 px-3.5 py-1.5 text-[13px] font-semibold text-indigo-600">
                            Para escuelas de esquí de España · Temporada 2026-2027
                        </span>
                        <h1 className="max-w-[900px] text-[clamp(36px,5vw,60px)] font-extrabold leading-[1.05] tracking-[-0.03em]">
                            Asigna las clases. Las horas y los importes se calculan solos.
                        </h1>
                        <p className="max-w-[700px] text-[19px] leading-relaxed text-slate-500">
                            El responsable reparte las clases desde un panel, cada monitor las consulta desde el navegador de su móvil y a final de
                            mes el resumen por monitor ya está hecho. Sin hojas de cálculo.
                        </p>
                        <div className="flex flex-wrap justify-center gap-3">
                            <a href="#contacto" className="rounded-[10px] bg-slate-900 px-6 py-3.5 font-semibold text-white hover:bg-slate-800">
                                Pide una demo de 20 min
                            </a>
                            <a href="#precios" className="rounded-[10px] border border-slate-200 bg-white px-6 py-3.5 font-semibold hover:bg-slate-50">
                                Ver planes
                            </a>
                        </div>
                        <div className="mt-6 w-full max-w-[1100px] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_24px_60px_rgba(15,23,42,0.14)]">
                            <div className="flex items-center gap-2 border-b border-slate-200 bg-slate-100 px-4 py-3" aria-hidden>
                                <span className="h-[11px] w-[11px] rounded-full bg-slate-300" />
                                <span className="h-[11px] w-[11px] rounded-full bg-slate-300" />
                                <span className="h-[11px] w-[11px] rounded-full bg-slate-300" />
                            </div>
                            <Image
                                src="/landing/panel-responsable.webp"
                                alt="Panel del responsable con la operativa del día, horas totales y liquidación del equipo"
                                width={1920}
                                height={1200}
                                priority
                                className="block h-auto w-full"
                            />
                        </div>
                    </div>
                </section>

                {/* Problema: antes y después */}
                <section className="py-14">
                    <div className={`${container} flex flex-col gap-7`}>
                        <div className="flex max-w-[760px] flex-col gap-4">
                            <span className={eyebrow}>¿Te suena?</span>
                            <h2 className={sectionTitle}>Cada fin de mes, horas sumando clases de monitores a mano</h2>
                            <ul className="flex flex-col gap-3">
                                {pains.map((pain) => (
                                    <li key={pain} className={`${lead} border-l-2 border-slate-300 pl-4`}>
                                        {pain}
                                    </li>
                                ))}
                            </ul>
                        </div>
                        <div className="overflow-x-auto rounded-[14px] border border-slate-200 bg-white">
                            <table className="w-full min-w-[640px] border-collapse text-[15px]">
                                <thead>
                                    <tr className="bg-slate-900 text-left text-white">
                                        <th className="px-5 py-4 font-semibold">Aspecto</th>
                                        <th className="px-5 py-4 font-semibold">Hoy, a mano</th>
                                        <th className="px-5 py-4 font-semibold">Con Vesotel Jornadas</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {comparison.map(([aspect, before, after]) => (
                                        <tr key={aspect} className="border-t border-slate-200">
                                            <td className="px-5 py-4 font-semibold">{aspect}</td>
                                            <td className="px-5 py-4 text-slate-500">{before}</td>
                                            <td className="px-5 py-4">{after}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </section>

                {/* Responsable: calendario */}
                <section id="funciones" className="scroll-mt-24 py-14">
                    <div className={`${container} flex flex-wrap items-center gap-12`}>
                        <div className="flex min-w-0 flex-[1_1_360px] flex-col gap-4">
                            <span className={eyebrow}>Para el responsable</span>
                            <h2 className={sectionTitle}>Toda la escuela en un calendario</h2>
                            <p className={lead}>Vista de mes, semana, día y agenda con las clases de cada monitor, y filtro por monitor.</p>
                            <CheckList
                                items={[
                                    "Alta individual o para varios monitores a la vez, y edición en cualquier momento",
                                    "Tipos de clase a medida: por horas, por días o importe fijo",
                                    "Equipo: activa, desactiva y ordena la plantilla (el alta inicial la hacemos nosotros en la puesta en marcha)",
                                ]}
                            />
                        </div>
                        <div className="min-w-0 flex-[1.4_1_520px]">
                            <Screenshot src="/landing/calendario-equipo.webp" alt="Calendario de equipo con las clases del mes de cada monitor" />
                        </div>
                    </div>
                </section>

                {/* Responsable: parte diario */}
                <section className="py-14">
                    <div className={`${container} flex flex-col gap-7`}>
                        <div className="flex flex-wrap items-end justify-between gap-6">
                            <div className="flex min-w-0 max-w-[640px] flex-[1_1_420px] flex-col gap-3.5">
                                <span className={eyebrow}>Parte diario</span>
                                <h2 className={sectionTitle}>El día de todo el equipo, de un vistazo</h2>
                                <p className={lead}>
                                    Una fila por monitor y una columna por hora. Ves quién está libre, quién tiene clase y a qué hora, y añades una clase
                                    pulsando en el hueco.
                                </p>
                            </div>
                            <div className="flex-[0_1_380px]">
                                <CheckList
                                    items={[
                                        "Franja horaria ajustable a la jornada de la escuela",
                                        "Pasa de un día a otro con las flechas",
                                        "Incluido en todos los planes",
                                    ]}
                                />
                            </div>
                        </div>
                        <Screenshot src="/landing/parte-diario.webp" alt="Parte diario del responsable con las clases de cada monitor por horas" />
                    </div>
                </section>

                {/* Responsable: liquidación */}
                <section className="py-14">
                    <div className={`${container} flex flex-wrap-reverse items-center gap-12`}>
                        <div className="min-w-0 flex-[1.4_1_520px]">
                            <Screenshot src="/landing/facturacion.webp" alt="Resumen y facturación del mes con coste bruto, neto y total por monitor" />
                        </div>
                        <div className="flex min-w-0 flex-[1_1_360px] flex-col gap-4">
                            <span className={eyebrow}>Liquidación</span>
                            <h2 className={sectionTitle}>El cierre de mes, ya calculado</h2>
                            <p className={lead}>Totales por monitor, por tipo de clase y por periodo, en bruto y en neto. Los listados se exportan a CSV para la gestoría.</p>
                            <CheckList
                                items={[
                                    "Tarifa propia por monitor y tipo de clase, en bruto o en neto",
                                    "Suplementos como nocturnidad u otros pluses",
                                    "Seguridad Social, IRPF y otras retenciones con su desglose",
                                    "Cada clase guarda su tarifa: cambiar una tarifa no altera lo ya registrado, aunque edites la clase",
                                ]}
                            />
                        </div>
                    </div>
                </section>

                {/* Monitores */}
                <section className="pb-[72px] pt-14">
                    <div className={container}>
                        <div className="flex flex-wrap items-end gap-12 overflow-hidden rounded-[20px] bg-slate-900 px-6 pt-12 text-white sm:px-10">
                            <div className="flex min-w-0 flex-[1_1_360px] flex-col gap-4 pb-12">
                                <span className="text-[13px] font-semibold uppercase tracking-[0.08em] text-indigo-300">Para los monitores</span>
                                <h2 className={sectionTitle}>Sus clases y lo que lleva generado, desde el navegador del móvil</h2>
                                <p className="text-[17px] leading-relaxed text-slate-300">
                                    Cada monitor entra con su usuario y solo ve lo suyo. No tiene que instalar nada.
                                </p>
                                <CheckList
                                    dark
                                    items={[
                                        "Calendario con sus clases por día, semana o mes",
                                        "Horas trabajadas e importe generado, con el desglose",
                                        "Acceso con cuenta personal y verificación en dos pasos opcional",
                                    ]}
                                />
                            </div>
                            <div className="mx-auto min-w-0 flex-[0_1_320px]">
                                <div className="rounded-t-[36px] border border-b-0 border-slate-700 bg-slate-800 px-3 pt-3">
                                    <Image
                                        src="/landing/panel-monitor-movil.webp"
                                        alt="Panel del monitor en el móvil con ingresos del mes, días de actividad y horas por tipo de clase"
                                        width={780}
                                        height={1688}
                                        className="block h-auto w-full rounded-t-[26px]"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Módulos */}
                <section id="modulos" className="scroll-mt-24 py-14">
                    <div className={`${container} flex flex-col gap-7`}>
                        <div className="flex max-w-[720px] flex-col gap-2.5">
                            <span className={eyebrow}>Módulos</span>
                            <h2 className={sectionTitle}>Dos módulos para completar la herramienta</h2>
                            <p className={lead}>
                                Seguimos desarrollando módulos nuevos de forma continua. Si tu escuela necesita algo concreto,{" "}
                                <a href="#contacto" className="font-semibold text-slate-900 underline underline-offset-4">
                                    cuéntanoslo
                                </a>
                                .
                            </p>
                        </div>
                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="flex flex-col gap-3 rounded-[14px] border border-slate-200 bg-white p-6">
                                <h3 className="text-[19px] font-bold">Cuadrante compartido</h3>
                                <p className="text-base leading-relaxed text-slate-600">Cada monitor ve las clases de sus compañeros del día.</p>
                                <p className="text-sm text-slate-500">
                                    Incluido en los planes {getPlan("escuela").name} y {getPlan("grande").name}; en {getPlan("basico").name},{" "}
                                    {formatEurosCompact(EXTRAS.sharedSchedule)} al mes.
                                </p>
                            </div>
                            <div className="flex flex-col gap-3 rounded-[14px] border border-slate-200 bg-white p-6">
                                <h3 className="text-[19px] font-bold">Informes</h3>
                                <p className="text-base leading-relaxed text-slate-600">Genera y descarga informes en PDF y CSV, con un formato fijo.</p>
                                <p className="text-base leading-relaxed text-slate-600">Informes a medida: bajo consulta.</p>
                                <p className="text-sm text-slate-500">
                                    Incluido en los planes {getPlan("escuela").name} y {getPlan("grande").name}; en {getPlan("basico").name},{" "}
                                    {formatEurosCompact(EXTRAS.reports)} al mes.
                                </p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Precios */}
                <section id="precios" className="scroll-mt-24 border-y border-slate-200 bg-white py-20">
                    <div className={`${container} flex flex-col gap-9`}>
                        <div className="flex max-w-[720px] flex-col gap-2.5">
                            <span className={eyebrow}>Planes</span>
                            <h2 className={sectionTitle}>Pagas solo los meses que abres</h2>
                            <p className={lead}>Elige el plan por número de monitores. Sin permanencia.</p>
                        </div>

                        <PlanCards />
                        <div className="mx-auto w-full max-w-[720px]">
                            <PricingCalculator />
                        </div>
                    </div>
                </section>

                <MonitorSection />
                {/* Prueba social: pendiente. Sin clientes aun. No anadir testimonios ni logos inventados (decision del usuario: sin oferta escuela fundadora). */}

                {/* Cómo empezar */}
                <section className="pb-10 pt-20">
                    <div className={`${container} flex flex-col gap-8`}>
                        <h2 className={sectionTitle}>Cómo empezar</h2>
                        <ol className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-4">
                            {steps.map((step, i) => (
                                <li key={step} className="flex flex-col gap-2.5 rounded-[14px] border border-slate-200 bg-white p-5">
                                    <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-[15px] font-bold text-white">{i + 1}</span>
                                    <p className="text-[15px] leading-normal">{step}</p>
                                </li>
                            ))}
                        </ol>
                    </div>
                </section>

                {/* Preguntas frecuentes */}
                <section id="preguntas" className="scroll-mt-24 pb-20 pt-14">
                    <div className="mx-auto flex max-w-[820px] flex-col gap-7 px-6">
                        <h2 className={sectionTitle}>Preguntas frecuentes</h2>
                        <Accordion type="single" collapsible defaultValue="faq-0" className="rounded-[14px] border border-slate-200 bg-white px-6">
                            {faqs.map((faq, i) => (
                                <AccordionItem key={faq.q} value={`faq-${i}`} className="last:border-b-0">
                                    <AccordionTrigger className="py-5 text-left text-[17px] font-semibold hover:no-underline">{faq.q}</AccordionTrigger>
                                    <AccordionContent className="text-base leading-relaxed text-slate-600">{faq.a}</AccordionContent>
                                </AccordionItem>
                            ))}
                        </Accordion>
                    </div>
                </section>

                {/* Contacto */}
                <section id="contacto" className="scroll-mt-24 bg-slate-900 py-20 text-white">
                    <div className={`${container} flex flex-wrap gap-10`}>
                        <div className="flex flex-[1_1_320px] flex-col gap-4">
                            <h2 className={sectionTitle}>Pide una demo de 20 minutos</h2>
                            <p className="text-[17px] leading-relaxed text-slate-300">
                                Cuéntanos cómo organizáis las clases y te enseñamos la aplicación. Sin compromiso ni permanencia.
                            </p>
                        </div>
                        <div className="flex-[1_1_420px]">
                            <ContactForm />
                        </div>
                    </div>
                </section>
            </main>

            <footer className="border-t border-slate-800 bg-slate-900 py-7 text-sm text-slate-400">
                <div className={`${container} flex flex-wrap items-center justify-between gap-4`}>
                    <span>Vesotel Jornadas</span>
                    <Link href="/login" className="p-3 text-slate-300 hover:text-white">
                        Acceder
                    </Link>
                </div>
            </footer>
        </div>
    );
}
