import {
  Entity,
  Index,
  PrimaryGeneratedColumn,
  UpdateDateColumn,
  CreateDateColumn,
  BaseEntity,
  ManyToMany,
  JoinTable,
  Column
} from 'typeorm';
import { Organization, Scan } from '.';

@Entity()
@Index(['name'], { unique: true })
export class OrganizationTag extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;

  @Column()
  name: string;

  /**
   * Organizations that are labeled with this tag
   */
  @ManyToMany((type) => Organization, (organization) => organization.tags, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  @JoinTable({
    name: 'organization_tag_organizations_organization',
    joinColumn: {
      name: 'organizationtag_id',
      referencedColumnName: 'id'
    },
    inverseJoinColumn: {
      name: 'organization_id',
      referencedColumnName: 'id'
    }
  })
  organizations: Organization[];

  /**
   * Scans that have this tag enabled, and will run against all tagged organizations
   */
  @ManyToMany((type) => Scan, (scan) => scan.tags, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  scans: Scan[];
}
