import { IHttpClient } from '../../core/ports/IHttpClient';
import { IWorkLogRepository, WorkLogFilterOptions } from '../../core/ports/IWorkLogRepository';
import { WorkLog } from '../../core/entities/WorkLog';
import { WorkLogMapper, ApiWorkLogDTO } from '../../application/mappers/WorkLogMapper';

export class ApiWorkLogRepository implements IWorkLogRepository {
  constructor(private httpClient: IHttpClient) {}

  async getById(id: string): Promise<WorkLog | null> {
    try {
      const dto = await this.httpClient.get<ApiWorkLogDTO>(`/work-logs/${id}`);
      return dto ? WorkLogMapper.toDomain(dto) : null;
    } catch {
      return null;
    }
  }

  async list(filter?: WorkLogFilterOptions): Promise<WorkLog[]> {
    const params: Record<string, unknown> = {};
    if (filter?.companyId) params['company_id'] = filter.companyId;
    if (filter?.userId) params['user_id'] = filter.userId;
    if (filter?.startDate) params['start_date'] = filter.startDate;
    if (filter?.endDate) params['end_date'] = filter.endDate;
    if (filter?.type) params['type'] = filter.type;
    if (filter?.skip !== undefined) params['skip'] = filter.skip;
    if (filter?.limit !== undefined) params['limit'] = filter.limit;

    const dtos = await this.httpClient.get<ApiWorkLogDTO[]>('/work-logs', { params });
    return Array.isArray(dtos) ? dtos.map(WorkLogMapper.toDomain) : [];
  }

  async save(workLog: Partial<WorkLog>): Promise<WorkLog> {
    const payload = WorkLogMapper.toDTO(workLog);
    if (workLog.id) {
      const updated = await this.httpClient.put<ApiWorkLogDTO>(`/work-logs/${workLog.id}`, payload);
      return WorkLogMapper.toDomain(updated);
    } else {
      const created = await this.httpClient.post<ApiWorkLogDTO>('/work-logs', payload);
      return WorkLogMapper.toDomain(created);
    }
  }

  async delete(id: string): Promise<boolean> {
    try {
      await this.httpClient.delete(`/work-logs/${id}`);
      return true;
    } catch {
      return false;
    }
  }
}
