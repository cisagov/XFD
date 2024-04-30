import { connectToDatabase, Organization, Domain, Scan } from '../../models';
import { Console } from 'console';
import { DataSource } from 'typeorm';
import { handler as findomain } from '../findomain';
import * as fs from 'fs';

console = new Console(process.stdout, process.stderr);
jest
  .spyOn(fs, 'readFileSync')
  .mockImplementation(() =>
    [
      'filedrop.cisa.gov,104.84.119.215',
      'www.filedrop.cisa.gov,104.84.119.215'
    ].join('\n')
  );

describe('findomain', () => {
  let scan: Scan;
  let connection: DataSource;
  beforeAll(async () => {
    connection = await connectToDatabase();
    scan = await Scan.create({
      name: 'findomain',
      arguments: {},
      frequency: 999
    }).save();
  });
  afterAll(async () => {
    await connection.destroy();
  });
  test('should add new domains', async () => {
    const organization = await Organization.create({
      name: 'test-' + Math.random(),
      rootDomains: ['test-' + Math.random()],
      ipBlocks: [],
      isPassive: false
    }).save();
    await findomain({
      organizationId: organization.id,
      organizationName: 'organizationName',
      scanId: scan.id,
      scanName: 'scanName',
      scanTaskId: 'scanTaskId'
    });

    const domains = (
      await Domain.find({
        where: { organization: { id: organization.id } },
        relations: ['organization', 'discoveredBy']
      })
    ).sort((a, b) => a.name.localeCompare(b.name));
    expect(domains.length).toEqual(2);
    expect(domains[0].name).toEqual('filedrop.cisa.gov');
    expect(domains[0].ip).toEqual('104.84.119.215');
    expect(domains[0].organization.id).toEqual(organization.id);
    expect(domains[0].discoveredBy.id).toEqual(scan.id);
    expect(domains[1].name).toEqual('www.filedrop.cisa.gov');
    expect(domains[1].ip).toEqual('104.84.119.215');
  });
  test('should update existing domains', async () => {
    const organization = await Organization.create({
      name: 'test-' + Math.random(),
      rootDomains: ['test-' + Math.random()],
      ipBlocks: [],
      isPassive: false
    }).save();
    const scanOld = await Scan.create({
      name: 'findomain',
      arguments: {},
      frequency: 999
    }).save();
    const domain = await Domain.create({
      organization: { id: organization.id },
      name: 'filedrop.cisa.gov',
      discoveredBy: scanOld,
      fromRootDomain: 'oldrootdomain.cisa.gov'
    }).save();
    await findomain({
      organizationId: organization.id,
      organizationName: 'organizationName',
      scanId: scan.id,
      scanName: 'scanName',
      scanTaskId: 'scanTaskId'
    });

    const domains = (
      await Domain.find({
        where: { organization: { id: organization.id } },
        relations: ['discoveredBy']
      })
    ).sort((a, b) => a.name.localeCompare(b.name));
    expect(domains.length).toEqual(2);
    expect(domains[0].id).toEqual(domain.id);
    expect(domains[0].name).toEqual('filedrop.cisa.gov');
    expect(domains[0].ip).toEqual('104.84.119.215');
    expect(domains[0].discoveredBy.id).toEqual(scanOld.id);
    expect(domains[0].fromRootDomain).toEqual('oldrootdomain.cisa.gov');
    expect(domains[1].name).toEqual('www.filedrop.cisa.gov');
    expect(domains[1].ip).toEqual('104.84.119.215');
    expect(domains[1].discoveredBy.id).toEqual(scan.id);
    expect(domains[1].fromRootDomain).toEqual(organization.rootDomains[0]);
  });
});
