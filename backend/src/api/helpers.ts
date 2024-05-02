import {
  APIGatewayProxyHandler,
  APIGatewayProxyEvent,
  APIGatewayProxyResult,
  Handler
} from 'aws-lambda';
import { ValidationOptions, validateOrReject } from 'class-validator';
import { ClassType } from 'class-transformer/ClassTransformer';
import { plainToClass } from 'class-transformer';
import S3Client from '../tasks/s3-client';
import { SES } from 'aws-sdk';
import * as nodemailer from 'nodemailer';
import logger from '../tools/lambda-logger';
import * as handlebars from 'handlebars';

export const REGION_STATE_MAP = {
  Alabama: '4',
  Alaska: '10',
  'American Samoa': '9',
  Arkansas: '6',
  Arizona: '9',
  California: '9',
  Colorado: '8',
  'Commonwealth Northern Mariana Islands': '9',
  Connecticut: '1',
  Delaware: '3',
  'District of Columbia': '3',
  'Federal States of Micronesia': '9',
  Florida: '4',
  Georgia: '4',
  Guam: '9',
  Hawaii: '9',
  Idaho: '10',
  Illinois: '5',
  Indiana: '5',
  Iowa: '7',
  Kansas: '7',
  Kentucky: '4',
  Louisiana: '6',
  Maine: '1',
  Maryland: '3',
  Massachusetts: '1',
  Michigan: '5',
  Minnesota: '5',
  Mississippi: '4',
  Missouri: '7',
  Montana: '8',
  Nebraska: '7',
  Nevada: '9',
  'New Hampshire': '1',
  'New Jersey': '2',
  'New Mexico': '6',
  'New York': '2',
  'North Carolina': '4',
  'North Dakota': '8',
  Ohio: '5',
  Oklahoma: '6',
  Oregon: '10',
  Pennsylvania: '3',
  'Puerto Rico': '2',
  'Republic of Marshall Islands': '9',
  'Rhode Island': '1',
  'South Carolina': '4',
  'South Dakota': '8',
  Tennessee: '4',
  Texas: '6',
  Utah: '8',
  Vermont: '1',
  'Virgin Islands': '2',
  Virginia: '3',
  Washington: '10',
  'West Virginia': '3',
  Wisconsin: '5',
  Wyoming: '8'
};

export const validateBody = async <T>(
  obj: ClassType<T>,
  body: string | null,
  validateOptions?: ValidationOptions
): Promise<T> => {
  const raw: any = plainToClass(obj, JSON.parse(body ?? '{}'));
  await validateOrReject(raw, {
    ...validateOptions,
    whitelist: true,
    forbidUnknownValues: true
  });
  return raw;
};

export const makeResponse = (
  event: APIGatewayProxyEvent,
  opts: Partial<APIGatewayProxyResult>
): APIGatewayProxyResult => {
  const origin = event.headers?.origin || '*';
  const { body, statusCode = 200, ...rest } = opts;
  return {
    statusCode,
    headers: {
      'Access-Control-Allow-Origin': origin
    },
    body: body ?? '',
    ...rest
  };
};

type WrapHandler = (
  handler: Handler<
    APIGatewayProxyEvent & {
      query?: any;
    },
    APIGatewayProxyResult
  >
) => APIGatewayProxyHandler;
export const wrapHandler: WrapHandler =
  (handler) => async (event, context, callback) => {
    try {
      const result = (await handler(
        event,
        context,
        callback
      )) as APIGatewayProxyResult;
      const resp = makeResponse(event, result);
      if (typeof jest === 'undefined') {
        logger.info(`=> ${resp.statusCode} ${event.path} `);
      }
      return resp;
    } catch (e) {
      logger.error(e);
      return makeResponse(event, {
        statusCode: Array.isArray(e) ? 400 : 500
      });
    }
  };

export const NotFound: APIGatewayProxyResult = {
  statusCode: 404,
  body: 'Item not found. View logs for details.'
};

export const Unauthorized: APIGatewayProxyResult = {
  statusCode: 403,
  body: 'Unauthorized access. View logs for details.'
};

export const sendEmail = async (
  recipient: string,
  subject: string,
  body: string
) => {
  try {
    const transporter = nodemailer.createTransport({
      SES: new SES({
        region: process.env.EMAIL_REGION!
      })
    });

    await transporter.sendMail({
      from: process.env.CROSSFEED_SUPPORT_EMAIL_SENDER!,
      to: recipient,
      subject: subject,
      text: body,
      replyTo: process.env.CROSSFEED_SUPPORT_EMAIL_REPLYTO!
    });

    logger.info('Email sent successfully');
    return 'Email sent successfully';
  } catch (error) {
    logger.error(`Error sending email: ${error}`);

    // Handle the error or re-throw it if needed
    throw error;
  }
};

