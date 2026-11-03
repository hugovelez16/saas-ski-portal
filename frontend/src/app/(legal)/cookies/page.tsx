import type { Metadata } from "next";
import Link from "next/link";
import { LEGAL_OWNER, SERVICE_NAME } from "@/lib/legal-config";
import { LegalContactEmail } from "@/components/legal-contact-email";

export const metadata: Metadata = {
    title: `Cookies | ${SERVICE_NAME}`,
    description: `Información sobre cookies y almacenamiento local técnico de ${SERVICE_NAME}.`,
};

export default function CookiePolicyPage() {
    return (
        <>
            <h1>Política de cookies</h1>

            <h2>Responsable y contacto</h2>
            <p>El titular del sitio es {LEGAL_OWNER.legalName}. Para consultas sobre esta política, contacta con <LegalContactEmail />.</p>

            <h2>Cookies técnicas</h2>
            <p>El servicio utiliza cookies propias estrictamente necesarias para mantener y renovar la sesión autenticada. Son necesarias para prestar el servicio solicitado y están exentas del consentimiento previsto en el artículo 22.2 de la LSSI.</p>
            <div className="overflow-x-auto">
                <table className="w-full border-collapse text-left text-sm">
                    <thead className="bg-slate-100">
                        <tr>
                            <th className="border border-slate-200 px-3 py-2 align-top">Cookie</th>
                            <th className="border border-slate-200 px-3 py-2 align-top">Finalidad</th>
                            <th className="border border-slate-200 px-3 py-2 align-top">Duración</th>
                            <th className="border border-slate-200 px-3 py-2 align-top">Tipo y atributos</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td className="border border-slate-200 px-3 py-2 align-top">access_token</td>
                            <td className="border border-slate-200 px-3 py-2 align-top">Mantener la sesión autenticada</td>
                            <td className="border border-slate-200 px-3 py-2 align-top">30 minutos; 5 minutos durante la verificación en dos pasos</td>
                            <td className="border border-slate-200 px-3 py-2 align-top">Propia, técnica y estrictamente necesaria; HttpOnly, Secure y SameSite=Lax</td>
                        </tr>
                        <tr>
                            <td className="border border-slate-200 px-3 py-2 align-top">refresh_token</td>
                            <td className="border border-slate-200 px-3 py-2 align-top">Renovar la sesión sin volver a iniciarla</td>
                            <td className="border border-slate-200 px-3 py-2 align-top">30 días</td>
                            <td className="border border-slate-200 px-3 py-2 align-top">Propia, técnica y estrictamente necesaria; HttpOnly, Secure y SameSite=Lax</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <h2>Almacenamiento local técnico</h2>
            <p>La aplicación guarda también preferencias y datos técnicos en el almacenamiento local del navegador. No son cookies y permanecen hasta que la persona los borra o elimina los datos del sitio desde el navegador. Son propios y técnicos: sirven para funciones o preferencias que la persona usa de forma expresa, por lo que tampoco requieren consentimiento.</p>
            <div className="overflow-x-auto">
                <table className="w-full border-collapse text-left text-sm">
                    <thead className="bg-slate-100">
                        <tr>
                            <th className="border border-slate-200 px-3 py-2 align-top">Clave</th>
                            <th className="border border-slate-200 px-3 py-2 align-top">Finalidad</th>
                            <th className="border border-slate-200 px-3 py-2 align-top">Duración y tipo</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td className="border border-slate-200 px-3 py-2 align-top">device_token</td>
                            <td className="border border-slate-200 px-3 py-2 align-top">Recordar el dispositivo de confianza para la verificación en dos pasos</td>
                            <td className="border border-slate-200 px-3 py-2 align-top">Almacenamiento local propio, sin caducidad hasta que el usuario lo borre</td>
                        </tr>
                        <tr>
                            <td className="border border-slate-200 px-3 py-2 align-top">lastCompanyId</td>
                            <td className="border border-slate-200 px-3 py-2 align-top">Recordar la última empresa activa; solo guarda su id</td>
                            <td className="border border-slate-200 px-3 py-2 align-top">Almacenamiento local propio, sin caducidad hasta que el usuario lo borre</td>
                        </tr>
                        <tr>
                            <td className="border border-slate-200 px-3 py-2 align-top">calendar_hours_preference</td>
                            <td className="border border-slate-200 px-3 py-2 align-top">Recordar la franja horaria del calendario</td>
                            <td className="border border-slate-200 px-3 py-2 align-top">Almacenamiento local propio, sin caducidad hasta que el usuario lo borre</td>
                        </tr>
                        <tr>
                            <td className="border border-slate-200 px-3 py-2 align-top">dataTable-visibility-*</td>
                            <td className="border border-slate-200 px-3 py-2 align-top">Recordar las columnas visibles de las tablas</td>
                            <td className="border border-slate-200 px-3 py-2 align-top">Almacenamiento local propio, sin caducidad hasta que el usuario lo borre</td>
                        </tr>
                        <tr>
                            <td className="border border-slate-200 px-3 py-2 align-top">admin_companies_view_mode</td>
                            <td className="border border-slate-200 px-3 py-2 align-top">Recordar la vista del listado de empresas, solo para administradores</td>
                            <td className="border border-slate-200 px-3 py-2 align-top">Almacenamiento local propio, sin caducidad hasta que el usuario lo borre</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <h2>Analítica</h2>
            <p>No se utilizan cookies de analítica, publicidad ni cookies de terceros. Si PostHog está activado, se emplea para analítica de uso y grabación de sesiones sin cookies ni almacenamiento en el dispositivo; utiliza persistencia en memoria. Encontrarás los detalles en la <Link href="/privacidad">política de privacidad</Link>.</p>

            <h2>Cómo borrar cookies</h2>
            <p>Puedes borrar las cookies desde la configuración de privacidad o historial de tu navegador, seleccionando la opción para eliminar las cookies y los datos del sitio. Al borrar las cookies de este servicio se cerrará la sesión y tendrás que volver a iniciar sesión.</p>
            <p>El almacenamiento local puede borrarse desde las herramientas de privacidad o configuración del navegador, eliminando los datos de este sitio.</p>
        </>
    );
}
