// The data in this table is derived from the "Government Units" and
// "Populated Places" Topical Gazetteers files from
// [USGS](https://geonames.usgs.gov/domestic/download_data.htm).

import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  BaseEntity,
  OneToMany
} from 'typeorm';

import { Organization } from './organizations';
@Entity()
export class Location extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  name: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  countryAbrv: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  country: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  county: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  countyFips: string | null;

  @Column({
    nullable: true,
    type: 'varchar',
    unique: true
  })
  gnisId: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  stateAbrv: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  stateFips: string | null;

  @Column({
    nullable: true,
    type: 'varchar'
  })
  state: string | null;

  @OneToMany((type) => Organization, (org) => org.location, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  organizations?: Organization[];
}
