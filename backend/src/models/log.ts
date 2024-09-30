import { BaseEntity, Column, Entity, PrimaryGeneratedColumn } from 'typeorm';

@Entity()
export class Log extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column('json')
  payload: Object;

  @Column({ nullable: false })
  createdAt: Date;

  @Column({ nullable: true })
  eventType: string;

  @Column({ nullable: false })
  result: string;
}
