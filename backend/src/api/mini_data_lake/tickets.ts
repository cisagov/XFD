import { wrapHandler, NotFound, Unauthorized } from '../helpers';
import { connectToDatalake, Ticket } from '../../models';

/**
 * @swagger
 *
 * /mdl/countVulnerabilities/{organizationId}:
 *  get:
 *    description: Return count of vulnerabilities for the logged-in user's organization.
 *    tags:
 *    - Mini Data Lake
 */
export const countVulnerabilities = wrapHandler(async (event) => {
  try {
    const userId = event.requestContext.authorizer!.id;
    if (!userId) {
      return Unauthorized;
    }

    const organizationId = event.pathParameters?.organizationId;
    console.log(`Generating stats for organization: ${organizationId}`);
    const dataLake = await connectToDatalake();
    const ticketRepository = dataLake.getRepository(Ticket);

    const count = await ticketRepository
      .createQueryBuilder('ticket')
      .where(
        'ticket.organizationId = :organizationId AND ticket."vulnSource" = :vulnSource AND ticket."falsePositive" = :falsePositive AND ticket.open = :open',
        {
          organizationId,
          vulnSource: 'nessus',
          falsePositive: 'false',
          open: 'true'
        }
      )
      .getCount();

    return {
      statusCode: 200,
      body: JSON.stringify({ count })
    };
  } catch (error) {
    console.error('Server Error:', error);
    return {
      statusCode: 500,
      body: JSON.stringify({
        error: 'Internal Server Error',
        details: error.message // remove  this line in production
      })
    };
  }
});
