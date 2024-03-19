// The data in this collection is derived from the Vulnerability Scans Database,
// the [requests Collection] (https://github.com/cisagov/ncats-data-dictionary/blob/develop/NCATS_Data_Dictionary.md#requests-collection).


import {
    Entity,
    Index,
    Column,
    PrimaryGeneratedColumn,
    BaseEntity,
    ManyToMany,
    ManyToOne
  } from 'typeorm';

import { Organization } from './organizations';
import {Cidr} from './cidrs'
@Entity()
export class Request extends BaseEntity {
    @PrimaryGeneratedColumn('uuid')
    id: string;

    @ManyToOne((type) => Organization, (org) => org.requests, {
        onDelete: 'CASCADE',
        nullable: true
      })
      organization: Organization;

    @Column({
        nullable: true,
        type: 'varchar',
        unique: true
      })
    @Index()
      acronym: string | null;
    
    @Column({ nullable: true, type: 'timestamp' })
      enrolledTimestamp : Date | null;

    @Column({ nullable: true, type: 'timestamp' })
      periodStartTimestamp : Date | null;
 
    @Column({
        nullable: true,
        type: 'varchar'
      })
      reportPeriod: string | null;

    @Column({
        nullable: true,
        type: 'varchar'
      })
      initStage: string | null;

    @Column({
        nullable: true,
        type: 'varchar'
      })
      scheduler: string | null;

    @Column({ nullable: true })
      retired: boolean;

    @Column("simple-array")
      reportTypes: string[]

    @Column({
        type: 'jsonb',
        default: []
      })
      scanWindows: Object[];
     
    @Column({
      type: 'jsonb',
      default: []
    })
    scanLimits: Object[];
     
    @ManyToMany((type) => Cidr, (cidr) => cidr.requests, {
      onDelete: 'CASCADE',
      onUpdate: 'CASCADE'
    })
    cidrs: Cidr[];
}