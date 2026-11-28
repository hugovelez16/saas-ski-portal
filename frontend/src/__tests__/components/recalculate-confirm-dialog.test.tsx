import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { RecalculateConfirmDialog } from '@/components/work-log/recalculate-confirm-dialog';
import type { WorkLogRecalculatePreview } from '@/lib/types';

const basePreview: WorkLogRecalculatePreview = {
    workLogId: 'wl-1',
    currentNetAmount: 40.0,
    currentGrossAmount: 47.06,
    currentDuration: 2,
    newNetAmount: 60.0,
    newGrossAmount: 70.59,
    newDuration: 2,
    applyToGroup: false,
    groupCount: 1,
};

describe('RecalculateConfirmDialog', () => {
    it('muestra el importe actual frente al nuevo en modo recálculo', () => {
        render(
            <RecalculateConfirmDialog
                open={true}
                preview={basePreview}
                mode="recalculate"
                onConfirm={vi.fn()}
                onCancel={vi.fn()}
            />
        );

        expect(screen.getByText('Recalcular con tarifa vigente')).toBeInTheDocument();
        expect(screen.getByText('Importe actual')).toBeInTheDocument();
        expect(screen.getByText('Nuevo importe')).toBeInTheDocument();
        expect(screen.getByText(/40,00/)).toBeInTheDocument();
        expect(screen.getByText(/60,00/)).toBeInTheDocument();
    });

    it('muestra el titulo de cambio de tipo y los totales del grupo cuando aplica', () => {
        render(
            <RecalculateConfirmDialog
                open={true}
                preview={{
                    ...basePreview,
                    applyToGroup: true,
                    groupCount: 3,
                    currentGroupNetAmount: 120.0,
                    currentGroupGrossAmount: 141.18,
                    newGroupNetAmount: 180.0,
                    newGroupGrossAmount: 211.77,
                }}
                mode="type_change"
                onConfirm={vi.fn()}
                onCancel={vi.fn()}
            />
        );

        expect(screen.getByText('Confirmar cambio de tipo')).toBeInTheDocument();
        expect(screen.getByText('Grupo actual (3 turnos)')).toBeInTheDocument();
        expect(screen.getByText(/120,00/)).toBeInTheDocument();
        expect(screen.getByText(/180,00/)).toBeInTheDocument();
    });

    it('ejecuta onConfirm y onCancel desde los botones', () => {
        const onConfirm = vi.fn();
        const onCancel = vi.fn();
        render(
            <RecalculateConfirmDialog
                open={true}
                preview={basePreview}
                mode="recalculate"
                onConfirm={onConfirm}
                onCancel={onCancel}
            />
        );

        fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
        expect(onCancel).toHaveBeenCalledTimes(1);

        fireEvent.click(screen.getByRole('button', { name: 'Confirmar y guardar' }));
        expect(onConfirm).toHaveBeenCalledTimes(1);
    });
});
