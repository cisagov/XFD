import { Category, connectToDatabase } from '../models';

async function populateCategoryTable() {
  await connectToDatabase();

  // Check if table is empty
  const count = await Category.count();
  if (count === 0) {
    // Data to be inserted
    const data = [
      { name: 'Landing Page', shortName: 'Landing Page', number: 'A1' },
      {
        name: 'Security Best Practices',
        shortName: 'Best Practices',
        number: 'A2'
      },
      { name: 'Baseline', shortName: 'Baseline', number: 'B1' },
      {
        name: 'Identity and Access Management',
        shortName: 'IAM',
        number: 'C1'
      },
      {
        name: 'Device Configuration and Security',
        shortName: 'Devices',
        number: 'C2'
      },
      { name: 'Data Security', shortName: 'Data', number: 'C3' },
      {
        name: 'Governance and Training',
        shortName: 'Governance',
        number: 'C4'
      },
      { name: 'Vulnerability Management', shortName: 'VM', number: 'C5' },
      { name: 'Supply Chain Risk Management', shortName: 'SCRM', number: 'C6' },
      { name: 'Incident Response', shortName: 'IR', number: 'C7' }
    ];

    // Insert data into the table
  }
}

populateCategoryTable().catch(console.error);
