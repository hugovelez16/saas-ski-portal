import { describe, it, expect, vi } from 'vitest';
import { WorkLogMapper } from '../../application/mappers/WorkLogMapper';
import { ApiWorkLogRepository } from '../../infrastructure/repositories/ApiWorkLogRepository';
import { IHttpClient } from '../../core/ports/IHttpClient';

describe('WorkLogMapper & ApiWorkLogRepository', () => {
  it('maps API DTO to Domain Entity with Money Value Objects', () => {
    const apiDto = {
      id: 'log-123',
      user_id: 'usr-1',
      company_id: 'comp-1',
      type: 'clase_esqui',
      start_date: '2026-03-15',
      end_date: '2026-03-15',
      start_time: '09:00:00',
      end_time: '11:00:00',
      duration: 2,
      gross_amount: 80.0,
      net_amount: 68.0,
      extra_data: { group_id: 'g-99' },
    };

    const domain = WorkLogMapper.toDomain(apiDto);
    expect(domain.id).toBe('log-123');
    expect(domain.userId).toBe('usr-1');
    expect(domain.grossAmount.amount).toBe(80.0);
    expect(domain.netAmount.amount).toBe(68.0);
    expect(domain.durationHours).toBe(2);
    expect(domain.groupId).toBe('g-99');
  });

  it('ApiWorkLogRepository lists and maps logs via mocked IHttpClient', async () => {
    const mockHttpClient: IHttpClient = {
      get: vi.fn().mockResolvedValue([
        {
          id: 'log-1',
          user_id: 'usr-1',
          company_id: 'comp-1',
          type: 'particular',
          start_date: '2026-03-10',
          duration: 1.5,
          gross_amount: 45.0,
          net_amount: 38.25,
        },
      ]),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
    };

    const repo = new ApiWorkLogRepository(mockHttpClient);
    const logs = await repo.list({ companyId: 'comp-1' });

    expect(logs).toHaveLength(1);
    expect(logs[0].id).toBe('log-1');
    expect(logs[0].grossAmount.amount).toBe(45.0);
    expect(mockHttpClient.get).toHaveBeenCalledWith('/work-logs', {
      params: { company_id: 'comp-1' },
    });
  });
});
