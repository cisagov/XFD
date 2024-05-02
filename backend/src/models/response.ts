import {
  BaseEntity,
  Column,
  Entity,
  Index,
  ManyToOne,
  PrimaryGeneratedColumn,
  Relation
} from 'typeorm';
import { Assessment, Question } from './index';

@Entity()
@Index(['assessment', 'question'], { unique: true })
export class Response extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  selection: string;

  @ManyToOne(() => Assessment, (assessment) => assessment.responses)
  assessment: Relation<Assessment>;

  @ManyToOne(() => Question, (question) => question.responses)
  question: Relation<Question>;
}
