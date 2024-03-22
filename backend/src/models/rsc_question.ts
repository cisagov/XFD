import {
  BaseEntity,
  Column,
  Entity,
  ManyToOne,
  OneToMany,
  PrimaryGeneratedColumn
} from 'typeorm';
import { RscAssessment } from './rsc_assessment';
import { RscCategory } from './rsc_category';
import { RscResource } from './rsc_resource';

@Entity()
export class RscQuestion extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  name: string;

  @Column()
  longForm: string;

  @Column()
  number: number;

  @ManyToOne(() => RscAssessment, (assessment) => assessment.questions)
  assessment: RscAssessment;

  @ManyToOne(() => RscCategory, (category) => category.questions)
  category: RscCategory;

  @OneToMany(() => RscResource, (resource) => resource.question)
  resources: RscResource[];
}
