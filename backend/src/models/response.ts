import {
  BaseEntity,
  Column,
  Entity,
  Index,
  ManyToOne,
  PrimaryGeneratedColumn
} from 'typeorm';
import { Assessment } from './assessment';
import { Question } from './question';

@Entity()
@Index(['assessment', 'question'], { unique: true })
export class Response extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  text: string;

  @ManyToOne(() => Assessment, (assessment) => assessment.responses)
  assessment: Assessment;

  @ManyToOne(() => Question, (question) => question.responses)
  question: Question;
}
