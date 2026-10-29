import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from '@/lib/api';
import {
    listCompanies,
    getCompany,
    createCompany,
    updateCompany,
    deleteCompany,
    listMyCompanies,
    listUserCompanies,
} from '@/lib/api/v2/companies';
import type { CompanyCreateV2, CompanyUpdateV2, CompanyFull, Page } from '@/lib/api/v2/types';

vi.mock('@/lib/api', () => ({
    default: {
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        delete: vi.fn(),
    },
}));

const mockedApi = vi.mocked(api);

const companyFull: CompanyFull = {
    id: 'c-1',
    name: 'Escuela Sierra',
    is_active: true,
    is_managed: true,
    tax_config: { iva: 21 },
    worklog_definitions: {},
    settings: {},
    created_at: '2026-01-01T00:00:00Z',
    updated_at: null,
};

describe('API v2 Companies client', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('listCompanies', () => {
        it('GET /v2/companies with include=members as params', async () => {
            const page: Page<CompanyFull> = { items: [companyFull], total: 1 };
            (mockedApi.get as any).mockResolvedValue({ data: page });

            const result = await listCompanies({ include: 'members' });

            expect(mockedApi.get).toHaveBeenCalledTimes(1);
            expect(mockedApi.get).toHaveBeenCalledWith('/v2/companies', { params: { include: 'members' } });
            expect(result).toEqual(page);
        });

        it('GET /v2/companies with params undefined when called without arguments', async () => {
            (mockedApi.get as any).mockResolvedValue({ data: { items: [], total: 0 } });

            const result = await listCompanies();

            expect(mockedApi.get).toHaveBeenCalledWith('/v2/companies', { params: undefined });
            expect(result).toEqual({ items: [], total: 0 });
        });

        it('forwards skip and limit without renaming them', async () => {
            (mockedApi.get as any).mockResolvedValue({ data: { items: [], total: 0 } });

            await listCompanies({ skip: 20, limit: 10 });

            expect(mockedApi.get).toHaveBeenCalledWith('/v2/companies', { params: { skip: 20, limit: 10 } });
        });
    });

    describe('getCompany', () => {
        it('GET /v2/companies/:id and returns data', async () => {
            (mockedApi.get as any).mockResolvedValue({ data: companyFull });

            const result = await getCompany('c-1');

            expect(mockedApi.get).toHaveBeenCalledWith('/v2/companies/c-1');
            expect(result).toEqual(companyFull);
        });
    });

    describe('createCompany', () => {
        it('POST /v2/companies with snake_case body and returns data', async () => {
            const body: CompanyCreateV2 = {
                name: 'Escuela Sierra',
                tax_config: { iva: 21 },
                is_managed: true,
            };
            (mockedApi.post as any).mockResolvedValue({ data: { ...companyFull, ...body } });

            const result = await createCompany(body);

            expect(mockedApi.post).toHaveBeenCalledWith('/v2/companies', body);
            expect(result.id).toBe('c-1');
            expect(result.tax_config).toEqual({ iva: 21 });
        });
    });

    describe('updateCompany', () => {
        it('PUT /v2/companies/:id with body unchanged', async () => {
            const body: CompanyUpdateV2 = { name: 'Escuela Actualizada' };
            (mockedApi.put as any).mockResolvedValue({ data: { ...companyFull, name: 'Escuela Actualizada' } });

            const result = await updateCompany('c-1', body);

            expect(mockedApi.put).toHaveBeenCalledWith('/v2/companies/c-1', { name: 'Escuela Actualizada' });
            expect(result.name).toBe('Escuela Actualizada');
        });

        it('sends reason as audit field in the body', async () => {
            const body: CompanyUpdateV2 = { is_active: false, reason: 'Impago' };
            (mockedApi.put as any).mockResolvedValue({ data: { ...companyFull, is_active: false } });

            const result = await updateCompany('c-1', body);

            expect(mockedApi.put).toHaveBeenCalledWith('/v2/companies/c-1', { is_active: false, reason: 'Impago' });
            expect(result.is_active).toBe(false);
        });

        it('does not send camelCase keys in the body', async () => {
            const body: CompanyUpdateV2 = { is_managed: false, tax_config: { iva: 10 } };
            (mockedApi.put as any).mockResolvedValue({ data: companyFull });

            await updateCompany('c-1', body);

            const sentBody = (mockedApi.put as any).mock.calls[0][1];
            expect(sentBody).not.toHaveProperty('isManaged');
            expect(sentBody).not.toHaveProperty('taxConfig');
            expect(sentBody).not.toHaveProperty('isActive');
        });
    });

    describe('deleteCompany', () => {
        it('DELETE /v2/companies/:id and returns undefined', async () => {
            (mockedApi.delete as any).mockResolvedValue({ data: undefined });

            const result = await deleteCompany('c-1');

            expect(mockedApi.delete).toHaveBeenCalledWith('/v2/companies/c-1');
            expect(result).toBeUndefined();
        });
    });

    describe('listMyCompanies', () => {
        it('GET /v2/me/companies and returns data', async () => {
            (mockedApi.get as any).mockResolvedValue({ data: [{ id: 'c-1' }] });

            const result = await listMyCompanies();

            expect(mockedApi.get).toHaveBeenCalledWith('/v2/me/companies');
            expect(result).toEqual([{ id: 'c-1' }]);
        });
    });

    describe('listUserCompanies', () => {
        it('GET /v2/users/:userId/companies and returns data', async () => {
            (mockedApi.get as any).mockResolvedValue({ data: [{ id: 'c-1' }, { id: 'c-2' }] });

            const result = await listUserCompanies('u-1');

            expect(mockedApi.get).toHaveBeenCalledWith('/v2/users/u-1/companies');
            expect(result).toHaveLength(2);
        });
    });
});
