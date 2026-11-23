FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM alpine:latest
WORKDIR /app
COPY --from=build /app/dist /app/dist
CMD ["cp", "-r", "/app/dist/.", "/srv/frontend/dist/"]
