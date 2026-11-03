import type { Metadata } from "next";
import Link from "next/link";
import { LEGAL_OWNER, LEGAL_PROVIDERS, SERVICE_NAME } from "@/lib/legal-config";
import { LegalContactEmail } from "@/components/legal-contact-email";

export const metadata: Metadata = {
    title: `Privacidad | ${SERVICE_NAME}`,
    description: `Información sobre el tratamiento de datos personales en ${SERVICE_NAME}.`,
};

export default function PrivacyPolicyPage() {
    return (
        <>
            <h1>Política de privacidad</h1>

            <h2>Quién trata los datos</h2>
            <p>El titular del servicio es {LEGAL_OWNER.legalName}. Sus datos de identificación figuran en el <Link href="/aviso-legal">aviso legal</Link>. Para contactar: <LegalContactEmail />.</p>
            <p>En la gestión de las cuentas, clases y jornadas de una escuela, la escuela cliente es la responsable del tratamiento de los datos de sus responsables, empleados y monitores. El titular del servicio actúa como encargado del tratamiento conforme al contrato de encargo previsto en el artículo 28 del RGPD. La escuela determina la base jurídica aplicable a ese tratamiento.</p>
            <p>El titular actúa como responsable del tratamiento para gestionar la relación comercial con la escuela, proteger las cuentas y sesiones —incluidos los registros de sesiones y de auditoría— y atender las solicitudes de demostración presentadas mediante la página de inicio.</p>

            <h2>Datos tratados y finalidades</h2>
            <ul>
                <li>Para gestionar el servicio y las cuentas: nombre, apellidos, correo electrónico, contraseña almacenada con hash y, si se configura la verificación en dos pasos, el secreto asociado.</li>
                <li>Para gestionar la actividad de la escuela: membresía, rol, tarifas, registros de clases y jornadas —fechas, horas, duración, importes brutos y netos, retenciones configuradas y descripciones—.</li>
                <li>Para la seguridad y auditoría: datos de sesión, incluida la dirección IP y el nombre del dispositivo, y registro de acciones.</li>
                <li>Para responder a solicitudes de demostración: los datos que la persona facilite al iniciar el contacto.</li>
            </ul>
            <p>La plataforma no está destinada a tratar categorías especiales de datos personales. No se solicitan ni se deben introducir esos datos.</p>

            <h2>Base jurídica</h2>
            <ul>
                <li>La ejecución del contrato con la escuela para gestionar la relación comercial y prestar el servicio.</li>
                <li>El interés legítimo en proteger las cuentas y sesiones y mantener registros de seguridad y auditoría.</li>
                <li>El consentimiento de la persona para atender una solicitud de demostración, que puede retirar en cualquier momento escribiendo al correo de contacto.</li>
                <li>El interés legítimo en mantener y mejorar el servicio para la analítica de uso con PostHog, únicamente cuando esté activada.</li>
                <li>Para los datos tratados por cuenta de una escuela, la base jurídica la determina la propia escuela como responsable.</li>
            </ul>

            <h2>Solicitudes de demostración</h2>
            <p>El formulario de la página de inicio no transmite los datos al servidor. Al enviarlo, prepara un correo electrónico para que la persona decida si lo envía. Si la persona elige WhatsApp, intervienen WhatsApp y Meta como proveedor del servicio elegido por ella, conforme a las condiciones y políticas de ese servicio.</p>

            <h2>Proveedores y destinatarios</h2>
            <p>Para operar el servicio se recurre a los siguientes proveedores, que tratan datos según el servicio que prestan:</p>
            <ul>
                <li>Alojamiento de la aplicación y de la base de datos: {LEGAL_PROVIDERS.hosting}.</li>
                <li>Envío de correos de restablecimiento de contraseña: {LEGAL_PROVIDERS.email}.</li>
                <li>PostHog, con servidor en la Unión Europea (eu.i.posthog.com), para analítica de uso y grabación de sesiones, únicamente si esta función está activada. PostHog identifica al usuario mediante su id interno, enmascara textos y campos de formulario y no graba el flujo de restablecimiento de contraseña. Usa persistencia en memoria: no instala cookies ni utiliza almacenamiento local del dispositivo.</li>
            </ul>
            <p>No se ceden datos a terceros, salvo cuando exista una obligación legal. Los datos de las distintas escuelas se mantienen separados.</p>

            <h2>Conservación</h2>
            <p>Los datos se conservan mientras dure la relación con la escuela o la cuenta correspondiente. Después se mantienen bloqueados durante los plazos legales de prescripción aplicables. Al terminar el contrato de servicio, la devolución o supresión de los datos se realiza conforme al contrato de encargo del tratamiento.</p>

            <h2>Derechos</h2>
            <p>La persona interesada puede ejercer los derechos de acceso, rectificación, supresión, oposición, limitación del tratamiento y portabilidad mediante el correo de contacto: <LegalContactEmail />.</p>
            <p>Si la solicitud se refiere a datos tratados por cuenta de una escuela, se trasladará a esa escuela para que responda como responsable del tratamiento.</p>
            <p>También se puede presentar una reclamación ante la <a href="https://www.aepd.es" target="_blank" rel="noreferrer">Agencia Española de Protección de Datos</a>.</p>

            <h2>Más información</h2>
            <p>Consulta la <Link href="/cookies">política de cookies</Link> y los <Link href="/terminos">términos de uso</Link>.</p>
        </>
    );
}
