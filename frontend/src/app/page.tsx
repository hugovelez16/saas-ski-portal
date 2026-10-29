import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { Check } from "lucide-react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { ContactForm, CONTACT_EMAIL } from "@/components/landing/contact-form";
import { PricingCalculator } from "@/components/landing/pricing-calculator";
import {
    BASE_FEE,
    EXTRA_MANAGER_FEE,
    MODULE_FEES,
    MONITOR_TIERS,
    OFF_SEASON_FEE,
    SETUP_FEE,
    formatEuros,
} from "@/lib/landing-pricing";

export const metadata: Metadata = {
    title: "Vesotel Jornadas: gestión de clases y monitores para escuelas de esquí",
    description:
        "Asigna las clases a tus monitores y deja que las horas y los importes se calculen solos. Calendario, parte diario y liquidación para escuelas de esquí.",
};

const container = "mx-auto max-w-[1200px] px-6";
const eyebrow = "text-[13px] font-semibold uppercase tracking-[0.08em] text-slate-500";
const sectionTitle = "text-[clamp(28px,3.4vw,40px)] font-extrabold leading-[1.1] tracking-tight";
const lead = "text-[17px] leading-relaxed text-slate-500";
const screenshotFrame = "overflow-hidden rounded-[14px] border border-slate-200 bg-white shadow-[0_16px_40px_rgba(15,23,42,0.10)]";

