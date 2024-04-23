import { handler as amass } from '../amass';
import { connectToDatabase, Organization, Domain, Scan } from '../../models';
import { spawnSync } from 'child_process';
import * as child_process from 'child_process';
import * as fs from 'fs';
const { Console } = require('console');
global.console = new Console(process.stdout, process.stderr);

beforeEach(() => {
  jest.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  jest.clearAllMocks();
});

jest
  .spyOn(fs, 'readFileSync')
  .mockImplementation(
    () =>
      `{"name":"filedrop.cisa.gov","domain":"cisa.gov","addresses":[{"ip":"2a02:26f0:7a00:195::447a","cidr":"2a02:26f0:7a00::/48","asn":6762,"desc":"SEABONE-NET TELECOM ITALIA SPARKLE S.p.A."},{"ip":"2a02:26f0:7a00:188::447a","cidr":"2a02:26f0:7a00::/48","asn":6762,"desc":"SEABONE-NET TELECOM ITALIA SPARKLE S.p.A."}],"tag":"dns","source":"DNS"}`
  );

jest.spyOn(child_process, 'spawnSync').mockImplementation(() => ({
  pid: 1234,
  output: [
    null,
    JSON.stringify({
      addresses: [{ ip: '104.84.119.215' }],
      name: '2a02:26f0:7a00:195::447a'
    }),
    null
  ],
  stdout: '',
  stderr: '',
  status: 0,
  signal: null
}));

describe('amass', () => {
  let scan;
  let connection;
  let organization;

  beforeAll(async () => {
    connection = await connectToDatabase();
    scan = await Scan.create({
      name: 'amass',
      arguments: {},
      frequency: 999
    }).save();
    organization = await Organization.create({
      name: 'test-' + Math.random(),
      rootDomains: ['rootdomain.example1'],
      ipBlocks: [],
      isPassive: false
    }).save();
  });

  afterAll(async () => {
    await connection.destroy();
  });

  test('should run amass', async () => {
    await amass({
      organizationId: organization.id,
      organizationName: 'Test Organization',
      scanId: scan.id,
      scanName: 'Test Scan',
      scanTaskId: 'Test Scan Task ID'
    });
    expect(spawnSync).toHaveBeenCalled();
  });

  test('should add new domains', async () => {
    const domains = await Domain.find({
      where: {
        organization: { id: organization.id }
      },
      relations: ['organization']
    });
    expect(domains.length).toEqual(1);
    expect(domains[0].name).toEqual('filedrop.cisa.gov');
    expect(domains[0].ip).toEqual('2a02:26f0:7a00:195::447a');
    expect(domains[0].organization.id).toEqual(organization.id);
  });
});
