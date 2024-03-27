// The data in this collection is derived from the Vulnerability Scans Database,
// the [reports Collection] (https://github.com/cisagov/ncats-data-dictionary/blob/develop/NCATS_Data_Dictionary.md#reports-collection).

import { Entity, Column, PrimaryColumn, BaseEntity, ManyToOne } from 'typeorm';

import { Organization } from './organizations';
import { Snapshot } from './snapshots';

@Entity()
export class Report extends BaseEntity {
  @PrimaryColumn()
  id: string;

  @ManyToOne((type) => Organization, (org) => org.reports, {
    onDelete: 'CASCADE',
    nullable: true
  })
  organization: Organization;

  @Column({ nullable: true, type: 'timestamp' })
  createdTimestamp: Date | null;

  @Column('varchar', { array: true, default: [] })
  reportTypes: string[];

  @ManyToOne((type) => Snapshot, (snapshot) => snapshot.reports, {
    onDelete: 'CASCADE',
    nullable: true
  })
  snapshot: Snapshot;
}
