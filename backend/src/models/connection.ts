import { createConnection, Connection } from 'typeorm';
import {
  // Models for the Crossfeed database
  Domain,
  Service,
  Vulnerability,
  Scan,
  Organization,
  User,
  Role,
  ScanTask,
  Webpage,
  ApiKey,
  SavedSearch,
  OrganizationTag,
  Cpe,
  Cve,

  //  Models for the Mini Data Lake database
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
  Request,
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

const connectDl = async (logging?:boolean) => {
  const dl_connection = createConnection({
    type: 'postgres',
    host: process.env.MDL_HOST,
    port: parseInt(process.env.MDL_PORT ?? ''),
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
      Request,
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
    name: 'mini_data_lake',
    dropSchema: false,
    logging: logging ?? false,
    cache: true
  });
  return dl_connection
}

export const connectToDatalake = async (logging?: boolean) => {
  if (!dl_connection?.isConnected) {
    dl_connection = await connectDl(logging);
  }
  else {
    console.log("didn't connect")
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
      Cpe,
      Cve,
      Domain,
      Service,
      Vulnerability,
      Scan,
      Organization,
      User,
      Role,
      ScanTask,
      Webpage,
      ApiKey,
      SavedSearch,
      OrganizationTag
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
