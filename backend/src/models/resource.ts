import {
  BaseEntity,
  Column,
  Entity,
  ManyToMany,
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

  @ManyToMany(() => Question, (question) => question.resources)
  questions: Question[];
}
