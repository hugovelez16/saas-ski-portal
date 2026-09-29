import { Money } from '../value-objects/Money';

export interface CalculationLine {
  type: 'income' | 'extra' | 'subtotal' | 'tax' | 'total';
  label: string;
  value: number;
  code?: string;
}

export interface CalculationSnapshot {
  version?: string;
  lines: CalculationLine[];
  metadata?: Record<string, unknown>;
}

export interface WorkLogProps {
  id: string;
  userId: string;
  companyId: string;
  type: string;
  startDate: string;
  endDate?: string | null;
  startTime?: string | null;
  endTime?: string | null;
  durationHours?: number | null;
  description?: string | null;
  grossAmount: Money;
  netAmount: Money;
  extraData?: Record<string, unknown>;
  calculationSnapshot?: CalculationSnapshot | null;
  createdAt?: string;
  updatedAt?: string;
}

export class WorkLog {
  readonly id: string;
  readonly userId: string;
  readonly companyId: string;
  readonly type: string;
  readonly startDate: string;
  readonly endDate?: string | null;
  readonly startTime?: string | null;
  readonly endTime?: string | null;
  readonly durationHours?: number | null;
  readonly description?: string | null;
  readonly grossAmount: Money;
  readonly netAmount: Money;
  readonly extraData: Record<string, unknown>;
  readonly calculationSnapshot?: CalculationSnapshot | null;
  readonly createdAt?: string;
  readonly updatedAt?: string;

  constructor(props: WorkLogProps) {
    this.id = props.id;
    this.userId = props.userId;
    this.companyId = props.companyId;
    this.type = props.type;
    this.startDate = props.startDate;
    this.endDate = props.endDate;
    this.startTime = props.startTime;
    this.endTime = props.endTime;
    this.durationHours = props.durationHours;
    this.description = props.description;
    this.grossAmount = props.grossAmount;
    this.netAmount = props.netAmount;
    this.extraData = props.extraData || {};
    this.calculationSnapshot = props.calculationSnapshot;
    this.createdAt = props.createdAt;
    this.updatedAt = props.updatedAt;
  }

  get groupId(): string | undefined {
    return this.extraData['group_id'] as string | undefined;
  }
}
