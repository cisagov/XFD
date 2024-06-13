import { IsString, isUUID, IsOptional, IsDateString } from 'class-validator';
import { Notification, connectToDatabase } from '../models';
import { validateBody, wrapHandler, NotFound, Unauthorized } from './helpers';
import { isGlobalWriteAdmin } from './auth';
import S3Client from '../tasks/s3-client';

class NewNotification {
  @IsDateString()
  startDatetime?: string;

  @IsDateString()
  endDatetime?: string;

  @IsString()
  maintenanceType?: string;

  @IsString()
  @IsOptional()
  status: string;

  @IsString()
  @IsOptional()
  message: string;

  @IsString()
  @IsOptional()
  updatedBy: string;
}
/**
 * @swagger
 *
 * /notifications:
 *  post:
 *    description: Create a new notification.
 *    tags:
 *    - Notifications
 */
export const create = wrapHandler(async (event) => {
  if (!isGlobalWriteAdmin(event)) return Unauthorized;
  const body = await validateBody(NewNotification, event.body);
  await connectToDatabase();

  const notification = await Notification.create({
    ...body
  });
  const res = await notification.save();
  return {
    statusCode: 200,
    body: JSON.stringify(res)
  };
});

/**
 * @swagger
 *
 * /notifications/{id}:
 *  delete:
 *    description: Delete a particular notification.
 *    parameters:
 *      - in: path
 *        name: id
 *        description: Notification id
 *    tags:
 *    - Notifications
 */
export const del = wrapHandler(async (event) => {
  if (!isGlobalWriteAdmin(event)) return Unauthorized;
  await connectToDatabase();
  const id = event.pathParameters?.notificationId;
  if (!id || !isUUID(id)) {
    return NotFound;
  }
  const result = await Notification.delete(id);
  return {
    statusCode: 200,
    body: JSON.stringify(result)
  };
});

/**
 * @swagger
 *
 * /notifications:
 *  get:
 *    description: List all notifications.
 *    tags:
 *    - Notifications
 */
export const list = wrapHandler(async (event) => {
  console.log('list function called with event: ', event);

  await connectToDatabase();
  console.log('Database connected');

  const result = await Notification.find({
    order: {
      startDatetime: 'DESC',
      id: 'DESC'
    }
  });

  console.log('Notification.find result: ', result);

  return {
    statusCode: 200,
    body: JSON.stringify(result)
  };
});

/**
 * @swagger
 *
 * /notifications/{id}:
 *  put:
 *    description: Update a particular notification.
 *    parameters:
 *      - in: path
 *        name: id
 *        description: notification id
 *    tags:
 *    - Notifications
 */

export const update = wrapHandler(async (event) => {
  if (!isGlobalWriteAdmin(event)) return Unauthorized;
  // Get the notification id from the path
  const id = event.pathParameters?.notificationId;

  // confirm that the id is a valid UUID
  if (!id || !isUUID(id)) {
    return NotFound;
  }

  // Validate the body
  const validatedBody = await validateBody(NewNotification, event.body);

  // Connect to the database
  await connectToDatabase();

  // Update the organization
  const updateResp = await Notification.update(id, validatedBody);

  // Handle response
  if (updateResp) {
    const updatedNot = await Notification.findOne(id);
    return {
      statusCode: 200,
      body: JSON.stringify(updatedNot)
    };
  }
  return NotFound;
});

/**
 * @swagger
 *
 * /notifications/508-banner:
 *  get:
 *    description: Get temporary 508 not compliant banner from s3.
 *    tags:
 *    - Notifications
 */
export const get508Banner = wrapHandler(async () => {
  const bannerFileName = '508warningtext.txt';
  try {
    const client = new S3Client();
    const bannerResult = await client.getEmailAsset(bannerFileName);
    return {
      statusCode: 200,
      body: JSON.stringify(bannerResult)
    };
  } catch (error) {
    console.log('S3 Banner Error: ', error);
    return {
      statusCode: 500,
      body: 'Error retrieving file from S3. See details in logs.'
    };
  }
});
