import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { WorklogDefinitionBuilder } from '@/components/admin/worklog-definition-builder';

describe('WorklogDefinitionBuilder', () => {
    it('emite solo unit y nunca is_range al guardar', () => {
        const onSave = vi.fn();
        const initialValue = {
            clase: { label: 'Clase', unit: 'days', fields: [], options: [] },
        };

        render(<WorklogDefinitionBuilder initialValue={initialValue} onSave={onSave} />);
        fireEvent.click(screen.getByRole('button', { name: /guardar json/i }));

        expect(onSave).toHaveBeenCalledTimes(1);
        const payload = onSave.mock.calls[0][0];
        expect(payload.clase.unit).toBe('days');
        expect(payload.clase).not.toHaveProperty('is_range');
    });

    it('descarta is_range heredado de una definicion antigua', () => {
        const onSave = vi.fn();
        const initialValue = {
            curso: { label: 'Curso', is_range: true, fields: [], options: [] },
        };

        render(<WorklogDefinitionBuilder initialValue={initialValue} onSave={onSave} />);
        fireEvent.click(screen.getByRole('button', { name: /guardar json/i }));

        const payload = onSave.mock.calls[0][0];
        expect(payload.curso).not.toHaveProperty('is_range');
        expect(payload.curso.unit).toBe('hours');
    });

    it('un tipo nuevo se guarda con unit hours y sin is_range', () => {
        const onSave = vi.fn();

        render(<WorklogDefinitionBuilder initialValue={{}} onSave={onSave} />);
        fireEvent.click(screen.getByRole('button', { name: /añadir tipo de turno/i }));
        fireEvent.click(screen.getByRole('button', { name: /guardar json/i }));

        const payload = onSave.mock.calls[0][0];
        const [key] = Object.keys(payload);
        expect(key).toBe('nuevo_turno_1');
        expect(payload[key].unit).toBe('hours');
        expect(payload[key]).not.toHaveProperty('is_range');
    });
});
