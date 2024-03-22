import {
  BaseEntity,
  Column,
  Entity,
  OneToMany,
  PrimaryGeneratedColumn
} from 'typeorm';
import { RscQuestion } from './rsc_question';

@Entity()
export class RscCategory extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  name: string;

  @OneToMany(() => RscQuestion, (question) => question.category)
  questions: RscQuestion[];
}
