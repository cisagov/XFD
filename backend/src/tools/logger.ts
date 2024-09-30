import { Request } from 'express';
import * as jwt from 'jsonwebtoken';
import { ApiKey, User } from '../models';
import { Log } from '../models/log';
import { getRepository, Repository } from 'typeorm';
import { UserToken } from 'src/api/auth';
import { createHash } from 'crypto';

type AccessTokenPayload = {
  id: string;
};

type LoggerUserState = {
  data: User | undefined;
  ready: boolean;
  attempts: number;
};

type RecordPayload = object & {
  timestamp: Date;
};

export type RecordMessage =
  | ((
      request: Request,
      token: AccessTokenPayload | undefined,
      responseBody?: object
    ) => Promise<RecordPayload>)
  | RecordPayload;

export class Logger {
  private request: Request;
  private logId: string;
  private token: AccessTokenPayload | undefined;
  private user: LoggerUserState = {
    data: undefined,
    ready: false,
    attempts: 0
  };
  private logRep: Repository<Log>;

  async record(
    action: string,
    result: 'success' | 'fail',
    messageOrCB: RecordMessage | undefined,
    responseBody?: object | string
  ) {
    try {
      if (!this.logRep) {
        const logRepository = getRepository(Log);
        this.logRep = logRepository;
      }

      if (!this.token) {
        await this.parseToken();
      }

      const parsedResponseBody =
        typeof responseBody === 'string' &&
        responseBody !== 'User registration approved.'
          ? JSON.parse(responseBody)
          : responseBody;

      const payload =
        typeof messageOrCB === 'function'
          ? await messageOrCB(this.request, this.token, parsedResponseBody)
          : messageOrCB;

      const logRecord = await this.logRep.create({
        payload: payload as object,
        createdAt: payload?.timestamp,
        result: result,
        eventType: action
      });

      logRecord.save();
    } catch (error) {
      console.warn('Error occured in loggingMiddleware', error);
    }
  }

  async parseToken() {
    const authToken = this.request.headers.authorization;
    // Test if API key, e.g. a 32 digit hex string
    if (authToken && /^[A-Fa-f0-9]{32}$/.test(authToken ?? '')) {
      const apiKey = await ApiKey.findOne(
        {
          hashedKey: createHash('sha256').update(authToken).digest('hex')
        },
        { relations: ['user'] }
      );
      if (!apiKey) throw 'Invalid API key';
      this.token = { id: apiKey.user.id };
      apiKey.lastUsed = new Date();
      apiKey.save();
    } else {
      if (authToken) {
        const parsedUserFromJwt = jwt.verify(
          authToken,
          process.env.JWT_SECRET!
        ) as UserToken;
        this.token = { id: parsedUserFromJwt.id };
      }
    }
  }

  // Constructor takes a request and sets it to a class variable
  constructor(req: Request) {
    this.request = req;
  }
}

// Database Tables
