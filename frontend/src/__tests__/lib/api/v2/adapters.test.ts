import { describe, it, expect } from 'vitest';
import {
    fromV2Company,
    fromV2CompanyWithMembers,
    fromV2Member,
    toV2CompanyBody,
} from '@/lib/api/v2/adapters';

const fullCompanyV2 = {
    id: 'c-1',
    name: 'Escuela 1',
    is_active: true,
    is_managed: false,
    tax_config: { iva: 21 },
    worklog_definitions: { particular: { label: 'Particular', unit: 'hours' } },
    settings: { worker_experience: { input_mode: 'timer' } },
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-02-01T00:00:00',
};

const reducedCompanyV2 = {
    id: 'c-1',
    name: 'Escuela 1',
    is_managed: true,
    role: 'worker',
    is_active_member: true,
    rates_config: { particular: { base_rate: 10 } },
    worklog_definitions: {},
    tax_config: { iva: 21 },
    settings: { modules: { reports: true } },
};

const memberV2 = {
    user_id: 'u-1',
    company_id: 'c-1',
    role: 'worker',
    is_active: true,
    sort_order: 2,
    rates_config: { particular: { base_rate: 10, extra_rate: 0 } },
    settings: { allow_tutorial: false },
    joined_at: '2026-01-01T00:00:00',
    user: { id: 'u-1', email: 'ana@b.c', first_name: 'Ana', last_name: 'Lopez', is_active: true },
};

const omit = (obj: Record<string, any>, keys: string[]): Record<string, any> =>
    Object.fromEntries(Object.entries(obj).filter(([key]) => !keys.includes(key)));

describe('fromV2Company', () => {
    it('convierte las claves de primer nivel de la vista completa a camelCase', () => {
        const result = fromV2Company(fullCompanyV2 as any);

        expect(Object.keys(result).sort()).toEqual(
            ['createdAt', 'id', 'isActive', 'isManaged', 'name', 'settings', 'taxConfig', 'updatedAt', 'worklogDefinitions'].sort()
        );
        expect(result.isActive).toBe(true);
        expect(result.isManaged).toBe(false);
        expect(result.taxConfig).toEqual({ iva: 21 });
        expect(result.worklogDefinitions).toEqual({ particular: { label: 'Particular', unit: 'hours' } });
        expect(result.createdAt).toBe('2026-01-01T00:00:00');
        expect(result.updatedAt).toBe('2026-02-01T00:00:00');
    });

    it('no crea claves que no vienen en la respuesta', () => {
        const result = fromV2Company(omit(fullCompanyV2, ['created_at', 'updated_at']) as any);

        expect(result).not.toHaveProperty('createdAt');
        expect(result).not.toHaveProperty('updatedAt');
        expect(result.isActive).toBe(true);
    });

    it('elimina la clave members de la vista con miembros', () => {
        const result = fromV2Company({ ...fullCompanyV2, members: [memberV2] } as any);

        expect(result).not.toHaveProperty('members');
    });

    it('convierte la vista reducida sin añadir claves de la vista completa', () => {
        const result = fromV2Company(reducedCompanyV2 as any);

        expect(Object.keys(result).sort()).toEqual(
            ['id', 'isActiveMember', 'isManaged', 'name', 'ratesConfig', 'role', 'settings', 'taxConfig', 'worklogDefinitions'].sort()
        );
        expect(result).not.toHaveProperty('isActive');
        expect(result).not.toHaveProperty('createdAt');
        expect(result).not.toHaveProperty('updatedAt');
        expect(result.isActiveMember).toBe(true);
        expect(result.ratesConfig).toEqual({ particular: { base_rate: 10 } });
    });

    it('conserva sin convertir el contenido interno de settings, rates_config, tax_config y worklog_definitions', () => {
        const result = fromV2Company({
            ...fullCompanyV2,
            settings: { ui_customization: { some_key: 1, camelKey: 2 } },
            tax_config: { iva_reducido: 10 },
        } as any);

        expect(result.settings).toEqual({ ui_customization: { some_key: 1, camelKey: 2 } });
        expect(result.taxConfig).toEqual({ iva_reducido: 10 });
        expect(result.worklogDefinitions).toEqual({ particular: { label: 'Particular', unit: 'hours' } });
    });
});

