import { DataSource } from 'typeorm';
import {
  // Models for the Crossfeed database
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
} from './index';

let dbConnection: DataSource | null = null;

let dlConnection: DataSource | null = null;

const createDlConnection = async (
  logging: boolean = false
): Promise<DataSource> => {
  try {
    const dataSource = new DataSource({
      type: 'postgres',
      host: process.env.DB_HOST,
      port: parseInt(process.env.DB_PORT || '5432'),
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
      dropSchema: false,
      logging,
      cache: true
    });
    await dataSource.initialize();
    console.log('Data Lake connection initialized successfully.');
    return dataSource;
  } catch (error) {
    console.error('Failed to initialize the Data Lake connection:', error);
    throw new Error('Initialization of Data Lake connection failed');
  }
};

export const connectToDatalake = async (
  logging: boolean = false
): Promise<DataSource> => {
  if (!dlConnection?.isInitialized) {
    try {
      dlConnection = await createDlConnection(logging);
    } catch (error) {
      console.error('Connection to data lake failed:', error);
      throw error;
    }
  } else {
    console.log('Data Lake connection already initialized.');
  }
  return dlConnection;
};

const createDbConnection = async (
  logging: boolean = false
): Promise<DataSource> => {
  try {
    const dataSource = new DataSource({
      type: 'postgres',
      host: process.env.DB_HOST,
      port: parseInt(process.env.DB_PORT || '5432'),
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
        Scan,
        ScanTask,
        Service,
        User,
        Vulnerability,
        Webpage
      ],
      synchronize: false,
      dropSchema: false,
      logging,
      cache: true
    });
    await dataSource.initialize();
    console.log('DB connection initialized successfully.');
    return dataSource;
  } catch (error) {
    console.error('Failed to initialize the DB connection:', error);
    throw new Error('Initialization of DB connection failed');
  }
};

export const connectToDatabase = async (
  logging: boolean = false
): Promise<DataSource> => {
  if (!dbConnection?.isInitialized) {
    try {
      dbConnection = await createDbConnection(logging);
    } catch (error) {
      console.error('Connection to database failed:', error);
      throw error;
    }
  }
  return dbConnection;
};
