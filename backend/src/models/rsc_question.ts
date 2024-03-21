import {
  BaseEntity,
  Column,
  Entity,
  OneToMany,
  PrimaryGeneratedColumn
} from 'typeorm';
import { RscResource } from './rsc_resource';

@Entity()
export class RscQuestion extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  name: string;

  @OneToMany(() => RscResource, (resource) => resource.question)
  resources: RscResource[];
}
