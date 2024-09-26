import { SelectQueryBuilder } from 'typeorm';
import { Log } from '../models';
import { validateBody, wrapHandler } from './helpers';
import { IsDate, IsOptional, IsString } from 'class-validator';

type ParsedQuery = {
  [key: string]: string | ParsedQuery;
};

const parseQueryString = (query: string): ParsedQuery => {
  // Parses a query string that is used to search the JSON payload of a record
  // Example => createdUserPayload.userId: 123124121424
  const result: ParsedQuery = {};

  const parts = query.match(/(\w+(\.\w+)*):\s*[^:]+/g);

  if (!parts) {
    return result;
  }

  parts.forEach((part) => {
    const [key, value] = part.split(/:(.+)/);

    if (!key || value === undefined) return;

    const keyParts = key.trim().split('.');
    let current = result;

    keyParts.forEach((part, index) => {
      if (index === keyParts.length - 1) {
        current[part] = value.trim();
      } else {
        if (!current[part]) {
          current[part] = {};
        }
        current = current[part] as ParsedQuery;
      }
    });
  });

  return result;
};

const generateSqlConditions = (
  parsedQuery: ParsedQuery,
  jsonPath: string[] = []
): string[] => {
  const conditions: string[] = [];

  for (const [key, value] of Object.entries(parsedQuery)) {
    if (typeof value === 'object') {
      const newPath = [...jsonPath, key];
      conditions.push(...generateSqlConditions(value, newPath));
    } else {
      const jsonField =
        jsonPath.length > 0
          ? `${jsonPath.map((path) => `'${path}'`).join('->')}->>'${key}'`
          : `'${key}'`;
      conditions.push(
        `payload ${
          jsonPath.length > 0 ? '->' : '->>'
        } ${jsonField} = '${value}'`
      );
    }
  }

  return conditions;
};
class Filter {
  @IsString()
  value: string;

  @IsString()
  operator?: string;
}

class DateFilter {
  @IsDate()
  value: string;

  @IsString()
  operator:
    | 'is'
    | 'not'
    | 'after'
    | 'onOrAfter'
    | 'before'
    | 'onOrBefore'
    | 'empty'
    | 'notEmpty';
}
class LogSearch {
  @IsOptional()
  eventType?: Filter;
  @IsOptional()
  result?: Filter;
  @IsOptional()
  timestamp?: Filter;
  @IsOptional()
  payload?: Filter;
}

const generateDateCondition = (filter: DateFilter): string => {
  const { operator } = filter;

  switch (operator) {
    case 'is':
      return `log.createdAt = :timestamp`;
    case 'not':
      return `log.createdAt != :timestamp`;
    case 'after':
      return `log.createdAt > :timestamp`;
    case 'onOrAfter':
      return `log.createdAt >= :timestamp`;
    case 'before':
      return `log.createdAt < :timestamp`;
    case 'onOrBefore':
      return `log.createdAt <= :timestamp`;
    case 'empty':
      return `log.createdAt IS NULL`;
    case 'notEmpty':
      return `log.createdAt IS NOT NULL`;
    default:
      throw new Error('Invalid operator');
  }
};

const filterResultQueryset = async (qs: SelectQueryBuilder<Log>, filters) => {
  if (filters?.eventType) {
    qs.andWhere('log.eventType ILIKE :eventType', {
      eventType: `%${filters?.eventType?.value}%`
    });
  }
  if (filters?.result) {
    qs.andWhere('log.result ILIKE :result', {
      result: `%${filters?.result?.value}%`
    });
  }
  if (filters?.payload) {
    try {
      const parsedQuery = parseQueryString(filters?.payload?.value);
      const conditions = generateSqlConditions(parsedQuery);
      qs.andWhere(conditions[0]);
    } catch (error) {}
  }

  if (filters?.timestamp) {
    const timestampCondition = generateDateCondition(filters?.timestamp);
    let date;
    try {
      date = new Date(filters?.timestamp?.value);
    } catch (error) {}
    qs.andWhere(timestampCondition, {
      timestamp: new Date(filters?.timestamp?.value)
    });
  }

  return qs;
};

export const list = wrapHandler(async (event) => {
  const search = await validateBody(LogSearch, event.body);

  const qs = Log.createQueryBuilder('log');

  const filterQs = await filterResultQueryset(qs, search);

  const [results, resultsCount] = await filterQs.getManyAndCount();

  return {
    statusCode: 200,
    body: JSON.stringify({
      result: results,
      count: resultsCount
    })
  };
});
