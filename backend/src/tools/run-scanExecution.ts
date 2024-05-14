// Script to execute the scanExecution function
import { handler as scanExecution } from '../tasks/scanExecution';
const amqp = require('amqplib');

async function localScanExecution(scan_type, desired_count, apiKeyList = '') {
  console.log('Starting...');
  const payload = {
    scanType: scan_type,
    desiredCount: desired_count,
    apiKeyList: apiKeyList
  };
  scanExecution(payload, {} as any, () => null);
}

async function sendMessageToQueue(message, queue) {
  const connection = await amqp.connect('amqp://rabbitmq');
  const channel = await connection.createChannel();

  await channel.assertQueue(queue, { durable: true });

  // Simulate sending a message to the queue
  channel.sendToQueue(queue, Buffer.from(JSON.stringify(message)), {
    persistent: true
  });

  console.log('Message sent:', message);

  setTimeout(() => {
    connection.close();
  }, 500);
}

// Simulate sending a message
const SCAN_TYPE = 'dnstwist';
const DESIRED_COUNT = 1;
const ORG_LIST = ['DHS', 'DOI'];
const QUEUE = `staging-${SCAN_TYPE}-queue`;
const API_KEY_LIST = '';

for (const org of ORG_LIST) {
  const message = {
    scriptType: SCAN_TYPE,
    org: org
  };
  sendMessageToQueue(message, QUEUE);
}

localScanExecution(SCAN_TYPE, DESIRED_COUNT, API_KEY_LIST);
