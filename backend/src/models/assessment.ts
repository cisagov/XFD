import {
  BaseEntity,
  Column,
  Entity,
  ManyToOne,
  OneToMany,
  PrimaryGeneratedColumn,
  Relation
} from 'typeorm';
import { Response, User } from './index';

@Entity()
export class Assessment extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  createdAt: Date;

  @Column()
  updatedAt: Date;

  @Column({ unique: true })
  rscId: string;

  @Column()
  type: string;

  @ManyToOne(() => User, (user) => user.assessments)
  user: Relation<User>;

  @OneToMany(() => Response, (response) => response.assessment)
  responses: Relation<Response>[];
}
