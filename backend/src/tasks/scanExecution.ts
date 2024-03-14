import { Handler } from 'aws-lambda';
import * as AWS from 'aws-sdk';
import { integer } from 'aws-sdk/clients/cloudfront';

const ecs = new AWS.ECS();
let docker;
if (process.env.IS_LOCAL) {
  docker = require('dockerode');
}

const toSnakeCase = (input) => input.replace(/ /g, '-');

async function startDesiredTasks(
  scanType: string,
  desiredCount: integer,
  queueUrl: string
) {
  try {
    // ECS can only start 10 tasks at a time. Split up into batches
    const batchSize = 10;
    let remainingCount = desiredCount;
    while (remainingCount > 0) {
      const currentBatchCount = Math.min(remainingCount, batchSize);

      if (process.env.IS_LOCAL) {
        // If running locally, use RabbitMQ and Docker instead of SQS and ECS
        console.log('Starting local containers');
        await startLocalContainers(currentBatchCount, scanType, queueUrl);
      } else {
        await ecs
          .runTask({
            cluster: process.env.PE_FARGATE_CLUSTER_NAME!,
            taskDefinition: process.env.PE_FARGATE_TASK_DEFINITION_NAME!,
            networkConfiguration: {
              awsvpcConfiguration: {
                assignPublicIp: 'ENABLED',
                securityGroups: [process.env.FARGATE_SG_ID!],
                subnets: [process.env.FARGATE_SUBNET_ID!]
              }
            },
            platformVersion: '1.4.0',
            launchType: 'FARGATE',
            count: currentBatchCount,
            overrides: {
              containerOverrides: [
                {
                  name: 'main',
                  environment: [
                    {
                      name: 'SERVICE_TYPE',
                      value: scanType
                    },
                    {
                      name: 'SERVICE_QUEUE_URL',
                      value: queueUrl
                    }
                  ]
                }
              ]
            }
          })
          .promise();
      }
      console.log('Tasks started:', currentBatchCount);
      remainingCount -= currentBatchCount;
    }
  } catch (error) {
    console.error('Error starting tasks:', error);
    throw error;
  }
}

async function startLocalContainers(
  count: number,
  scanType: string,
  queueUrl: string
) {
  // Start 'count' number of local Docker containers
  for (let i = 0; i < count; i++) {
    try {
      const containerName = toSnakeCase(
        `crossfeed_worker_${scanType}_${i}_` +
          Math.floor(Math.random() * 10000000)
      );
      const container = await docker!.createContainer({
        // We need to create unique container names to avoid conflicts.
        name: containerName,
        Image: 'pe-worker',
        HostConfig: {
          // In order to use the host name "db" to access the database from the
          // crossfeed-worker image, we must launch the Docker container with
          // the Crossfeed backend network.
          NetworkMode: 'crossfeed_backend',
          Memory: 4000000000 // Limit memory to 4 GB. We do this locally to better emulate fargate memory conditions. TODO: In the future, we could read the exact memory from SCAN_SCHEMA to better emulate memory requirements for each scan.
        },
        Env: [
          `DB_DIALECT=${process.env.DB_DIALECT}`,
          `DB_HOST=${process.env.DB_HOST}`,
          `IS_LOCAL=true`,
          `DB_PORT=${process.env.DB_PORT}`,
          `DB_NAME=${process.env.DB_NAME}`,
          `DB_USERNAME=${process.env.DB_USERNAME}`,
          `DB_PASSWORD=${process.env.DB_PASSWORD}`,
          `PE_DB_NAME=${process.env.PE_DB_NAME}`,
          `PE_DB_USERNAME=${process.env.PE_DB_USERNAME}`,
          `PE_DB_PASSWORD=${process.env.PE_DB_PASSWORD}`,
          `CENSYS_API_ID=${process.env.CENSYS_API_ID}`,
          `CENSYS_API_SECRET=${process.env.CENSYS_API_SECRET}`,
          `WORKER_USER_AGENT=${process.env.WORKER_USER_AGENT}`,
          `SHODAN_API_KEY=${process.env.SHODAN_API_KEY}`,
          `HIBP_API_KEY=${process.env.HIBP_API_KEY}`,
          `SIXGILL_CLIENT_ID=${process.env.SIXGILL_CLIENT_ID}`,
          `SIXGILL_CLIENT_SECRET=${process.env.SIXGILL_CLIENT_SECRET}`,
          `INTELX_API_KEY=${process.env.INTELX_API_KEY}`,
          `PE_SHODAN_API_KEYS=${process.env.PE_SHODAN_API_KEYS}`,
          `WORKER_SIGNATURE_PUBLIC_KEY=${process.env.WORKER_SIGNATURE_PUBLIC_KEY}`,
          `WORKER_SIGNATURE_PRIVATE_KEY=${process.env.WORKER_SIGNATURE_PRIVATE_KEY}`,
          `ELASTICSEARCH_ENDPOINT=${process.env.ELASTICSEARCH_ENDPOINT}`,
          `AWS_ACCESS_KEY_ID=${process.env.AWS_ACCESS_KEY_ID}`,
          `AWS_SECRET_ACCESS_KEY=${process.env.AWS_SECRET_ACCESS_KEY}`,
          `AWS_REGION=${process.env.AWS_REGION}`,
          `LG_API_KEY=${process.env.LG_API_KEY}`,
          `LG_WORKSPACE_NAME=${process.env.LG_WORKSPACE_NAME}`,
          `SERVICE_QUEUE_URL=${queueUrl}`,
          `SERVICE_TYPE=${scanType}`
        ]
      } as any);
      await container.start();
      console.log(`Done starting container ${i}`);
    } catch (e) {
      console.error(e);
    }
  }
}

export const handler: Handler = async (event) => {
  let desiredCount: integer;
  let scanType: string;
  if (event.desiredCount) {
    desiredCount = event.desiredCount;
  } else {
    console.log('Desired count not found. Setting to 1.');
    desiredCount = 1;
  }

  if (event.scanType) {
    scanType = event.scanType;
  } else {
    console.error('scanType must be provided.');
    return 'Failed no scanType';
  }

  try {
    if (scanType === 'shodan') {
      await startDesiredTasks(
        scanType,
        desiredCount,
        process.env.SHODAN_QUEUE_URL!
      );
    } else if (scanType === 'dnstwist') {
      desiredCount = 30;
      await startDesiredTasks(
        scanType,
        desiredCount,
        process.env.DNSTWIST_QUEUE_URL!
      );
    } else if (scanType === 'hibp') {
      desiredCount = 20;
      await startDesiredTasks(
        scanType,
        desiredCount,
        process.env.HIBP_QUEUE_URL!
      );
    } else if (scanType === 'intelx') {
      desiredCount = 10;
      await startDesiredTasks(
        scanType,
        desiredCount,
        process.env.INTELX_QUEUE_URL!
      );
    } else if (scanType === 'cybersixgill') {
      desiredCount = 10;
      await startDesiredTasks(
        scanType,
        desiredCount,
        process.env.CYBERSIXGILL_QUEUE_URL!
      );
    } else {
      console.log(
        'Shodan, DNSTwist, HIBP, and Cybersixgill are the only script types available right now.'
      );
    }
  } catch (error) {
    console.error(error);
    return {
      statusCode: 500,
      body: JSON.stringify(error)
    };
  }
};
