import {
  BaseEntity,
  Column,
  Entity,
  OneToMany,
  PrimaryGeneratedColumn
} from 'typeorm';
import { Question } from './question';

@Entity()
export class Category extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  name: string;

  @Column({ unique: true })
  number: string;

  @Column({ nullable: true })
  shortName: string;

  @OneToMany(() => Question, (question) => question.category)
  questions: Question[];
}
