const dummyType = ['micro/small', 'small/medium', 'medium/large'];

const dummyDate = [0o1 / 0o1 / 2021, 0o1 / 0o2 / 2021, 0o1 / 0o3 / 2021];

const microCategories = [
  {
    id: 1,
    name: 'Identity Access Management'
  },
  {
    id: 2,
    name: 'Device Configuration & Security'
  },
  {
    id: 3,
    name: 'Data Security'
  }
];

const smallToLargeCategories = [
  {
    id: 1,
    name: 'Identity Access Management'
  },
  {
    id: 2,
    name: 'Device Configuration & Security'
  },
  {
    id: 3,
    name: 'Data Security'
  },
  {
    id: 4,
    name: 'Governance & Training'
  },
  {
    id: 5,
    name: 'Vulnerability Management'
  },
  {
    id: 6,
    name: 'Supply Chain Risk Management'
  },
  {
    id: 7,
    name: 'Incident Response'
  }
];

const radialButtons = [
  {
    id: 1,
    name: 'Implemented',
    selected: false
  },
  {
    id: 2,
    name: 'In Progress',
    selected: false
  },
  {
    id: 3,
    name: 'Scoped',
    selected: true
  },
  {
    id: 4,
    name: 'Not in Scope',
    selected: false
  }
];

const dummyQuestions = [
  {
    id: 1,
    title:
      'Does your organization have security controls in place that appropriately identify, authenticate, and authorize users?',
    answers: radialButtons,
    category: 'Identity Access Management'
  },
  {
    id: 2,
    title:
      'Does your system require a minimum password length of 15 characters (including OT systems, where technically feasible)?',
    answers: radialButtons,
    category: 'Identity Access Management'
  },
  {
    id: 3,
    title:
      'Do you log all unsuccessful login attempts and provide security teams with alerts if a certain number of unsuccessful logins occur over a short period of time?',
    answers: radialButtons,
    category: 'Identity Access Management'
  },
  {
    id: 4,
    title:
      'Do you change default passwords on all your IT and OT assets to the maximum extent possible, and implement compensating security controls wherever it is not?',
    answers: radialButtons,
    category: 'Identity Access Management'
  },
  {
    id: 5,
    title:
      'Do you have a process in place to ensure that all devices are configured to the most secure settings possible?',
    answers: radialButtons,
    category: 'Device Configuration & Security'
  },
  {
    id: 6,
    title:
      'Do you have administrative policies or automated processes that ensure all new hardware, firmware, and software are updated with the latest security patches?',
    answers: radialButtons,
    category: 'Device Configuration & Security'
  },
  {
    id: 7,
    title:
      'Are Microsoft Office macros, or similar embedded code, disabled by default?',
    answers: radialButtons,
    category: 'Device Configuration & Security'
  },
  {
    id: 8,
    title:
      'Do you maintain a regulary updated inventory of all organizational assets with an IP address, and update this on a regular basis?',
    answers: radialButtons,
    category: 'Device Configuration & Security'
  }
];
const dummyResults = [
  {
    id: 1,
    type: 'micro/small',
    date: '2021-01-01',
    categories: microCategories,
    questions: dummyQuestions
  },
  {
    id: 2,
    type: 'small/medium',
    date: '2021-01-02',
    categories: smallToLargeCategories,
    questions: dummyQuestions
  },
  {
    id: 3,
    type: 'medium/large',
    date: '2021-01-03',
    categories: smallToLargeCategories,
    questions: dummyQuestions
  },
  {
    id: 4,
    type: 'micro/small',
    date: '2021-01-01',
    categories: microCategories,
    questions: dummyQuestions
  },
  {
    id: 5,
    type: 'small/medium',
    date: '2021-01-02',
    categories: smallToLargeCategories,
    questions: dummyQuestions
  },
  {
    id: 6,
    type: 'medium/large',
    date: '2021-01-03',
    categories: smallToLargeCategories,
    questions: dummyQuestions
  },
  {
    id: 7,
    type: 'micro/small',
    date: '2021-01-01',
    categories: microCategories,
    questions: dummyQuestions
  },
  {
    id: 8,
    type: 'small/medium',
    date: '2021-01-02',
    categories: smallToLargeCategories,
    questions: dummyQuestions
  }
];

export { dummyType, dummyDate, smallToLargeCategories, dummyResults };
