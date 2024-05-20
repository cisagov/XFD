import { createConnection, Connection } from 'typeorm';
import {
  // Models for the Crossfeed database
  ApiKey,
  Notification,
  Assessment,
  Category,
  Cpe,
  Cve,
  Domain,
  Organization,
  OrganizationTag,
  Question,
  Resource,
  Response,
  Role,
  SavedSearch,
  Scan,
  ScanTask,
  Service,
  User,
  Vulnerability,
  Webpage,

  //  Models for the Mini Data Lake database
  CertScan,
  Cidr,
  Contact,
  DL_Cpe,
  DL_Cve,
  DL_Domain,
  DL_Organization,
  HostScan,
  Host,
  Ip,
  Kev,
  Location,
  PortScan,
  PrecertScan,
  Report,
  Sector,
  Snapshot,
  SslyzeScan,
  Tag,
  Tally,
  TicketEvent,
  Ticket,
  TrustymailScan,
  VulnScan
} from '.';

let connection: Connection | null = null;

let dl_connection: Connection | null = null;

let dl2_connection: Connection | null = null;

const connectDl2 = async (logging?: boolean) => {
  const dl2_connection = createConnection({
    type: 'postgres',
    host: process.env.DB_HOST,
    port: parseInt(process.env.DB_PORT ?? ''),
    username: process.env.MDL_USERNAME,
    password: process.env.MDL_PASSWORD,
    database: process.env.MDL_NAME,
    entities: [
      CertScan,
      Cidr,
      Contact,
      DL_Cpe,
      DL_Cve,
      DL_Domain,
      HostScan,
      Host,
      Ip,
      Kev,
      Location,
      DL_Organization,
      PortScan,
      PrecertScan,
      Report,
      Sector,
      Snapshot,
      SslyzeScan,
      Tag,
      Tally,
      TicketEvent,
      Ticket,
      TrustymailScan,
      VulnScan
    ],
    synchronize: false,
    name: 'default2',
    dropSchema: false,
    logging: logging ?? false,
    cache: true
  });
  return dl2_connection;
};

export const connectToDatalake2 = async (logging?: boolean) => {
  if (!dl2_connection?.isConnected) {
    console.log('Connected to datalake');
    dl2_connection = await connectDl2(logging);
  }
  return dl2_connection;
};

const connectDl = async (logging?: boolean) => {
  // process.env.DB_HOST = 'db';
  // process.env.MDL_USERNAME = 'mdl';
  // process.env.MDL_PASSWORD = 'password';
  // process.env.MDL_NAME = 'crossfeed_mini_datalake';

  // console.log(process.env.MDL_USERNAME)
  // console.log(process.env.MDL_PASSWORD)
  // console.log(process.env.MDL_NAME)
  const dl_connection = createConnection({
    type: 'postgres',
    host: process.env.DB_HOST,
    port: parseInt(process.env.DB_PORT ?? ''),
    username: process.env.MDL_USERNAME,
    password: process.env.MDL_PASSWORD,
    database: process.env.MDL_NAME,
    entities: [
      CertScan,
      Cidr,
      Contact,
      DL_Cpe,
      DL_Cve,
      DL_Domain,
      HostScan,
      Host,
      Ip,
      Kev,
      Location,
      DL_Organization,
      PortScan,
      PrecertScan,
      Report,
      Sector,
      Snapshot,
      SslyzeScan,
      Tag,
      Tally,
      TicketEvent,
      Ticket,
      TrustymailScan,
      VulnScan
    ],
    synchronize: false,
    name: 'default',
    dropSchema: false,
    logging: logging ?? false,
    cache: true
  });
  return dl_connection;
};

export const connectToDatalake = async (logging?: boolean) => {
  if (!dl_connection?.isConnected) {
    console.log('Connected to datalake');
    dl_connection = await connectDl(logging);
  }
  return dl_connection;
};

const connectDb = async (logging?: boolean) => {
  const connection = createConnection({
    type: 'postgres',
    host: process.env.DB_HOST,
    port: parseInt(process.env.DB_PORT ?? ''),
    username: process.env.DB_USERNAME,
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME,
    entities: [
      ApiKey,
      Assessment,
      Category,
      Cpe,
      Cve,
      Domain,
      Organization,
      OrganizationTag,
      Question,
      Resource,
      Response,
      Role,
      SavedSearch,
      OrganizationTag,
      Notification,
      Scan,
      ScanTask,
      Service,
      User,
      Vulnerability,
      Webpage
    ],
    synchronize: false,
    name: 'default',
    dropSchema: false,
    logging: logging ?? false,
    cache: true
  });
  return connection;
};

export const connectToDatabase = async (logging?: boolean) => {
  if (!connection?.isConnected) {
    connection = await connectDb(logging);
  }
  return connection;
};
