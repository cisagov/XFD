import {
  BaseEntity,
  Column,
  Entity,
  Index,
  JoinTable,
  ManyToMany,
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

  @Column({ nullable: true })
  description: string;

  @Column()
  longForm: string;

  @Column()
  number: string;

  @ManyToMany(() => Resource, (resource) => resource.questions)
  @JoinTable()
  resources: Resource[];

  @ManyToOne(() => Category, (category) => category.questions)
  category: Category;

  @OneToMany(() => Response, (response) => response.question)
  responses: Response[];
}
