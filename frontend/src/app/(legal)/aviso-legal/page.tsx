import type { Metadata } from "next";
import Link from "next/link";
import { LegalContactEmail } from "@/components/legal-contact-email";
import { LEGAL_JURISDICTION, LEGAL_OWNER, SERVICE_NAME } from "@/lib/legal-config";

export const metadata: Metadata = {
    title: `Aviso legal | ${SERVICE_NAME}`,
    description: `Información legal sobre el sitio web ${SERVICE_NAME}.`,
};

export default function LegalNoticePage() {
    return (
        <>
            <h1>Aviso legal</h1>

            <h2>Información del titular</h2>
            <p>En cumplimiento del artículo 10 de la Ley 34/2002, de servicios de la sociedad de la información y de comercio electrónico, se informa de los datos del titular de este sitio:</p>
            <ul>
                <li>Denominación: {LEGAL_OWNER.legalName}</li>
                <li>NIF: {LEGAL_OWNER.taxId}</li>
                <li>Domicilio: {LEGAL_OWNER.address}</li>
                <li>Inscripción: {LEGAL_OWNER.registryData}</li>
                <li>Correo electrónico: <LegalContactEmail /></li>
            </ul>
            <p>Más información sobre el titular en <a href={LEGAL_OWNER.website} target="_blank" rel="noreferrer">vesotel.com</a>.</p>

            <h2>Objeto del sitio</h2>
            <p>Este sitio ofrece información y acceso al servicio SaaS {SERVICE_NAME}, destinado a la gestión de escuelas de esquí, sus clases, jornadas, tarifas, importes y retenciones de monitores.</p>

            <h2>Condiciones de uso</h2>
            <p>La persona usuaria se compromete a utilizar el sitio de forma lícita, diligente y respetuosa con estos términos y con los derechos de terceros. No debe intentar acceder a áreas, cuentas o datos para los que carezca de autorización, ni realizar acciones que perjudiquen la seguridad o disponibilidad del sitio.</p>
            <p>El acceso a las funciones del servicio puede requerir una cuenta y queda sujeto a los <Link href="/terminos">términos de uso</Link>.</p>

            <h2>Propiedad intelectual e industrial</h2>
            <p>Los contenidos, elementos, diseños y componentes del sitio están protegidos por la normativa aplicable sobre propiedad intelectual e industrial. No se permite su reproducción, transformación, distribución o comunicación pública fuera de los usos permitidos por la ley o sin autorización de quien ostente los derechos correspondientes.</p>

            <h2>Responsabilidad</h2>
            <p>El titular procura que la información publicada sea adecuada y que el sitio funcione correctamente, pero no garantiza que esté libre de errores o que el acceso sea ininterrumpido. La información del sitio tiene carácter general y no sustituye la revisión que corresponda a cada escuela sobre sus datos y cálculos.</p>

            <h2>Enlaces</h2>
            <p>Los enlaces a sitios de terceros se ofrecen como referencia. El titular no controla sus contenidos, disponibilidad ni prácticas de privacidad y no asume responsabilidad por ellos.</p>

            <h2>Legislación y jurisdicción</h2>
            <p>Este aviso se rige por la legislación española. Para las cuestiones que puedan someterse a fuero, las partes se atendrán a {LEGAL_JURISDICTION}, sin perjuicio de las normas imperativas que resulten aplicables.</p>
        </>
    );
}
