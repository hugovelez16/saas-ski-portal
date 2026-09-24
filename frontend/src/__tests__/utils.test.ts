import { describe, it, expect } from 'vitest';
import { cn, formatCurrency } from '../lib/utils';

describe('Utilidades de frontend', () => {
    it('cn combina clases de Tailwind correctamente', () => {
        expect(cn('p-4', 'bg-blue-500')).toBe('p-4 bg-blue-500');
        expect(cn('p-4', false && 'hidden', 'text-white')).toBe('p-4 text-white');
        expect(cn('p-2', 'p-4')).toBe('p-4');
    });

    it('formatCurrency formatea cantidades monetarias en Euros', () => {
        const formatted = formatCurrency(1250.5);
        expect(formatted).toContain('1.250,50');
        expect(formatted).toContain('€');
    });
});
