import { S3 } from 'aws-sdk';
import {
    Organization,
    Domain,
    Vulnerability,
    connectToDatabase
  } from '../models';
import { CommandOptions } from './ecs-client';
import S3Client from './s3-client';
import stream from 'stream';
import * as tar from 'tar';
import * as fs from 'fs';

const LOCAL_DIRECTORY = './extracted_files/';

// Function to extract the .tbz file
async function extractTBZFile(data: Buffer) {
    try {
        console.log(data)
      // Create the local directory if it doesn't exist
      if (!fs.existsSync(LOCAL_DIRECTORY)) {
        fs.mkdirSync(LOCAL_DIRECTORY);
      }
  
      // Write the downloaded data to a temporary file
      const tempFilePath = `${LOCAL_DIRECTORY}/temp.tbz`;
      fs.writeFileSync(tempFilePath, data);

      fs.readdir(LOCAL_DIRECTORY, function (err, files) {
        //handling error
        if (err) {
            return console.log('Unable to scan directory: ' + err);
        } 
        //listing all files using forEach
        files.forEach(function (file) {
            // Do whatever you want to do with the file
            console.log(file); 
        });
    });
  
      // Extract the .tbz file
      await tar.x({
        file: tempFilePath,
        cwd: LOCAL_DIRECTORY,
        sync: true,
        strip: 1,
        onwarn: (message) => console.warn(message)
      });
  
      // Delete the temporary file
      fs.unlinkSync(tempFilePath);
    } catch (error) {
      console.error("Error extracting .tbz file:", error);
      throw error;
    }
  }

export const handler = async (commandOptions: CommandOptions) => {
    try{
        console.log('1');
        const client = new S3Client();
        console.log('2');
        console.log('2');
        // const extract = tarStream.extract();
        console.log('3');
        const fileData = await client.pull_daily_vs("cyhy_extract_2024-04-08T000000+0000.tbz",)
        console.log('4');
        if (!fileData) {
            throw new Error('Failed to download file from S3');
          }
        console.log('5');
        await extractTBZFile(fileData);
        console.log('6')
        try {
            // List the files in the extracted directory
            const files = fs.readdirSync(LOCAL_DIRECTORY);
        
            // Iterate through each file
            for (const file of files) {
              // Perform some action on each file, for example, logging its name
              console.log('Processing file:', file);
              // Perform your action here
            }
          } catch (error) {
            console.error("Error iterating through extracted files:", error);
            throw error;
          }
    }
    catch (e) {
        console.error('Unknown failure.');
        console.error(e);
  }
    

}

