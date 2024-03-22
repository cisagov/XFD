import {
  BaseEntity,
  CreateDateColumn,
  Entity,
  ManyToOne,
  OneToMany,
  PrimaryGeneratedColumn,
  UpdateDateColumn
} from 'typeorm';
import { User } from './user';
import { RscQuestion } from './rsc_question';

@Entity()
export class RscAssessment extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;

  @ManyToOne(() => User, (user) => user.assessments)
  user: User;

  @OneToMany(() => RscQuestion, (question) => question.assessment)
  questions: RscQuestion[];
}
