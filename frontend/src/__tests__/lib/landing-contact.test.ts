import { describe, it, expect, vi, afterEach } from 'vitest';
import {
    CONTACT_EMAIL,
    CONTACT_SUBJECT,
    EMPTY_CONTACT,
    MONITOR_WAITLIST_MESSAGE,
    MONITOR_WAITLIST_SUBJECT,
    SELECT_PLAN_EVENT,
    announcePlan,
    buildContactMessage,
    buildMailtoUrl,
    buildWhatsAppUrl,
    validateContact,
    type ContactData,
} from '@/lib/landing-contact';

const valid: ContactData = {
    school: 'Escuela Sol y Nieve',
    monitors: '18',
    plan: 'escuela',
    contactName: 'Ana Pérez',
    email: 'ana@escuela.es',
};

afterEach(() => {
    vi.restoreAllMocks();
});

describe('buildContactMessage', () => {
    it('genera el mensaje exacto con los campos del formulario', () => {
        expect(buildContactMessage(valid)).toBe(
            'Hola, quiero pedir una demo de Vesotel Jornadas.\nEscuela: Escuela Sol y Nieve\nMonitores (aprox.): 18\nPlan: Pista Azul\nContacto: Ana Pérez\nCorreo: ana@escuela.es',
        );
    });

    it('usa la etiqueta de cada plan', () => {
        expect(buildContactMessage({ ...valid, plan: 'basico' })).toContain('Plan: Pista Verde');
        expect(buildContactMessage({ ...valid, plan: 'grande' })).toContain('Plan: Pista Roja');
        expect(buildContactMessage({ ...valid, plan: 'no-se' })).toContain('Plan: No lo sé');
    });

    it('recorta los espacios de los campos', () => {
        expect(buildContactMessage({ ...valid, school: '  Sol  ' })).toContain('Escuela: Sol\n');
    });
});

describe('buildWhatsAppUrl', () => {
    const message = buildContactMessage({ ...valid, school: 'Esquí & Nieve #1' });
    const url = buildWhatsAppUrl(message);

    it('empieza por el numero de WhatsApp y el parametro text', () => {
        expect(url.startsWith('https://wa.me/34685710117?text=')).toBe(true);
    });

    it('codifica el texto sin caracteres que rompan la URL', () => {
        const query = url.slice('https://wa.me/34685710117?text='.length);
        expect(query).toContain('Esqu%C3%AD%20%26%20Nieve%20%231');
        expect(query).toContain('%0A');
        expect(query).not.toMatch(/[&# \n]/);
    });

    it('al decodificar el texto se recupera el mensaje original', () => {
        const query = url.slice('https://wa.me/34685710117?text='.length);
        expect(decodeURIComponent(query)).toBe(message);
    });
});

describe('buildMailtoUrl', () => {
    it('usa el correo de contacto, el asunto y el cuerpo codificados', () => {
        const message = buildContactMessage(valid);
        const url = buildMailtoUrl(CONTACT_SUBJECT, message);
        expect(url.startsWith(
            'mailto:hugo@vesotel.com?subject=Solicitud%20de%20demo%20de%20Vesotel%20Jornadas&body=',
        )).toBe(true);
        const body = url.slice(url.indexOf('&body=') + '&body='.length);
        expect(decodeURIComponent(body)).toBe(message.replace(/\n/g, '\r\n'));
    });

    it('codifica las tildes y los saltos de linea CRLF de la lista de espera', () => {
        const url = buildMailtoUrl(MONITOR_WAITLIST_SUBJECT, MONITOR_WAITLIST_MESSAGE);
        expect(url).toContain('%C3%B3');
        expect(url).toContain('%0D%0A');
        const body = decodeURIComponent(url.slice(url.indexOf('&body=') + '&body='.length));
        expect(body).not.toMatch(/(?<!\r)\n/);
        expect(url.startsWith(`mailto:${CONTACT_EMAIL}?subject=`)).toBe(true);
    });
});

describe('validateContact', () => {
    it('devuelve errores de obligatorio para todos los campos vacios, sin plan', () => {
        const errors = validateContact(EMPTY_CONTACT);
        expect(Object.keys(errors).sort()).toEqual(['contactName', 'email', 'monitors', 'school']);
        expect(errors.school).toBe('Indica el nombre de la escuela.');
        expect(errors.monitors).toBe('Indica un número entero de monitores mayor que 0.');
        expect(errors.contactName).toBe('Indica tu nombre.');
        expect(errors.email).toBe('Indica tu correo.');
    });

    it('devuelve un objeto vacio con datos validos', () => {
        expect(validateContact(valid)).toEqual({});
    });

    it.each(['0', '-3', '2.5', 'abc', '1e3', '07'])('rechaza monitores "%s"', (monitors) => {
        expect(validateContact({ ...valid, monitors }).monitors).toBe(
            'Indica un número entero de monitores mayor que 0.',
        );
    });

    it.each(['18', ' 18 '])('acepta monitores "%s"', (monitors) => {
        expect(validateContact({ ...valid, monitors })).toEqual({});
    });

    it('rechaza un correo sin dominio con punto', () => {
        expect(validateContact({ ...valid, email: 'ana@escuela' }).email).toBe(
            'Introduce un correo válido.',
        );
    });

    it('rechaza un correo con espacios interiores', () => {
        expect(validateContact({ ...valid, email: 'ana @escuela.es' }).email).toBe(
            'Introduce un correo válido.',
        );
    });

    it('acepta un correo valido', () => {
        expect(validateContact({ ...valid, email: 'ana@escuela.es' })).toEqual({});
    });

    it('trata los campos solo con espacios como vacios', () => {
        const errors = validateContact({
            ...valid,
            school: '   ',
            contactName: '   ',
            email: '   ',
        });
        expect(errors.school).toBe('Indica el nombre de la escuela.');
        expect(errors.contactName).toBe('Indica tu nombre.');
        expect(errors.email).toBe('Indica tu correo.');
    });

    it('nunca devuelve error para el plan', () => {
        expect(validateContact({ ...valid, plan: 'no-se' })).toEqual({});
    });
});

describe('announcePlan', () => {
    it('despacha SELECT_PLAN_EVENT en window con el plan como detail', () => {
        const listener = vi.fn();
        window.addEventListener(SELECT_PLAN_EVENT, listener);
        try {
            announcePlan('grande');
            expect(listener).toHaveBeenCalledTimes(1);
            const event = listener.mock.calls[0][0] as CustomEvent<string>;
            expect(event.detail).toBe('grande');
        } finally {
            window.removeEventListener(SELECT_PLAN_EVENT, listener);
        }
    });
});
