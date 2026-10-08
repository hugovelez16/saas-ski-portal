import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Utility function to merge Tailwind CSS classes conditionally.
 * Combines `clsx` for conditional classes and `tailwind-merge` to resolve conflicts.
 * 
 * @param inputs - Class names or conditional class objects.
 * @returns Merged class string.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
  }).format(amount)
}

/**
 * Utility function to format tax and deduction rates as clean percentages.
 * Handles IEEE-754 floating point imprecision (e.g., 0.0648 * 100 -> 6.48%).
 *
 * @param rate - Rate as decimal (e.g. 0.0648) or whole percentage (e.g. 6.48).
 * @returns Formatted percentage string (e.g. "6.48%").
 */
export function formatPercentage(rate: number | null | undefined): string {
  if (rate == null || isNaN(rate)) return "0%"
  const pct = Math.abs(rate) <= 1 && rate !== 0 ? rate * 100 : rate
  const rounded = Number(Math.round(Number(`${pct}e2`)) + 'e-2')
  return `${rounded}%`
}

