import {
  BaseEntity,
  Column,
  Entity,
  Index,
  JoinTable,
  ManyToMany,
  ManyToOne,
  OneToMany,
  PrimaryGeneratedColumn,
  Relation
} from 'typeorm';
import { Category, Resource, Response } from './index';

@Entity()
@Index(['category', 'number'], { unique: true })
export class Question extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  name: string;

  @Column({ nullable: true })
  description: string;

  @Column()
  longForm: string;

  @Column()
  number: string;

  @ManyToMany(() => Resource, (resource) => resource.questions)
  @JoinTable()
  resources: Relation<Resource>[];

  @ManyToOne(() => Category, (category) => category.questions)
  category: Relation<Category>;

  @OneToMany(() => Response, (response) => response.question)
  responses: Relation<Response>[];
}
