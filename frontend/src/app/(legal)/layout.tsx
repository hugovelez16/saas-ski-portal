import Image from "next/image";
import Link from "next/link";
import { LegalFooter } from "@/components/legal-footer";
import { LEGAL_LAST_UPDATED, SERVICE_NAME } from "@/lib/legal-config";

/**
 * Layout de las paginas legales. Publico: no usa useAuth ni redirige, para
 * que las paginas se lean sin sesion. Los estilos del texto se aplican a los
 * elementos HTML del contenido para que cada pagina sea solo marcado simple.
 */
export default function LegalLayout({ children }: { children: React.ReactNode }) {
    return (
        <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900">
            <header className="border-b border-slate-200 bg-white">
                <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
                    <Link href="/" className="flex items-center gap-3">
                        <Image src="/logo.webp" alt="Vesotel" width={36} height={33} className="h-auto w-9" />
                        <span className="font-bold">{SERVICE_NAME}</span>
                    </Link>
                    <Link
                        href="/login"
                        className="inline-flex min-h-11 items-center rounded-md border border-slate-200 bg-white px-4 text-sm font-semibold hover:bg-slate-50"
                    >
                        Acceder
                    </Link>
                </div>
            </header>

            <main className="flex-1">
                <article
                    className={[
                        "mx-auto max-w-3xl px-4 py-10 sm:px-6",
                        "text-[15px] leading-relaxed text-slate-700",
                        "[&_h1]:mb-2 [&_h1]:text-3xl [&_h1]:font-bold [&_h1]:tracking-tight [&_h1]:text-slate-900",
                        "[&_h2]:mb-3 [&_h2]:mt-10 [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-slate-900",
                        "[&_h3]:mb-2 [&_h3]:mt-6 [&_h3]:font-semibold [&_h3]:text-slate-900",
                        "[&_p]:mb-4 [&_ul]:mb-4 [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-6",
                        "[&_a]:font-medium [&_a]:text-indigo-600 [&_a]:underline [&_a]:underline-offset-4",
                    ].join(" ")}
                >
                    {children}
                    <p className="mt-12 border-t border-slate-200 pt-4 text-sm text-slate-500">
                        Última actualización: {LEGAL_LAST_UPDATED}
                    </p>
                </article>
            </main>

            <footer className="border-t border-slate-200 bg-white py-4">
                <LegalFooter />
            </footer>
        </div>
    );
}
