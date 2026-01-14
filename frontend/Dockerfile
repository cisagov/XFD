FROM node:20.19.4-alpine
USER root

RUN apk update && apk upgrade

WORKDIR /app

COPY ./package* ./

COPY patches/ ./patches

RUN npm install -g npm@9 --legacy-peer-deps

RUN npm ci --legacy-peer-deps

COPY . .

EXPOSE 3000

CMD [ "npm", "run", "dev" ]
