// The data in this table is derived from IP addresses supplied by the
// CyHy stakeholders.

import {
  Entity,
  Unique,
  Column,
  PrimaryGeneratedColumn,
  BaseEntity,
  OneToMany,
  ManyToOne,
  UpdateDateColumn,
  CreateDateColumn
} from 'typeorm';
import { Domain } from './domains';
import { HostScan } from './host_scans';
import { Host } from './hosts';
import { Organization } from './organizations';
import { Ticket } from './tickets';
import { VulnScan } from './vuln_scans';
import { PortScan } from './port_scans';
@Entity()
@Unique(['ip', 'organization'])
export class Ip extends BaseEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  // TODO Determine if this should be many to many or FK
  @ManyToOne((type) => Organization, (organization) => organization.ips, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  organization: Organization;

  @CreateDateColumn()
  createdTimestamp: Date;

  @UpdateDateColumn()
  updatedTimestamp: Date | null;

  @Column({ nullable: true, type: 'timestamp' })
  lastSeenTimestamp: Date | null;

  @Column({
    nullable: true,
    type: 'inet'
  })
  ip: string | null;

  @Column({ nullable: true })
  live: boolean;

  @Column({ nullable: true })
  falsePositive: boolean;

  @Column({ nullable: true })
  fromCidr: boolean;

  @Column({ nullable: true })
  retired: boolean;

  @OneToMany((type) => Domain, (domain) => domain.ip, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  domains: Domain[];

  @OneToMany((type) => HostScan, (host_scan) => host_scan.ip, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  hostScans: HostScan[];

  @OneToMany((type) => Host, (host) => host.ip, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  hosts: Host[];

  @OneToMany((type) => Ticket, (ticket) => ticket.ip, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  tickets: Ticket[];

  @OneToMany((type) => VulnScan, (vuln_scan) => vuln_scan.ip, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  vulnScans: VulnScan[];

  @OneToMany((type) => PortScan, (port_scan) => port_scan.ip, {
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  })
  portScans: PortScan[];
}
