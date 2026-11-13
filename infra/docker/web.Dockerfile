FROM node:24-alpine AS builder
RUN npm install --global pnpm@11.25.0
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
RUN pnpm install --frozen-lockfile
COPY apps/web ./apps/web
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

FROM node:24-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
RUN addgroup --system --gid 1001 ficka && adduser --system --uid 1001 --ingroup ficka ficka
COPY --from=builder --chown=ficka:ficka /app/apps/web/.next/standalone ./
COPY --from=builder --chown=ficka:ficka /app/apps/web/.next/static ./apps/web/.next/static
USER ficka
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
