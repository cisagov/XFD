import { plainToClass } from 'class-transformer';
import {
  DL_Organization,
  Cidr,
  Location,
  connectToDatalake
} from '../../models';

export default async (
  organization: DL_Organization,
  cidrs: Cidr[],
  location: Location | null
): Promise<string> => {
  console.log(`Saving org ${organization.acronym} to datalake`);
  await connectToDatalake();

  const cidr_entities: Cidr[] = [];
  const cidr_ids_list: string[] = [];
  for (const cidr of cidrs) {
    const cidrUpdatedValues = Object.keys(cidr)
      .map((key) => {
        if (['network'].indexOf(key) > -1) return '';
        else if (key === 'organization') return 'organizationId';
        return cidr[key] !== null ? key : '';
      })
      .filter((key) => key !== '');

    const cidrId: string = (
      await Cidr.createQueryBuilder()
        .insert()
        .values(cidr)
        .orUpdate({
          conflict_target: ['network'],
          overwrite: cidrUpdatedValues
        })
        .returning('id')
        .execute()
    ).identifiers[0].id;

    cidr_ids_list.push(cidrId);
    const cidrEntity = await Cidr.findOne({ where: { id: cidrId } });
    if (cidrEntity) {
      cidr_entities.push(cidrEntity);
    }
  }

  //   console.log(cidr_entities)
  //   upsert the passed location and return the id
  let locationId: string;
  if (location !== null) {
    const locationUpdatedValues = Object.keys(location)
      .map((key) => {
        if (['gnisId'].indexOf(key) > -1) return '';
        return location[key] !== null ? key : '';
      })
      .filter((key) => key !== '');
    locationId = (
      await Location.createQueryBuilder()
        .insert()
        .values(location)
        .orUpdate({
          conflict_target: ['gnisId'],
          overwrite: locationUpdatedValues
        })
        .returning('id')
        .execute()
    ).identifiers[0].id;
  } else {
    locationId = '';
  }

  const organizationUpdatedValues = Object.keys(organization)
    .map((key) => {
      if (['acronym'].indexOf(key) > -1) return '';
      return organization[key] !== null ? key : '';
    })
    .filter((key) => key !== '');
  const orgId: string = (
    await DL_Organization.createQueryBuilder()
      .insert()
      .values(organization)
      .orUpdate({
        conflict_target: ['acronym'],
        overwrite: organizationUpdatedValues
      })
      .returning('id')
      .execute()
  ).identifiers[0].id;

  const organization_promise = await DL_Organization.findOne({
    where: { id: orgId },
    relations: ['cidrs']
  });
  if (organization_promise) {
    const organization_entity: DL_Organization = organization_promise;
    if (location !== null) {
      const location_promise = await Location.findOne({
        where: { id: locationId }
      });
      if (location_promise) {
        const location_entity: Location = location_promise;
        organization_entity.location = location_entity;
      }
    }

    const newCidrs = cidr_ids_list.filter(
      (cidr) => !organization_entity.cidrs?.some((item) => item.id === cidr)
    );
    organization_entity.cidrs?.push(
      ...newCidrs.map((id) => plainToClass(Cidr, { id }))
    );
    organization_entity.save();
  }

  return orgId;
};
