import {
  BaseEntity,
  Column,
  Entity,
  ManyToOne,
  PrimaryGeneratedColumn
} from 'typeorm';
import { RscQuestion } from './rsc_question';

@Entity()
export class RscResource extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  description: string;

  @Column()
  name: string;

  @Column()
  type: string;

  @Column()
  url: string;

  @ManyToOne(() => RscQuestion, (question) => question.resources)
  question: RscQuestion;
}
