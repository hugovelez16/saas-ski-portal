import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { WorklogDefinitionBuilder } from '@/components/admin/worklog-definition-builder';

describe('WorklogDefinitionBuilder', () => {
    it('emite solo unit, options e is_active y nunca is_range ni fields al guardar', () => {
        const onSave = vi.fn();
        const initialValue = {
            clase: { label: 'Clase', unit: 'days', fields: ['legacy'], options: [], is_active: true },
        };

        render(<WorklogDefinitionBuilder initialValue={initialValue} onSave={onSave} />);
        fireEvent.click(screen.getByRole('button', { name: /guardar tipos de turno/i }));

        expect(onSave).toHaveBeenCalledTimes(1);
        const payload = onSave.mock.calls[0][0];
        expect(payload.clase).toEqual({
            label: 'Clase',
            unit: 'days',
            options: [],
            is_active: true,
        });
        expect(payload.clase).not.toHaveProperty('is_range');
        expect(payload.clase).not.toHaveProperty('fields');
    });

    it('descarta is_range heredado de una definicion antigua', () => {
        const onSave = vi.fn();
        const initialValue = {
            curso: { label: 'Curso', is_range: true, options: [] },
        };

        render(<WorklogDefinitionBuilder initialValue={initialValue} onSave={onSave} />);
        fireEvent.click(screen.getByRole('button', { name: /guardar tipos de turno/i }));

        const payload = onSave.mock.calls[0][0];
        expect(payload.curso).not.toHaveProperty('is_range');
        expect(payload.curso.unit).toBe('hours');
    });

    it('un tipo nuevo se guarda con unit hours, is_active true y sin is_range', () => {
        const onSave = vi.fn();

        render(<WorklogDefinitionBuilder initialValue={{}} onSave={onSave} />);
        fireEvent.click(screen.getByRole('button', { name: /añadir tipo de turno/i }));
        fireEvent.click(screen.getByRole('button', { name: /guardar tipos de turno/i }));

        const payload = onSave.mock.calls[0][0];
        const [key] = Object.keys(payload);
        expect(key).toBe('nuevo_turno_1');
        expect(payload[key].unit).toBe('hours');
        expect(payload[key].is_active).toBe(true);
        expect(payload[key]).not.toHaveProperty('is_range');
    });

    it('permite desactivar un tipo existente sin borrarlo', () => {
        const onSave = vi.fn();
        render(
            <WorklogDefinitionBuilder
                initialValue={{ particular: { label: 'Particular', unit: 'hours', options: [], is_active: true } }}
                usage={{ particular: { work_logs_count: 3, member_rates_count: 1 } }}
                onSave={onSave}
            />
        );

        const activeSwitch = screen.getByLabelText(/activar o desactivar particular/i);
        fireEvent.click(activeSwitch);
        fireEvent.click(screen.getByRole('button', { name: /guardar tipos de turno/i }));

        const payload = onSave.mock.calls[0][0];
        expect(payload.particular.is_active).toBe(false);
        expect(screen.getByRole('button', { name: /eliminar tipo particular/i })).toBeDisabled();
    });

    it('pide confirmacion antes de eliminar un tipo sin turnos avisando sobre tarifas asociadas', () => {
        const onSave = vi.fn();
        render(
            <WorklogDefinitionBuilder
                initialValue={{
                    particular: { label: 'Particular', unit: 'hours', options: [], is_active: true },
                    evento: { label: 'Evento', unit: 'fixed', options: [], is_active: true },
                }}
                usage={{
                    particular: { work_logs_count: 1, member_rates_count: 1 },
                    evento: { work_logs_count: 0, member_rates_count: 2 },
                }}
                onSave={onSave}
            />
        );

        fireEvent.click(screen.getByRole('button', { name: /eliminar tipo evento/i }));
        expect(screen.getByText(/tarifas asociadas/i)).toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: /eliminar y limpiar tarifas/i }));
        fireEvent.click(screen.getByRole('button', { name: /guardar tipos de turno/i }));

        const payload = onSave.mock.calls[0][0];
        expect(payload).not.toHaveProperty('evento');
        expect(payload).toHaveProperty('particular');
    });
});
