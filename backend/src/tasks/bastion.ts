import { Handler } from 'aws-lambda';
import { connectToDatabase, User, connectToDatalake } from '../models';
import ESClient from '../tasks/es-client';
const AWS = require('aws-sdk');
const s3 = new AWS.S3({ region: 'us-gov-east-1' });
import { handler as searchSyncOrgs } from './search-sync-orgs';

export const handler: Handler = async (event) => {
  if (event.mode === 'db') {
    const connection = await connectToDatabase(true);
    const res = await connection.query(event.query);
    console.log(res);
    const params = {
      Bucket: 'cisa-crossfeed-prod-exports',
      Key: 'bastion_output.json',
      Body: JSON.stringify(res),
      ContentType: 'application/json'
    };
    await s3.putObject(params).promise();
  } else if (event.mode === 'mdl') {
    const connection = await connectToDatalake(true);
    const res = await connection.query(event.query);
    console.log(res);
    const params = {
      Bucket: 'cisa-crossfeed-prod-exports',
      Key: 'bastion_output.json',
      Body: JSON.stringify(res),
      ContentType: 'application/json'
    };
    await s3.putObject(params).promise();
  } else if (event.mode === 'es') {
    if (event.query === 'delete') {
      const client = new ESClient();
      await client.deleteAll();
      console.log('Index successfully deleted');
    } else {
      console.log('Query not found: ' + event.query);
    }
    if (event.query === 'update') {
      const connection = await connectToDatabase(true);
      const client = new ESClient();
      await searchSyncOrgs();
      await client.syncDomainsIndex();
      await client.syncOrganizationsIndex();
      console.log('Index successfully updated');
    } else {
      console.log('Query not found: ' + event.query);
    }
  } else {
    console.log('Mode not found: ' + event.mode);
  }
};
