import {
  BaseEntity,
  Column,
  Entity,
  ManyToOne,
  OneToMany,
  PrimaryGeneratedColumn
} from 'typeorm';
import { Response } from './response';
import { User } from './user';

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
  user: User;

  @OneToMany(() => Response, (response) => response.assessment)
  responses: Response[];
}
