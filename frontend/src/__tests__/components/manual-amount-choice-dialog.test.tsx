import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ManualAmountChoiceDialog } from '@/components/work-log/manual-amount-choice-dialog';

const renderDialog = (overrides: Partial<React.ComponentProps<typeof ManualAmountChoiceDialog>> = {}) => {
    const props = {
        open: true,
        message: 'El turno tiene importe manual.',
        canRecalculate: true,
        onKeep: vi.fn(),
        onRecalculate: vi.fn(),
        onCancel: vi.fn(),
        ...overrides,
    };
    render(<ManualAmountChoiceDialog {...props} />);
    return props;
};

describe('ManualAmountChoiceDialog', () => {
    it('shows the title and the backend message', () => {
        renderDialog();

        expect(screen.getByText('Importe manual')).toBeInTheDocument();
        expect(screen.getByText('El turno tiene importe manual.')).toBeInTheDocument();
    });

    it('shows "Calcular por tarifa" when canRecalculate is true', () => {
        renderDialog({ canRecalculate: true });

        expect(screen.getByRole('button', { name: 'Calcular por tarifa' })).toBeInTheDocument();
    });

    it('hides "Calcular por tarifa" when canRecalculate is false', () => {
        renderDialog({ canRecalculate: false });

        expect(screen.queryByRole('button', { name: 'Calcular por tarifa' })).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Conservar importe' })).toBeInTheDocument();
    });

    it('calls onKeep when "Conservar importe" is clicked', () => {
        const { onKeep, onRecalculate, onCancel } = renderDialog();

        fireEvent.click(screen.getByRole('button', { name: 'Conservar importe' }));

        expect(onKeep).toHaveBeenCalledTimes(1);
        expect(onRecalculate).not.toHaveBeenCalled();
        expect(onCancel).not.toHaveBeenCalled();
    });

    it('calls onRecalculate when "Calcular por tarifa" is clicked', () => {
        const { onKeep, onRecalculate, onCancel } = renderDialog({ canRecalculate: true });

        fireEvent.click(screen.getByRole('button', { name: 'Calcular por tarifa' }));

        expect(onRecalculate).toHaveBeenCalledTimes(1);
        expect(onKeep).not.toHaveBeenCalled();
        expect(onCancel).not.toHaveBeenCalled();
    });

    it('calls onCancel when "Cancelar" is clicked', () => {
        const { onKeep, onRecalculate, onCancel } = renderDialog();

        fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));

        expect(onCancel).toHaveBeenCalledTimes(1);
        expect(onKeep).not.toHaveBeenCalled();
        expect(onRecalculate).not.toHaveBeenCalled();
    });

    it('renders nothing when open is false', () => {
        renderDialog({ open: false });

        expect(screen.queryByText('Importe manual')).not.toBeInTheDocument();
    });
});