const comparison = [
    ["Asignar una clase", "Anotarla y avisar al monitor", "Se registra en la app, una a una o en bloque"],
    ["Aviso al monitor", "Manual, uno a uno", "La ve en su calendario al momento"],
    ["Total por monitor", "Sumar horas y hacer cuentas al cierre", "Calculado solo, por monitor y por periodo"],
    ["Suplementos y retenciones", "Se calculan a mano", "Se configuran una vez y se aplican con su desglose"],
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
        a: "Sí. Cada clase guarda el desglose con el que se calculó, así que el cambio solo afecta a las clases que se registren a partir de ese momento.",
    },
    {
        q: "¿Qué pasa con mis datos fuera de temporada?",
        a: `Puedes mantener la escuela lista para la siguiente temporada por ${OFF_SEASON_FEE} € al mes de mayo a noviembre, o darla de baja sin coste y volver más adelante con una nueva puesta en marcha. La exportación de tus datos es siempre gratuita.`,
    },
    {
        q: "¿Qué pasa si la aplicación falla en plena temporada?",
        a: "El servicio incluye copias de seguridad periódicas de la base de datos, guardadas fuera del servidor donde funciona la aplicación.",
    },
    {
        q: "¿Hay permanencia?",
        a: "No. La escuela puede cancelar cuando quiera.",
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
        <div className="min-h-screen bg-slate-50 text-slate-900">
            {/* Cabecera */}
            <header className="border-b border-slate-200 bg-white">
                <div className={`${container} flex flex-wrap items-center justify-between gap-3 py-3.5`}>
                    <Link href="/" className="flex items-center gap-3">
                        <Image src="/logo.webp" alt="Vesotel" width={44} height={40} className="h-auto w-11" />
                        <span className="flex flex-col leading-tight">
                            <span className="text-[19px] font-extrabold">Vesotel</span>
                            <span className="text-[13px] text-slate-500">Jornadas</span>
                        </span>
                    </Link>
                    <nav aria-label="Principal" className="flex flex-wrap items-center gap-1 text-[15px] font-medium">
                        <a href="#funciones" className="p-3 text-slate-600 hover:text-slate-900">Funciones</a>
                        <a href="#precios" className="p-3 text-slate-600 hover:text-slate-900">Precios</a>
                        <a href="#preguntas" className="p-3 text-slate-600 hover:text-slate-900">Preguntas</a>
                        <Link href="/login" className="rounded-[10px] border border-slate-200 bg-white px-4 py-2.5 font-semibold hover:bg-slate-50">
                            Acceder
                        </Link>
                        <a href="#contacto" className="rounded-[10px] bg-slate-900 px-4 py-3 font-semibold text-white hover:bg-slate-800">
                            Solicitar información
                        </a>
                    </nav>
                </div>
            </header>

            <main>
                {/* Hero */}
                <section className="pb-14 pt-16 sm:pt-[72px]">
                    <div className={`${container} flex flex-col items-center gap-7 text-center`}>
                        <span className="rounded-full border border-indigo-100 bg-indigo-50 px-3.5 py-1.5 text-[13px] font-semibold text-indigo-600">
                            Para escuelas de esquí · Temporada 2026-2027
                        </span>
                        <h1 className="max-w-[900px] text-[clamp(36px,5vw,60px)] font-extrabold leading-[1.05] tracking-[-0.03em]">
                            Asigna las clases. Las horas y los importes se calculan solos.
                        </h1>
                        <p className="max-w-[700px] text-[19px] leading-relaxed text-slate-500">
                            El responsable reparte las clases desde un panel, cada monitor las ve en su móvil y a final de mes el resumen por
                            monitor ya está hecho. Sin hojas de cálculo ni avisos uno a uno.
                        </p>
                        <div className="flex flex-wrap justify-center gap-3">
                            <a href="#contacto" className="rounded-[10px] bg-slate-900 px-6 py-3.5 font-semibold text-white hover:bg-slate-800">
                                Solicitar información
                            </a>
                            <a href="#precios" className="rounded-[10px] border border-slate-200 bg-white px-6 py-3.5 font-semibold hover:bg-slate-50">
                                Ver precios
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

                {/* Antes y después */}
                <section className="py-14">
                    <div className={`${container} flex flex-col gap-7`}>
                        <div className="flex max-w-[720px] flex-col gap-2.5">
                            <h2 className={sectionTitle}>Entre 4 y 5 horas al mes, solo en contar horas</h2>
                            <p className={lead}>
                                Es lo que dedica de media un responsable a sumar las horas de cada monitor y calcular lo que le corresponde, sin contar
                                los cambios de cada día.
                            </p>
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
                <section id="funciones" className="py-14">
                    <div className={`${container} flex flex-wrap items-center gap-12`}>
                        <div className="flex min-w-0 flex-[1_1_360px] flex-col gap-4">
                            <span className={eyebrow}>Para el responsable</span>
                            <h2 className={sectionTitle}>Toda la escuela en un calendario</h2>
                            <p className={lead}>
                                Vista de mes, semana, día y agenda con las clases de cada monitor. Mueves una clase arrastrándola y el monitor lo ve al
                                instante.
                            </p>
                            <CheckList
                                items={[
                                    "Alta individual o masiva de clases, y edición en cualquier momento",
                                    "Tipos de clase a medida: por horas, por días o importe fijo",
                                    "Equipo: alta, baja y orden de la plantilla",
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
                                <CheckList items={["Franja horaria ajustable a la jornada de la escuela", "Pasa de un día a otro con las flechas"]} />
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
                            <p className={lead}>Totales por monitor, por tipo de clase y por periodo, en bruto y en neto. Se exporta a CSV para la gestoría.</p>
                            <CheckList
                                items={[
                                    "Tarifa propia por monitor y tipo de clase, en bruto o en neto",
                                    "Suplementos como nocturnidad u otros pluses",
                                    "Seguridad Social, IRPF y otras retenciones con su desglose",
                                    "Cada clase guarda su cálculo: cambiar una tarifa no altera lo ya registrado",
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
                                <h2 className={sectionTitle}>Sus clases y lo que lleva ganado, en el móvil</h2>
                                <p className="text-[17px] leading-relaxed text-slate-300">
                                    Cada monitor entra con su usuario y solo ve lo suyo. No tiene que instalar nada ni esperar a que le avisen.
                                </p>
                                <CheckList
                                    dark
                                    items={[
                                        "Calendario con sus clases por día, semana o mes",
                                        "Horas trabajadas e importe generado, con el desglose",
                                        "Cuenta personal con contraseña y verificación en dos pasos",
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

                {/* Precios */}
                <section id="precios" className="border-y border-slate-200 bg-white py-20">
                    <div className={`${container} flex flex-col gap-9`}>
                        <div className="flex max-w-[720px] flex-col gap-2.5">
                            <span className={eyebrow}>Precios</span>
                            <h2 className={sectionTitle}>Pagas solo los meses de temporada</h2>
                            <p className={lead}>
                                Temporada de diciembre a abril. Se factura por las cuentas de monitor de cada mes, así que si entran o salen monitores el
                                importe se ajusta. Sin permanencia.
                            </p>
                        </div>

                        <div className="flex flex-wrap items-stretch gap-6">
                            <div className="flex min-w-0 flex-[1_1_420px] flex-col gap-5">
                                <div className="flex flex-col gap-3.5 rounded-[14px] border border-slate-200 bg-slate-50 p-6">
                                    <div className="flex flex-wrap items-baseline justify-between gap-3">
                                        <span className="font-semibold">Cuota base de la escuela</span>
                                        <span className="text-[28px] font-extrabold tracking-tight">
                                            {BASE_FEE} € <span className="text-sm font-medium text-slate-500">/mes</span>
                                        </span>
                                    </div>
                                    <p className="text-sm text-slate-500">
                                        Incluye una cuenta de responsable. Cada responsable adicional, {EXTRA_MANAGER_FEE} € al mes.
                                    </p>
                                </div>

                                <div className="overflow-hidden rounded-[14px] border border-slate-200">
                                    <table className="w-full border-collapse text-[15px]">
                                        <thead>
                                            <tr className="bg-slate-900 text-left text-white">
                                                <th className="px-5 py-3 font-semibold">Monitores</th>
                                                <th className="px-5 py-3 text-right font-semibold">Por monitor y mes</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {MONITOR_TIERS.map((tier) => (
                                                <tr key={tier.from} className="border-t border-slate-200">
                                                    <td className="px-5 py-3">
                                                        {tier.from} a {tier.to}
                                                    </td>
                                                    <td className="px-5 py-3 text-right font-semibold tabular-nums">{formatEuros(tier.price)}</td>
                                                </tr>
                                            ))}
                                            <tr className="border-t border-slate-200">
                                                <td className="px-5 py-3">Más de 50</td>
                                                <td className="px-5 py-3 text-right font-semibold">A consultar</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                                <p className="text-sm leading-normal text-slate-500">
                                    Tramos progresivos: cada precio se aplica solo a los monitores de ese tramo. Con 15 monitores, los 10 primeros a 5,00 € y
                                    los 5 siguientes a 4,75 €.
                                </p>

                                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                                    {[
                                        ["Módulo Informes", `${MODULE_FEES.reports} € /mes`],
                                        ["Parte diario del equipo", `${MODULE_FEES.teamDailyReport} € /mes`],
                                        ["Puesta en marcha", `${SETUP_FEE} € una vez`],
                                        ["Mantenimiento fuera de temporada", `${OFF_SEASON_FEE} € /mes`],
                                    ].map(([label, price]) => (
                                        <div key={label} className="flex flex-col gap-1 rounded-xl border border-slate-200 p-4">
                                            <span className="text-sm text-slate-500">{label}</span>
                                            <span className="text-lg font-bold">{price}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="min-w-0 flex-[1_1_380px]">
                                <PricingCalculator />
                            </div>
                        </div>
                    </div>
                </section>

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
                <section id="preguntas" className="pb-20 pt-14">
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
                <section id="contacto" className="bg-slate-900 py-20 text-white">
                    <div className={`${container} flex flex-wrap items-start gap-12`}>
                        <div className="flex min-w-0 flex-[1_1_360px] flex-col gap-4">
                            <h2 className={sectionTitle}>Ten la escuela lista antes del primer día de nieve</h2>
                            <p className="text-[17px] leading-relaxed text-slate-300">
                                Cuéntanos cuántos monitores tienes y te preparamos un presupuesto. Te respondemos por correo.
                            </p>
                            <p className="text-[15px] text-slate-400">
                                O escríbenos a{" "}
                                <a href={`mailto:${CONTACT_EMAIL}`} className="text-white underline">
                                    {CONTACT_EMAIL}
                                </a>
                            </p>
                        </div>
                        <div className="min-w-0 flex-[1_1_460px]">
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
