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
    title: 'What is the best way to secure your data?',
    answers: radialButtons
  },
  {
    id: 2,
    title: 'Do you need to use a VPN to secure your data?',
    answers: radialButtons
  },
  {
    id: 3,
    title: 'How often should you update your passwords?',
    answers: radialButtons
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
