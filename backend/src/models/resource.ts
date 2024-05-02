import {
  BaseEntity,
  Column,
  Entity,
  ManyToMany,
  PrimaryGeneratedColumn,
  Relation
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

  @Column()
  type: string;

  @Column({ unique: true })
  url: string;

  @ManyToMany(() => Question, (question) => question.resources)
  questions: Relation<Question>[];
}
