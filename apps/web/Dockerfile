FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
COPY apps/web/package.json ./apps/web/
RUN npm ci -w apps/web 2>/dev/null || npm install -w apps/web
COPY apps/web ./apps/web
ARG VITE_API_URL=
ARG VITE_WS_URL=
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL
RUN npm run build -w apps/web

FROM nginx:alpine
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY apps/web/docker-entrypoint.sh /start.sh
RUN chmod +x /start.sh
COPY --from=build /app/apps/web/dist /usr/share/nginx/html
EXPOSE 80
ENTRYPOINT ["/start.sh"]
