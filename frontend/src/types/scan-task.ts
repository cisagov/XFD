import { Scan } from './scan';

export interface ScanTask {
  id: string;
  status: string;
  type: string;
  input: string;
  output: string;
  created_at: string;
  started_at: string;
  requested_at: string;
  finished_at: string;
  scan: Scan;
  fargate_task_arn: string;
  concurrency_index: Int16Array;
}
