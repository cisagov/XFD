import { Log } from '../models';
import { wrapHandler } from './helpers';

export const list = wrapHandler(async () => {
  const logs = await Log.find();
  return {
    statusCode: 200,
    body: JSON.stringify({
      result: logs,
      count: logs.length
    })
  };
});
