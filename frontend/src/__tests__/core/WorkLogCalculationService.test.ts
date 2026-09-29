import { describe, it, expect } from 'vitest';
import { WorkLogCalculationService } from '../../core/services/WorkLogCalculationService';
import { WorkLog } from '../../core/entities/WorkLog';
import { Money } from '../../core/value-objects/Money';

describe('WorkLogCalculationService (Frontend Core)', () => {
  it('calculates monthly stats accurately for mixed work logs', () => {
    const march2026 = new Date(2026, 2, 15); // Marzo 2026

    const logs: WorkLog[] = [
      new WorkLog({
        id: '1',
        userId: 'u1',
        companyId: 'c1',
        type: 'particular',
        startDate: '2026-03-10',
        durationHours: 3.5,
        grossAmount: new Money(100),
        netAmount: new Money(85),
      }),
      new WorkLog({
        id: '2',
        userId: 'u1',
        companyId: 'c1',
        type: 'tutorial',
        startDate: '2026-03-20',
        endDate: '2026-03-22', // 3 dias
        grossAmount: new Money(300),
        netAmount: new Money(255), // 85 EUR/dia
      }),
      new WorkLog({
        id: '3',
        userId: 'u1',
        companyId: 'c1',
        type: 'particular',
        startDate: '2026-02-28', // Febrero - debe ser ignorado
        durationHours: 2,
        grossAmount: new Money(60),
        netAmount: new Money(50),
      }),
    ];

    const stats = WorkLogCalculationService.calculateMonthlyStats(logs, march2026);

    expect(stats.totalEarnings).toBe(85 + 255);
    expect(stats.particularHours).toBe(3.5);
    expect(stats.tutorialDays).toBe(3);
    expect(stats.totalDaysWorked).toBe(4); // 1 particular + 3 tutorial
  });
});
