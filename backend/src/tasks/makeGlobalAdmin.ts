import { Handler } from 'aws-lambda';
import { connectToDatabase, User, UserType } from '../models';

export const handler: Handler = async (event) => {
  await connectToDatabase(true);
  if (event.email) {
    const user = await User.findOneBy({
      email: event.email
    });
    if (user) {
      user.userType = event.role || UserType.GLOBAL_ADMIN;
      await User.save(user);
    }
  }
};
