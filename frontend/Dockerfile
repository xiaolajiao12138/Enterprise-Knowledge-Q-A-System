# 阶段一：前端静态资源构建
FROM node:20-alpine as builder

WORKDIR /app

COPY package.json ./
RUN npm install --registry=https://registry.npmmirror.com

COPY . ./
RUN npm run build

# 阶段二：生产环境 Nginx 镜像
FROM nginx:alpine

# 复制前端编译产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 反代配置
COPY ../nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
