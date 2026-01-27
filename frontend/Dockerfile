FROM node:20.19.4-alpine

# Define arguments that we will pass from docker-compose
# We set default values (1000) just in case the args aren't passed.
ARG USER_ID=1000
ARG GROUP_ID=1000

USER root

# 1. Install 'shadow' so we can use the 'usermod' and 'groupmod' commands.
#    Also run your standard updates.
RUN apk update && apk upgrade && apk add --no-cache shadow

# 2. Modify the built-in 'node' user to match YOUR local UID/GID.
#    This makes the 'node' user inside the container essentially a clone of YOU.
RUN groupmod -g ${GROUP_ID} node && \
    usermod -u ${USER_ID} -g ${GROUP_ID} node

# 3. Global installs (still as root)
RUN npm install -g npm@9 --legacy-peer-deps

# 4. Prepare the directory
WORKDIR /app
RUN chown node:node /app

# --- SWITCH TO YOUR USER ---
USER node

# 5. Copy manifest files
# Because we updated the 'node' user's ID above, these files are now
# owned by YOUR UID, not a generic 1000.
COPY --chown=node:node ./package* ./
COPY --chown=node:node patches/ ./patches

# 6. Install dependencies (runs as You)
RUN npm ci --legacy-peer-deps

# 7. Copy the rest (runs as You)
COPY --chown=node:node . .

EXPOSE 3000

CMD [ "npm", "run", "dev" ]
