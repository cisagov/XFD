import {
  Entity,
  Column,
  Unique,
  PrimaryGeneratedColumn,
  BaseEntity,
  CreateDateColumn
} from 'typeorm';

@Entity()
@Unique(['email'])
export class EmailBlocklist extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  email: string;

  @CreateDateColumn()
  createdAt: Date;
}
