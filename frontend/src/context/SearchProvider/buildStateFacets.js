import { get } from 'lodash';

function getValueFacet(aggregations, fieldName) {
  const value = get(aggregations, fieldName);
  // console.log('This is the value being accessed inside getValueFacet: ', value);
  if (value?.buckets?.length > 0) {
    return [
      {
        field: fieldName,
        type: 'value',
        data: value.buckets.map((bucket) => ({
          // Boolean values and date values require using `key_as_string`
          value: bucket.key_as_string || bucket.key,
          count: bucket.doc_count
        }))
      }
    ];
  }
  // else if (value?.services?.doc_count?.length > 0) {
  //   return [
  //     {
  //       field: fieldName,
  //       type: 'value',
  //       data: value.doc_count.map((bucket) => ({
  //         // Boolean values and date values require using `key_as_string`
  //         value: bucket.key_as_string || bucket.key,
  //         count: doc_count
  //       }))
  //     }
  //   ];
  // }
}

// function getRangeFacet(aggregations, fieldName) {
//   const value = get(aggregations, fieldName);
//   if (value?.buckets?.length  > 0) {
//     return [
//       {
//         field: fieldName,
//         type: "range",
//         data: value.buckets.map(bucket => ({
//           // Boolean values and date values require using `key_as_string`
//           value: {
//             to: bucket.to,
//             from: bucket.from,
//             name: bucket.key
//           },
//           count: bucket.doc_count
//         }))
//       }
//     ];
//   }
// }

const FACETS = [
  'name',
  'fromRootDomain',
  'services.port',
  'vulnerabilities.cve',
  'vulnerabilities.severity',
  'organization.name',
  'services.products.cpe'
];
export default function buildStateFacets(aggregations) {
  const facets = {};

  for (let facetName of FACETS) {
    // console.log('This is the agg being accessed: ', aggregations);
    // console.log('This is the facet name being accessed: ', facetName);
    const value = getValueFacet(aggregations, facetName);

    // console.log('This is the value being presented: ', value);
    if (value) {
      facets[facetName] = value;
    }
  }

  if (Object.keys(facets).length > 0) {
    console.log('This is the facets being returned: ', facets);
    return facets;
  }
}
