FROM node:22-alpine AS dependencies

WORKDIR /workspace

COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY packages/contracts/package.json packages/contracts/package.json

RUN npm ci

FROM node:22-alpine AS builder

WORKDIR /workspace

COPY --from=dependencies /workspace/node_modules ./node_modules
COPY package.json package-lock.json ./
COPY apps/web ./apps/web
COPY packages ./packages

ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_AUTH_MODE=demo
ARG NEXT_PUBLIC_FIREBASE_API_KEY=
ARG NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
ARG NEXT_PUBLIC_FIREBASE_PROJECT_ID=
ARG NEXT_PUBLIC_FIREBASE_APP_ID=
ARG NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=
ARG NEXT_PUBLIC_DEMO_ENABLED=false
ARG NEXT_PUBLIC_DEMO_EMAIL=
ARG NEXT_PUBLIC_DEMO_PASSWORD=
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_AUTH_MODE=${NEXT_PUBLIC_AUTH_MODE} \
    NEXT_PUBLIC_FIREBASE_API_KEY=${NEXT_PUBLIC_FIREBASE_API_KEY} \
    NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=${NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN} \
    NEXT_PUBLIC_FIREBASE_PROJECT_ID=${NEXT_PUBLIC_FIREBASE_PROJECT_ID} \
    NEXT_PUBLIC_FIREBASE_APP_ID=${NEXT_PUBLIC_FIREBASE_APP_ID} \
    NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=${NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID} \
    NEXT_PUBLIC_DEMO_ENABLED=${NEXT_PUBLIC_DEMO_ENABLED} \
    NEXT_PUBLIC_DEMO_EMAIL=${NEXT_PUBLIC_DEMO_EMAIL} \
    NEXT_PUBLIC_DEMO_PASSWORD=${NEXT_PUBLIC_DEMO_PASSWORD}

RUN npm run web:build

FROM node:22-alpine AS runner

ENV NODE_ENV=production \
    PORT=8080 \
    HOSTNAME=0.0.0.0

WORKDIR /app

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /workspace/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /workspace/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=nextjs:nodejs /workspace/apps/web/public ./apps/web/public

USER nextjs

EXPOSE 8080

CMD ["node", "apps/web/server.js"]
