import {
  BaseEntity,
  Column,
  CreateDateColumn,
  Entity,
  ManyToOne,
  OneToMany,
  PrimaryGeneratedColumn,
  UpdateDateColumn
} from 'typeorm';
import { Response } from './response';
import { User } from './user';

@Entity()
export class Assessment extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;

  @Column()
  rscId: string;

  @Column()
  type: string;

  @ManyToOne(() => User, (user) => user.assessments)
  user: User;

  @OneToMany(() => Response, (response) => response.assessment)
  responses: Response[];
}
