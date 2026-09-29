import { WorkLog } from '../../core/entities/WorkLog';
import { Money } from '../../core/value-objects/Money';

export interface ApiWorkLogDTO {
  id: string;
  user_id: string;
  company_id: string;
  type: string;
  start_date: string;
  end_date?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  duration?: number | null;
  duration_hours?: number | null;
  description?: string | null;
  gross_amount?: number | null;
  net_amount?: number | null;
  extra_data?: Record<string, unknown>;
  calculation_snapshot?: Record<string, unknown> | null;
  created_at?: string;
  updated_at?: string;
}

export class WorkLogMapper {
  static toDomain(dto: ApiWorkLogDTO): WorkLog {
    const rawDuration = dto.duration_hours !== undefined && dto.duration_hours !== null ? dto.duration_hours : dto.duration;
    
    return new WorkLog({
      id: dto.id,
      userId: dto.user_id,
      companyId: dto.company_id,
      type: dto.type,
      startDate: dto.start_date,
      endDate: dto.end_date,
      startTime: dto.start_time,
      endTime: dto.end_time,
      durationHours: rawDuration !== undefined && rawDuration !== null ? Number(rawDuration) : null,
      description: dto.description,
      grossAmount: new Money(dto.gross_amount),
      netAmount: new Money(dto.net_amount),
      extraData: dto.extra_data || {},
      calculationSnapshot: dto.calculation_snapshot as any,
      createdAt: dto.created_at,
      updatedAt: dto.updated_at,
    });
  }

  static toDTO(domain: Partial<WorkLog>): Partial<ApiWorkLogDTO> {
    return {
      id: domain.id,
      user_id: domain.userId,
      company_id: domain.companyId,
      type: domain.type,
      start_date: domain.startDate,
      end_date: domain.endDate,
      start_time: domain.startTime,
      end_time: domain.endTime,
      duration: domain.durationHours,
      description: domain.description,
      gross_amount: domain.grossAmount ? domain.grossAmount.amount : undefined,
      net_amount: domain.netAmount ? domain.netAmount.amount : undefined,
      extra_data: domain.extraData,
    };
  }
}
