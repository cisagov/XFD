/**
 * Interface for the structure of the incoming data.
 */
interface IncomingDataItem {
  id: string; // e.g., "121.113.220.13|High"
  value: number;
  label: string;
}

/**
 * Interface for the desired simplified structure of the outgoing data.
 */
interface OutgoingDataItem {
  hostName: string;
  value: number; // Represents the count for the specified severity level
}

/**
 * Transforms an array of IncomingDataItem into an array of OutgoingDataItem,
 * aggregating counts for a specific severity level, sorting by that count,
 * and limiting the result to the top 10 entries.
 *
 * @param incomingData An array of objects with 'id', 'value', and 'label' properties.
 * @param targetSeverity The severity level to aggregate and sort by (e.g., 'low', 'medium', 'high', 'critical', 'all').
 * @returns A new array with the top 10 data items, each containing 'hostName' and 'value' (severity count),
 * sorted from highest to lowest based on the specified severity.
 */
export function transformOverviewHostData(
  incomingData: IncomingDataItem[],
  targetSeverity: 'low' | 'medium' | 'high' | 'critical' | 'all'
): OutgoingDataItem[] {
  // Use a Map to store aggregated data, keyed by hostName.
  const aggregatedCounts = new Map<
    string,
    {
      low: number;
      medium: number;
      high: number;
      critical: number;
      all: number;
    }
  >();

  // Iterate over each item in the incoming data array.
  incomingData.forEach((item) => {
    const parts = item.id.split('|');
    if (parts.length !== 2) {
      console.warn(`Skipping malformed ID: ${item.id}`);
      return;
    }

    const hostName = parts[0];
    const severity = parts[1].toLowerCase();

    if (!aggregatedCounts.has(hostName)) {
      aggregatedCounts.set(hostName, {
        low: 0,
        medium: 0,
        high: 0,
        critical: 0,
        all: 0
      });
    }

    const hostCounts = aggregatedCounts.get(hostName)!;

    switch (severity) {
      case 'low':
        hostCounts.low++;
        break;
      case 'medium':
        hostCounts.medium++;
        break;
      case 'high':
        hostCounts.high++;
        break;
      case 'critical':
        hostCounts.critical++;
        break;
      default:
        console.warn(
          `Unknown severity level encountered: ${severity} for host: ${hostName}`
        );
        break;
    }
    hostCounts.all++;
  });

  // Convert the aggregated counts into the desired OutgoingDataItem format.
  const transformedResult: OutgoingDataItem[] = Array.from(
    aggregatedCounts.entries()
  ).map(([hostName, counts]) => ({
    hostName: hostName,
    value: counts[targetSeverity] || 0
  }));

  // Sort the transformed data by 'value' in descending order.
  transformedResult.sort((a, b) => b.value - a.value);

  return transformedResult.slice(0, 10);
}
