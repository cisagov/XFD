import { Handler } from 'aws-lambda';
import { connectToDatabase, User } from '../models';
import ESClient from '../tasks/es-client';
const AWS = require('aws-sdk');
const s3 = new AWS.S3({ region: 'us-gov-east-1' });

export const handler: Handler = async (event) => {
  if (event.mode === 'db') {
    const connection = await connectToDatabase(true);
    const res = await connection.query(event.query);
    console.log(res);
    const params = {
      Bucket: 'cisa-crossfeed-prod-exports', // replace with your bucket name
      Key: 'bastion_output.json', // the file name you want to save as
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
  } else {
    console.log('Mode not found: ' + event.mode);
  }
};
