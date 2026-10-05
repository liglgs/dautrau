FROM node:24-slim AS build
# Keep the project root distinct from the App Router directory (app/).
WORKDIR /workspace/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_VIGILENS_DATA_MODE=api
RUN npm run build

FROM node:24-slim
WORKDIR /workspace/frontend
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY --from=build --chown=node:node /workspace/frontend ./
USER node
EXPOSE 3100
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 CMD node -e "fetch('http://127.0.0.1:3100/').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"
CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0"]
