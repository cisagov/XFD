import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  UpdateDateColumn,
  CreateDateColumn,
  BaseEntity,
  ManyToOne
} from 'typeorm';
import { Vulnerability } from './vulnerability';
import { User } from './user';

@Entity()
export class SavedSearch extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;

  @Column()
  name: string;

  @Column()
  searchTerm: string;

  @Column()
  sortDirection: string;

  @Column()
  sortField: string;

  @Column()
  count: number;

  @Column({ type: 'jsonb', default: '[]' })
  filters: { field: string; values: any[]; type: string }[];

  @Column()
  searchPath: string;
  // The following properties are deprecated due to the refactor of the Save Search Modal.
  // The Create Vulnerabilities functionality has been removed as it is no longer needed.
  // These properties are kept here for reference and will be removed in future versions.  // @Column({
  //   default: false
  // })
  // createVulnerabilities: boolean;

  // // Content of vulnerability when search is configured to create vulnerabilities from results
  // @Column({ type: 'jsonb', default: '{}' })
  // vulnerabilityTemplate: Partial<Vulnerability> & {
  //   title: string;
  // };

  @ManyToOne((type) => User, {
    onDelete: 'SET NULL',
    onUpdate: 'CASCADE'
  })
  createdBy: User;
}
