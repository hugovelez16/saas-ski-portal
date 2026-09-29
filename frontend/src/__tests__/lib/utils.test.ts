import { describe, it, expect } from 'vitest';
import { cn, formatCurrency, formatPercentage } from '@/lib/utils';

describe('cn (class name utility)', () => {
    it('should merge simple class names', () => {
        expect(cn('foo', 'bar')).toBe('foo bar');
    });

    it('should handle conditional classes', () => {
        expect(cn('base', false && 'hidden', 'visible')).toBe('base visible');
    });

    it('should resolve Tailwind conflicts (last wins)', () => {
        // tailwind-merge should keep the last conflicting class
        expect(cn('p-4', 'p-8')).toBe('p-8');
        expect(cn('text-red-500', 'text-blue-500')).toBe('text-blue-500');
    });

    it('should handle undefined and null values', () => {
        expect(cn('foo', undefined, null, 'bar')).toBe('foo bar');
    });

    it('should handle empty inputs', () => {
        expect(cn()).toBe('');
    });

    it('should handle object syntax from clsx', () => {
        expect(cn({ 'bg-red-500': true, 'bg-blue-500': false })).toBe('bg-red-500');
    });
});

describe('formatCurrency', () => {
    it('should format a positive number as EUR', () => {
        const result = formatCurrency(1234.56);
        // jsdom may omit thousand separators; just verify the number and currency
        expect(result).toContain('1234,56');
        expect(result).toContain('€');
    });

    it('should format zero', () => {
        const result = formatCurrency(0);
        expect(result).toContain('0,00');
        expect(result).toContain('€');
    });

    it('should format negative numbers', () => {
        const result = formatCurrency(-50);
        expect(result).toContain('50,00');
        expect(result).toContain('€');
    });

    it('should round to 2 decimal places', () => {
        const result = formatCurrency(99.999);
        expect(result).toContain('100,00');
    });
});

describe('formatPercentage', () => {
    it('should format decimal tax rate without floating point precision issues', () => {
        // 0.0648 * 100 is 6.4799999999999995 in JS
        expect(formatPercentage(0.0648)).toBe('6.48%');
    });

    it('should format standard whole percentage rates', () => {
        expect(formatPercentage(0.15)).toBe('15%');
        expect(formatPercentage(0.21)).toBe('21%');
        expect(formatPercentage(0)).toBe('0%');
    });

    it('should format rates already in 1-100 range', () => {
        expect(formatPercentage(6.48)).toBe('6.48%');
        expect(formatPercentage(15)).toBe('15%');
    });

    it('should handle null and undefined safely', () => {
        expect(formatPercentage(null)).toBe('0%');
        expect(formatPercentage(undefined)).toBe('0%');
        expect(formatPercentage(NaN)).toBe('0%');
    });
});

