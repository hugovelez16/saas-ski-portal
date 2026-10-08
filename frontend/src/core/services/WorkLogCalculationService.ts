import { differenceInCalendarDays, parseISO, isSameMonth, format } from 'date-fns';
import { WorkLog } from '../entities/WorkLog';

export interface MonthlyStatsResult {
  totalEarnings: number;
  totalDaysWorked: number;
  tutorialDays: number;
  particularHours: number;
}

export class WorkLogCalculationService {
  /**
   * Calcula metricas mensuales agregadas a partir de una coleccion de WorkLogs.
   * Sin coeficientes magicos ni dependencias del framework UI.
   */
  static calculateMonthlyStats(workLogs: WorkLog[], targetMonth: Date): MonthlyStatsResult {
    let totalEarnings = 0;
    let particularHours = 0;
    let tutorialDays = 0;
    const uniqueDays = new Set<string>();

    for (const entry of workLogs) {
      const netAmount = entry.netAmount.amount;

      if (entry.type === 'particular' && entry.startDate) {
        const entryDate = parseISO(entry.startDate);
        if (isSameMonth(entryDate, targetMonth)) {
          totalEarnings += netAmount;
          particularHours += entry.durationHours || 0;
          uniqueDays.add(entry.startDate);
        }
      } else if (entry.type === 'tutorial' && entry.startDate && entry.endDate) {
        const start = parseISO(entry.startDate);
        const end = parseISO(entry.endDate);
        const duration = differenceInCalendarDays(end, start) + 1;
        const dailyEarning = duration > 0 ? netAmount / duration : 0;

        for (let dt = new Date(start); dt <= end; dt.setDate(dt.getDate() + 1)) {
          if (isSameMonth(dt, targetMonth)) {
            totalEarnings += dailyEarning;
            tutorialDays += 1;
            const dayStr = format(dt, 'yyyy-MM-dd');
            uniqueDays.add(dayStr);
          }
        }
      } else if (entry.startDate) {
        const entryDate = parseISO(entry.startDate);
        if (isSameMonth(entryDate, targetMonth)) {
          totalEarnings += netAmount;
          uniqueDays.add(entry.startDate);
        }
      }
    }

    return {
      totalEarnings: Math.round(totalEarnings * 100) / 100,
      totalDaysWorked: uniqueDays.size,
      tutorialDays,
      particularHours: Math.round(particularHours * 100) / 100,
    };
  }
}
