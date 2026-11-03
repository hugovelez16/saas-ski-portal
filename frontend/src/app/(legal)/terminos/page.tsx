import type { Metadata } from "next";
import Link from "next/link";
import { LegalContactEmail } from "@/components/legal-contact-email";
import { LEGAL_JURISDICTION, SERVICE_NAME } from "@/lib/legal-config";

export const metadata: Metadata = {
    title: `Términos | ${SERVICE_NAME}`,
    description: `Condiciones de acceso y uso del servicio ${SERVICE_NAME}.`,
};

export default function TermsPage() {
    return (
        <>
            <h1>Términos de uso</h1>

            <h2>Objeto</h2>
            <p>Estos términos regulan el acceso y uso de {SERVICE_NAME}, un servicio SaaS de gestión de escuelas de esquí que permite administrar clases, jornadas, tarifas, importes y retenciones de monitores.</p>

            <h2>Acceso y cuentas</h2>
            <p>El acceso a las funciones privadas requiere una cuenta personal creada por la escuela o por el titular del servicio, según corresponda. Cada persona debe utilizar su propia cuenta y no compartir sus credenciales.</p>

            <h2>Obligaciones de las personas usuarias</h2>
            <ul>
                <li>Mantener la confidencialidad de sus credenciales y avisar de inmediato si sospecha que otra persona las conoce o ha accedido a su cuenta.</li>
                <li>Utilizar el servicio de forma lícita y de acuerdo con estos términos.</li>
                <li>No intentar acceder a cuentas, empresas o datos ajenos ni eludir los controles de acceso.</li>
                <li>Proporcionar información veraz y utilizar el servicio respetando los derechos de otras personas.</li>
            </ul>

            <h2>Responsabilidades de la escuela</h2>
            <p>La escuela es responsable de los datos personales que introduce en el servicio y de disponer de una base jurídica adecuada para su tratamiento. También debe revisar que las tarifas y retenciones que configura sean correctas y apropiadas para su actividad. Los cálculos y resultados de la plataforma son una ayuda operativa y deben ser revisados por la escuela antes de utilizarlos para tomar decisiones o realizar pagos.</p>
            <p>Los datos de cada escuela se mantienen separados de los de las demás empresas usuarias.</p>

            <h2>Disponibilidad y copias de seguridad</h2>
            <p>El titular aplica medidas para mantener el servicio y realiza copias de seguridad diarias de la base de datos. No se garantiza una disponibilidad ininterrumpida ni la ausencia de interrupciones, errores o incidencias. Las copias de seguridad no sustituyen las obligaciones de la escuela sobre la conservación de la información que necesite.</p>

            <h2>Suspensión de cuentas</h2>
            <p>El titular podrá restringir o suspender una cuenta cuando sea necesario para proteger la seguridad del servicio o de sus usuarios, cumplir una obligación legal o responder a un uso contrario a estos términos o al contrato aplicable. Cuando sea posible, se informará a la escuela o a la persona afectada y se facilitará la regularización de la situación.</p>

            <h2>Propiedad intelectual</h2>
            <p>El software, diseño y demás elementos del servicio están protegidos por la normativa de propiedad intelectual e industrial. El acceso no transmite derechos sobre ellos. La persona usuaria puede utilizar el servicio durante la vigencia de su autorización y conforme a estos términos y al contrato con la escuela.</p>

            <h2>Protección de datos</h2>
            <p>El tratamiento de datos personales se describe en la <Link href="/privacidad">política de privacidad</Link>. Respecto de los datos que la escuela introduce para gestionar sus actividades, la escuela actúa como responsable y el titular del servicio como encargado del tratamiento.</p>

            <h2>Condiciones económicas</h2>
            <p>Las condiciones económicas del servicio para cada escuela son las establecidas en el contrato celebrado con ella.</p>

            <h2>Modificaciones</h2>
            <p>El titular podrá actualizar estos términos cuando cambie el servicio o cuando sea necesario por motivos legales u operativos. Se publicará la versión vigente en esta página. Si una modificación afecta de forma sustancial a la relación contractual con una escuela, se comunicará por los medios previstos en su contrato.</p>

            <h2>Ley aplicable y jurisdicción</h2>
            <p>Estos términos se rigen por la legislación española. Las controversias se someterán a {LEGAL_JURISDICTION}, con respeto a las normas imperativas aplicables.</p>

            <h2>Contacto</h2>
            <p>Para consultas sobre estos términos, puedes escribir a <LegalContactEmail />.</p>
        </>
    );
}
