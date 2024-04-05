import {
    Entity,
    Column,
    PrimaryGeneratedColumn,
    BaseEntity,
    CreateDateColumn,
    UpdateDateColumn
  } from 'typeorm';
  
  @Entity()
  export class Notification extends BaseEntity {
    @PrimaryGeneratedColumn('uuid')
    id: string;
  
    @CreateDateColumn()
    createdAt: Date;

    @UpdateDateColumn()
    updatedAt: Date;
  
    @Column({
      type: 'timestamp',
      nullable: true
    })
    startDatetime: Date | null;

    @Column({
        type: 'timestamp',
        nullable: true
      })
      endDatetime: Date | null;

    @Column({
      nullable: true,
      type: 'varchar'
    })
    maintenanceType: string | null;
  
    @Column({
      nullable: true,
      type: 'varchar'
    })
    status: string | null;

    @Column({
        type: 'timestamp',
        nullable: true
      })
    updatedBy: Date | null;

  }