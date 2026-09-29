import { WorkLog } from '../entities/WorkLog';

export interface WorkLogFilterOptions {
  companyId?: string;
  userId?: string;
  startDate?: string;
  endDate?: string;
  type?: string;
  skip?: number;
  limit?: number;
}

export interface IWorkLogRepository {
  getById(id: string): Promise<WorkLog | null>;
  list(filter?: WorkLogFilterOptions): Promise<WorkLog[]>;
  save(workLog: Partial<WorkLog>): Promise<WorkLog>;
  delete(id: string): Promise<boolean>;
}
