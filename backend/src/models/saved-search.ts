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
  // TODO: Add this back if we have the ability to create vulnerabilities from search results
  // @Column({
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
