import { get } from 'lodash';

function getValueFacet(aggregations, fieldName) {
  const value = get(aggregations, fieldName);
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
  'from_root_domain',
  'services.port',
  'vulnerabilities.cve',
  'vulnerabilities.severity',
  'organization.name',
  // The following commented-out code is to be used for future .x releases.
  // Returning org id and region id with facets will allow for a full range of dynamic filters.
  // 'organization.id',
  //'organization.region_id',
  'services.products.cpe'
];
export default function buildStateFacets(aggregations) {
  const facets = {};

  for (let facetName of FACETS) {
    const value = getValueFacet(aggregations, facetName);
    if (value) {
      facets[facetName] = value;
    }
  }

  // Special handling for no_services filter aggregation
  if (
    aggregations.no_services &&
    typeof aggregations.no_services.doc_count === 'number'
  ) {
    facets['no_services'] = [
      {
        field: 'no_services',
        type: 'value',
        data: [
          {
            value: true,
            count: aggregations.no_services.doc_count
          }
        ]
      }
    ];
  }

  if (Object.keys(facets).length > 0) {
    return facets;
  }
}
