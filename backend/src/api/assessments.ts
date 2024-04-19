import { validateBody, wrapHandler, NotFound, Unauthorized } from './helpers';
import { Assessment, connectToDatabase } from '../models';
import { isUUID } from 'class-validator';

/**
 * @swagger
 *
 * /assessments:
 *  post:
 *    description: Save an RSC assessment to the XFD database.
 *    tags:
 *    - Assessments
 */
export const createAssessment = wrapHandler(async (event) => {
  const body = await validateBody(Assessment, event.body);

  await connectToDatabase();

  const assessment = Assessment.create(body);
  await Assessment.save(assessment);

  return {
    statusCode: 200,
    body: JSON.stringify(assessment)
  };
});

/**
 * @swagger
 *
 * /assessments:
 *  get:
 *    description: Lists all assessments for the logged-in user.
 *    tags:
 *    - Assessments
 */
export const list = wrapHandler(async (event) => {
  const userId = event.requestContext.authorizer!.id;

  if (!userId) {
    return Unauthorized;
  }

  await connectToDatabase();

  const assessments = await Assessment.findBy({
    user: userId
  });

  return {
    statusCode: 200,
    body: JSON.stringify(assessments)
  };
});

/**
 * @swagger
 *
 * /assessments/{id}:
 *  get:
 *    description: Return user responses and questions organized by category for a specific assessment.
 *    parameters:
 *      - in: path
 *        name: id
 *        description: Assessment id
 *    tags:
 *    - Assessments
 */
export const get = wrapHandler(async (event) => {
  const assessmentId = event.pathParameters?.id;

  if (!assessmentId || !isUUID(assessmentId)) {
    return NotFound;
  }

  await connectToDatabase();

  const assessment = await Assessment.findOne({
    where: { id: assessmentId },
    relations: [
      'responses',
      'responses.question',
      'responses.question.category'
    ]
  });

  if (!assessment) {
    return NotFound;
  }

  const responsesByCategory = assessment.responses.reduce((acc, response) => {
    const categoryName = response.question.category.name;
    if (!acc[categoryName]) {
      acc[categoryName] = [];
    }
    acc[categoryName].push(response);
    return acc;
  }, {});

  return {
    statusCode: 200,
    body: JSON.stringify(responsesByCategory)
  };
});
