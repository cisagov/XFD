// Script to execute the scanExecution function
import { handler as scanExecution } from '../tasks/scanExecution';

async function localScanExecution() {
  console.log('Starting...');
  const payload = { scanType: 'dnstwist', desiredCount: 3 };
  scanExecution(payload, {} as any, () => null);
}

localScanExecution();