export const sendRegistrationTextEmail = async (recipient: string) => {
  const transporter = nodemailer.createTransport({
    SES: new SES({
      region: process.env.EMAIL_REGION!
    })
  });

  const mailOptions = {
    from: process.env.CROSSFEED_SUPPORT_EMAIL_SENDER!,
    to: recipient,
    subject: 'Crossfeed Registration Pending',
    text: 'Your registration is pending approval.',
    replyTo: process.env.CROSSFEED_SUPPORT_EMAIL_REPLYTO!
  };

  await transporter.sendMail(mailOptions, (error, data) => {
    console.log(data);
    if (error) {
      console.log(error);
    }
  });
};

export const sendRegistrationHtmlEmail = async (recipient: string) => {
  const transporter = nodemailer.createTransport({
    SES: new SES({
      region: process.env.EMAIL_REGION!
    })
  });

  const mailOptions = {
    from: process.env.CROSSFEED_SUPPORT_EMAIL_SENDER!,
    to: recipient,
    subject: 'Crossfeed Registration Pending',
    html: '<p>Your registration is pending approval.</p>',
    replyTo: process.env.CROSSFEED_SUPPORT_EMAIL_REPLYTO!
  };

  await transporter.sendMail(mailOptions, (error, data) => {
    console.log(data);
    if (error) {
      console.log(error);
    }
  });
};

export const sendUserRegistrationEmail = async (
  recepient: string,
  subject: string,
  firstName: string,
  lastName: string,
  templateFileName: string
) => {
  try {
    const client = new S3Client();
    const htmlTemplate = await client.getEmailAsset(templateFileName);
    const template = handlebars.compile(htmlTemplate);
    const data = {
      firstName: firstName,
      lastName: lastName
    };

    const htmlToSend = template(data);
    const mailOptions = {
      from: process.env.CROSSFEED_SUPPORT_EMAIL_SENDER!,
      to: recepient,
      subject: subject,
      html: htmlToSend,
      replyTo: process.env.CROSSFEED_SUPPORT_EMAIL_REPLYTO!
    };

    const transporter = nodemailer.createTransport({
      SES: new SES({
        region: process.env.EMAIL_REGION!
      })
    });
    await transporter.sendMail(mailOptions);
  } catch (errorMessage) {
    console.log('Email error: ', errorMessage);
  }
};

export const sendRegistrationDeniedEmail = async (
  recepient: string,
  subject: string,
  firstName: string,
  lastName: string,
  templateFileName: string
) => {
  try {
    const client = new S3Client();
    const htmlTemplate = await client.getEmailAsset(templateFileName);
    const template = handlebars.compile(htmlTemplate);
    const data = {
      firstName: firstName,
      lastName: lastName
    };

    const htmlToSend = template(data);
    const mailOptions = {
      from: process.env.CROSSFEED_SUPPORT_EMAIL_SENDER!,
      to: recepient,
      subject: subject,
      html: htmlToSend,
      replyTo: process.env.CROSSFEED_SUPPORT_EMAIL_REPLYTO!
    };

    const transporter = nodemailer.createTransport({
      SES: new SES({
        region: process.env.EMAIL_REGION!
      })
    });
    await transporter.sendMail(mailOptions);
  } catch (errorMessage) {
    console.log('Email error: ', errorMessage);
  }
};

export const sendRegistrationApprovedEmail = async (
  recepient: string,
  subject: string,
  firstName: string,
  lastName: string,
  templateFileName: string
) => {
  try {
    const client = new S3Client();
    const htmlTemplate = await client.getEmailAsset(templateFileName);
    const template = handlebars.compile(htmlTemplate);
    const data = {
      firstName: firstName,
      lastName: lastName
    };

    const htmlToSend = template(data);
    const mailOptions = {
      from: process.env.CROSSFEED_SUPPORT_EMAIL_SENDER!,
      to: recepient,
      subject: subject,
      html: htmlToSend,
      replyTo: process.env.CROSSFEED_SUPPORT_EMAIL_REPLYTO!
    };

    const transporter = nodemailer.createTransport({
      SES: new SES({
        region: process.env.EMAIL_REGION!
      })
    });
    await transporter.sendMail(mailOptions);
  } catch (errorMessage) {
    console.log('Email error: ', errorMessage);
  }
};