describe('fromV2Member', () => {
    it('convierte la membresia y el usuario anidado a camelCase', () => {
        const result = fromV2Member(memberV2 as any);

        expect(result.userId).toBe('u-1');
        expect(result.companyId).toBe('c-1');
        expect(result.isActive).toBe(true);
        expect(result.sortOrder).toBe(2);
        expect(result.joinedAt).toBe('2026-01-01T00:00:00');
        expect(result.user).toEqual({
            id: 'u-1',
            email: 'ana@b.c',
            firstName: 'Ana',
            lastName: 'Lopez',
            isActive: true,
        });
        expect(result).not.toHaveProperty('user_id');
        expect(result.user).not.toHaveProperty('first_name');
    });

    it('deja user undefined cuando el backend envia user null', () => {
        const result = fromV2Member({ ...memberV2, user: null } as any);

        expect(result.user).toBeUndefined();
        expect(result.userId).toBe('u-1');
    });

    it('no añade la clave user cuando la respuesta no la incluye', () => {
        const result = fromV2Member(omit(memberV2, ['user']) as any);

        expect('user' in result).toBe(false);
    });

    it('conserva sin convertir rates_config y settings', () => {
        const result = fromV2Member(memberV2 as any);

        expect(result.ratesConfig).toEqual({ particular: { base_rate: 10, extra_rate: 0 } });
        expect(result.settings).toEqual({ allow_tutorial: false });
    });

    it('convierte updated_at de MemberOut a updatedAt', () => {
        const result = fromV2Member({ ...memberV2, updated_at: '2026-03-01T00:00:00' } as any);

        expect(result.updatedAt).toBe('2026-03-01T00:00:00');
    });
});

describe('fromV2CompanyWithMembers', () => {
    it('convierte los miembros a camelCase', () => {
        const result = fromV2CompanyWithMembers({ ...fullCompanyV2, members: [memberV2] } as any);

        expect(result.isManaged).toBe(false);
        expect(result.members).toHaveLength(1);
        expect(result.members[0].userId).toBe('u-1');
        expect(result.members[0].user?.firstName).toBe('Ana');
    });

    it('devuelve members como [] cuando el backend no lo envia', () => {
        const result = fromV2CompanyWithMembers(fullCompanyV2 as any);

        expect(result.members).toEqual([]);
    });
});

describe('toV2CompanyBody', () => {
    it('convierte las claves de primer nivel de camelCase a snake_case', () => {
        const body = toV2CompanyBody({
            name: 'Escuela 1',
            taxConfig: { iva: 21 },
            worklogDefinitions: {},
            isManaged: true,
            isActive: false,
        });

        expect(body).toEqual({
            name: 'Escuela 1',
            tax_config: { iva: 21 },
            worklog_definitions: {},
            is_managed: true,
            is_active: false,
        });
    });

    it('no toca el contenido interno de los valores', () => {
        const body = toV2CompanyBody({
            taxConfig: { someKey: 1, otherTax: 2 },
            settings: { ui_customization: { labelText: 'x' } },
        });

        expect(body).toEqual({
            tax_config: { someKey: 1, otherTax: 2 },
            settings: { ui_customization: { labelText: 'x' } },
        });
    });

    it('mantiene reason como campo de auditoria', () => {
        const body = toV2CompanyBody({ isActive: false, reason: 'Impago' });

        expect(body).toEqual({ is_active: false, reason: 'Impago' });
    });

    it('deja intactas las claves que ya estan en snake_case', () => {
        const body = toV2CompanyBody({ tax_config: { iva: 21 }, is_managed: true });

        expect(body).toEqual({ tax_config: { iva: 21 }, is_managed: true });
    });
});
