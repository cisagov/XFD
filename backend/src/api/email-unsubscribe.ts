import { IsString } from 'class-validator';
import { validateBody, wrapHandler, NotFound } from './helpers';
import { connectToDatabase, EmailBlocklist } from '../models';

class Email {
  @IsString()
  email: string;
}

/**
 * @swagger
 *
 * /email-unsubscribe:
 *  post:
 *    description: Add user to the email blocklist.
 */
export const unsubscribe = wrapHandler(async (event) => {
  console.log(event);
  const body = await validateBody(Email, event.body);

  await connectToDatabase();

  body.email = body.email.toLowerCase();
  const email = await EmailBlocklist.create({
    ...body
  });
  await EmailBlocklist.save(email);

  return {
    statusCode: 200,
    body: 'Email has been added to blocklist'
  };
});

export const resubscribe = wrapHandler(async (event) => {
  const body = await validateBody(Email, event.body);
  await connectToDatabase();

  body.email = body.email.toLowerCase();

  const email = await EmailBlocklist.findOne({
    email: body.email
  });
  if (email) {
    const result = await EmailBlocklist.delete({
      email: body.email
    });
    return {
      statusCode: 200,
      body: JSON.stringify(result)
    };
  }
  return NotFound;
});
