import {
  BaseEntity,
  Column,
  Entity,
  Index,
  ManyToOne,
  OneToMany,
  PrimaryGeneratedColumn
} from 'typeorm';
import { Category } from './category';
import { Resource } from './resource';
import { Response } from './response';

@Entity()
@Index(['category', 'number'], { unique: true })
export class Question extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  name: string;

  @Column()
  longForm: string;

  @Column()
  number: number;

  @ManyToOne(() => Category, (category) => category.questions)
  category: Category;

  @OneToMany(() => Resource, (resource) => resource.question)
  resources: Resource[];

  @OneToMany(() => Response, (response) => response.question)
  responses: Response[];
}
