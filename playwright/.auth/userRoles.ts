// playwright/.auth/userRoles.ts

export const userRoles = [
  {
    role: 'global-admin',
    username: process.env.PW_GLOBAL_ADMIN_USERNAME!,
    password: process.env.PW_GLOBAL_ADMIN_PASSWORD!,
    totpSecret: process.env.PW_GLOBAL_ADMIN_2FA_SECRET!
  },
  {
    role: 'regional-admin',
    username: process.env.PW_REGIONAL_ADMIN_USERNAME!,
    password: process.env.PW_REGIONAL_ADMIN_PASSWORD!,
    totpSecret: process.env.PW_REGIONAL_ADMIN_2FA_SECRET!
  },
  {
    role: 'global-view',
    username: process.env.PW_GLOBAL_VIEW_USERNAME!,
    password: process.env.PW_GLOBAL_VIEW_PASSWORD!,
    totpSecret: process.env.PW_GLOBAL_VIEW_2FA_SECRET!
  },
  {
    role: 'standard-user',
    username: process.env.PW_STANDARD_USER_USERNAME!,
    password: process.env.PW_STANDARD_USER_PASSWORD!,
    totpSecret: process.env.PW_STANDARD_USER_2FA_SECRET!
  }
];
