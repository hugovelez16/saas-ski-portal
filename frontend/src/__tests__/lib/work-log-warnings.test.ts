import { describe, it, expect, vi } from 'vitest';
import { notifyWorkLogWarnings } from '@/lib/work-log-warnings';

const warning = (message: string, code = 'OVERLAP') => ({
    code,
    message,
    conflictingLogIds: ['log-1'],
    userId: 'user-1',
});

describe('notifyWorkLogWarnings', () => {
    it('does not call toast when the log has no warnings', () => {
        const toast = vi.fn();

        notifyWorkLogWarnings(toast, { warnings: [] });

        expect(toast).not.toHaveBeenCalled();
    });

    it('does not call toast when warnings is undefined', () => {
        const toast = vi.fn();

        notifyWorkLogWarnings(toast, {});

        expect(toast).not.toHaveBeenCalled();
    });

    it('does not call toast when the log is null or undefined', () => {
        const toast = vi.fn();

        notifyWorkLogWarnings(toast, null);
        notifyWorkLogWarnings(toast, undefined);

        expect(toast).not.toHaveBeenCalled();
    });

    it('shows a single warning with its message', () => {
        const toast = vi.fn();

        notifyWorkLogWarnings(toast, { warnings: [warning('El turno se solapa con otro registro.')] });

        expect(toast).toHaveBeenCalledTimes(1);
        expect(toast).toHaveBeenCalledWith({
            title: 'Aviso',
            description: 'El turno se solapa con otro registro.',
        });
    });

    it('joins several distinct messages with a space', () => {
        const toast = vi.fn();

        notifyWorkLogWarnings(toast, {
            warnings: [
                warning('Primer aviso.', 'OVERLAP'),
                warning('Segundo aviso.', 'INACTIVE_USER'),
            ],
        });

        expect(toast).toHaveBeenCalledWith({
            title: 'Aviso',
            description: 'Primer aviso. Segundo aviso.',
        });
    });

    it('deduplicates repeated messages (bulk creation)', () => {
        const toast = vi.fn();

        notifyWorkLogWarnings(toast, {
            warnings: [
                warning('Se solapa con otro turno.'),
                warning('Se solapa con otro turno.'),
                warning('Otro aviso.', 'INACTIVE_USER'),
                warning('Se solapa con otro turno.'),
            ],
        });

        expect(toast).toHaveBeenCalledTimes(1);
        expect(toast).toHaveBeenCalledWith({
            title: 'Aviso',
            description: 'Se solapa con otro turno. Otro aviso.',
        });
    });

    it('does not throw when toast fails', () => {
        const toast = vi.fn(() => {
            throw new Error('toast error');
        });
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

        expect(() =>
            notifyWorkLogWarnings(toast, { warnings: [warning('Aviso.')] })
        ).not.toThrow();

        consoleSpy.mockRestore();
    });
});
