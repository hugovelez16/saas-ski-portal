import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/lib/api', () => ({
    default: {
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        delete: vi.fn(),
    },
}));

import api from '@/lib/api';
import { setup2fa, activate2fa, disable2fa, resetUser2fa } from '@/lib/api/users';

const mockedApi = vi.mocked(api);

describe('Two-factor API client', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('setup2fa should POST /2fa/setup and return the secret and QR uri', async () => {
        const payload = { secret: 'ABC123', qrCodeUri: 'otpauth://totp/Vesotel:user@vesotel.com?secret=ABC123' };
        (mockedApi.post as any).mockResolvedValue({ data: payload });

        const result = await setup2fa();

        expect(mockedApi.post).toHaveBeenCalledWith('/2fa/setup');
        expect(result).toEqual(payload);
    });

    it('activate2fa should POST /2fa/activate with the code', async () => {
        (mockedApi.post as any).mockResolvedValue({ data: { message: '2FA activated successfully' } });

        const result = await activate2fa('123456');

        expect(mockedApi.post).toHaveBeenCalledWith('/2fa/activate', { code: '123456' });
        expect(result.message).toContain('activated');
    });

    it('disable2fa should POST /2fa/disable with the code', async () => {
        (mockedApi.post as any).mockResolvedValue({ data: { message: '2FA disabled' } });

        const result = await disable2fa('654321');

        expect(mockedApi.post).toHaveBeenCalledWith('/2fa/disable', { code: '654321' });
        expect(result.message).toBe('2FA disabled');
    });

    it('resetUser2fa should POST /users/:id/reset-2fa', async () => {
        (mockedApi.post as any).mockResolvedValue({ data: { message: '2FA reset' } });

        const result = await resetUser2fa('user-1');

        expect(mockedApi.post).toHaveBeenCalledWith('/users/user-1/reset-2fa');
        expect(result.message).toBe('2FA reset');
    });

    it('should propagate API errors', async () => {
        (mockedApi.post as any).mockRejectedValue({ response: { status: 429 } });

        await expect(activate2fa('000000')).rejects.toEqual({ response: { status: 429 } });
    });
});
