import { Handler } from 'aws-lambda';
import { connectToDatalake2, connectToDatabase } from '../models';

export const handler: Handler = async (event) => {
  const connection = await connectToDatabase();
  try {
    await connection.query(
      `CREATE USER ${process.env.MDL_USERNAME} WITH PASSWORD '${process.env.MDL_PASSWORD}';`
    );
  } catch (e) {
    console.log(
      "Create user failed. This usually means that the user already exists, so you're OK if that was the case. Here's the exact error:",
      e
    );
  }
  try {
    await connection.query(
      `GRANT ${process.env.MDL_USERNAME} to ${process.env.DB_USERNAME};`
    );
  } catch (e) {
    console.log('Grant role failed. Error:', e);
  }
  try {
    await connection.query(
      `CREATE DATABASE ${process.env.MDL_NAME} owner ${process.env.MDL_USERNAME};`
    );
  } catch (e) {
    console.log(
      "Create database failed. This usually means that the database already exists, so you're OK if that was the case. Here's the exact error:",
      e
    );
  }

  try {
    await connection.query(
      `GRANT ALL PRIVILEGES ON DATABASE ${process.env.MDL_NAME} TO ${process.env.MDL_USERNAME};`
    );
  } catch (e) {
    console.log(
      "Failed to give user all role. This usually means the user already has this role, so you're OK if that was the case. Here's the exact error:",
      e
    );
  }

  const mdl_connection = await connectToDatalake2(true);
  const type = event?.type || event;
  const dangerouslyforce = type === 'dangerouslyforce';

  if (mdl_connection) {
    await mdl_connection.synchronize(dangerouslyforce);
  } else {
    console.error('Error: could not sync');
  }
};
