FROM node:22-bookworm-slim AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_DEBUG=0
ENV FRONTEND_DIST=/frontend/dist
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ /app/
COPY --from=frontend /src/dist /frontend/dist
EXPOSE 8000
CMD ["bash", "start.sh"]
