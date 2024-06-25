import {
  BaseEntity,
  BeforeInsert,
  BeforeUpdate,
  Column,
  CreateDateColumn,
  Entity,
  Index,
  OneToMany,
  PrimaryGeneratedColumn,
  UpdateDateColumn
} from 'typeorm';
import { ApiKey } from './api-key';
import { Assessment } from './assessment';
import { Role } from './';

export enum UserType {
  GLOBAL_ADMIN = 'globalAdmin',
  GLOBAL_VIEW = 'globalView',
  REGIONAL_ADMIN = 'regionalAdmin',
  READY_SET_CYBER = 'readySetCyber',
  STANDARD = 'standard'
}
@Entity()
export class User extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Index({ unique: true })
  @Column({
    nullable: true
  })
  cognitoId: string;

  @Index({ unique: true })
  @Column({
    nullable: true
  })
  oktaId: string;

  @Index({ unique: true })
  @Column({
    nullable: true
  })
  loginGovId: string;

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;

  @Column()
  firstName: string;

  @Column()
  lastName: string;

  @Column()
  fullName: string;

  @Index({ unique: true })
  @Column()
  email: string;

  /** Whether the user's invite is pending */
  @Column({ default: false })
  invitePending: boolean;

  /** Whether the user is blocked by maintenance to login */
  @Column({ default: false })
  loginBlockedByMaintenance: boolean;

  /**
   * When the user accepted the terms of use,
   * if the user did so
   */
  @Column({
    type: 'timestamp',
    nullable: true
  })
  dateAcceptedTerms: Date | null;

  @Column({
    type: 'text',
    nullable: true
  })
  acceptedTermsVersion: string | null;

  @Column({
    nullable: true,
    type: 'timestamp'
  })
  lastLoggedIn: Date | null;

  /** The user's type. globalView allows access to all organizations
   * while globalAdmin allows universally administering Crossfeed */
  @Column('text', { default: UserType.STANDARD })
  userType: UserType;

  /** List of the user's API keys */
  @OneToMany((type) => ApiKey, (key) => key.user, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  apiKeys: ApiKey[];

  /** The roles for organizations which the user belongs to */
  @OneToMany((type) => Role, (role) => role.user, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  roles: Role[];

  @BeforeInsert()
  @BeforeUpdate()
  setFullName() {
    this.fullName = this.firstName + ' ' + this.lastName;
  }

  @Column({
    nullable: true
  })
  regionId: string;

  @Column({
    nullable: true
  })
  state: string;

  @OneToMany(() => Assessment, (assessment) => assessment.user)
  assessments: Assessment[];
}
