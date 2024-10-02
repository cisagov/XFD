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
    const authorizationHeader = this.request.headers.authorization;

    if (!authorizationHeader) {
      throw 'Missing token/api key';
    }

    if (/^[A-Fa-f0-9]{32}$/.test(authorizationHeader)) {
      // API Key Logic
      const hashedKey = createHash('sha256')
        .update(authorizationHeader)
        .digest('hex');
      const apiKey = await ApiKey.findOne(
        { hashedKey },
        { relations: ['user'] }
      );

      if (!apiKey) {
        throw 'Invalid API key';
      }

      // Update last used and assign token
      apiKey.lastUsed = new Date();
      await apiKey.save();

      this.token = { id: apiKey.user.id };
    } else {
      // JWT Logic
      try {
        const parsedUserFromJwt = jwt.verify(
          authorizationHeader,
          process.env.JWT_SECRET!
        ) as UserToken;
        this.token = { id: parsedUserFromJwt.id };
      } catch (err) {
        throw 'Invalid JWT token';
      }
    }
  }

  // Constructor takes a request and sets it to a class variable
  constructor(req: Request) {
    this.request = req;
  }
}

// Database Tables
