import {
  BaseEntity,
  Column,
  Entity,
  ManyToOne,
  PrimaryGeneratedColumn
} from 'typeorm';
import { Question } from './question';

@Entity()
export class Resource extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  description: string;

  @Column()
  name: string;

  @Column('varchar', { array: true })
  possibleResponses: string[];

  @Column()
  type: string;

  @Column()
  url: string;

  @ManyToOne(() => Question, (question) => question.resources)
  question: Question;
}
