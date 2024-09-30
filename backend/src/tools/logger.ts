import { Request } from 'express';
import { decode } from 'jsonwebtoken';
import { User } from '../models';
import { attempt, unescape } from 'lodash';
import { Log } from '../models/log';
import { getRepository, Repository } from 'typeorm';

type AccessTokenPayload = {
  id: string;
  email: string;
  iat: string;
  exp: string;
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
      user: LoggerUserState,
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
      if (!this.user.ready && this.user.attempts > 0) {
        await this.fetchUser();
      }

      if (!this.logRep) {
        const logRepository = getRepository(Log);
        this.logRep = logRepository;
      }

      const parsedResponseBody =
        typeof responseBody === 'string' &&
        responseBody !== 'User registration approved.'
          ? JSON.parse(responseBody)
          : responseBody;

      const payload =
        typeof messageOrCB === 'function'
          ? await messageOrCB(this.request, this.user, parsedResponseBody)
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

  async fetchUser() {
    if (this.token) {
      const user = await User.findOne({ id: this.token.id });
      if (user) {
        this.user = {
          data: user,
          ready: true,
          attempts: 0
        };
      }
      this.user = {
        data: undefined,
        ready: false,
        attempts: this.user.attempts + 1
      };
    }
  }

  // Constructor takes a request and sets it to a class variable
  constructor(req: Request) {
    this.request = req;
    const authToken = req.headers.authorization;
    if (authToken) {
      const tokenPayload = decode(
        authToken as string
      ) as unknown as AccessTokenPayload;
      this.token = tokenPayload;
      if (this?.token?.id) {
        User.findOne({ id: this?.token?.id }).then((user) => {
          if (user) {
            this.user = { data: user, ready: true, attempts: 0 };
          }
        });
      }
    }
  }
}

// Database Tables
