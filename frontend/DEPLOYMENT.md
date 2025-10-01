# Deployment Guide - WhatsApp AI SaaS Frontend

Complete guide for deploying the Next.js frontend to production.

## 🚀 Deployment Options

### Option 1: Vercel (Recommended)

Vercel is the fastest and easiest way to deploy Next.js applications.

#### Prerequisites
- GitHub/GitLab/Bitbucket account
- Vercel account (free tier available)

#### Steps

1. **Push to Git Repository**
```bash
cd frontend
git init
git add .
git commit -m "Initial frontend commit"
git remote add origin <your-repo-url>
git push -u origin main
```

2. **Deploy to Vercel**

**Option A: Via Vercel Dashboard**
- Go to [vercel.com](https://vercel.com)
- Click "New Project"
- Import your Git repository
- Framework Preset: Next.js (auto-detected)
- Root Directory: `frontend`
- Configure environment variables:
  ```
  NEXT_PUBLIC_API_URL=https://your-api-domain.com
  ```
- Click "Deploy"

**Option B: Via Vercel CLI**
```bash
npm i -g vercel
cd frontend
vercel
```

3. **Configure Custom Domain** (Optional)
- Go to Project Settings → Domains
- Add your custom domain
- Update DNS records as instructed

#### Environment Variables on Vercel
```env
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

---

### Option 2: Netlify

Another excellent option for Next.js deployment.

#### Steps

1. **Build Configuration**
Create `netlify.toml` in frontend directory:
```toml
[build]
  command = "npm run build"
  publish = ".next"

[[plugins]]
  package = "@netlify/plugin-nextjs"

[build.environment]
  NEXT_PUBLIC_API_URL = "https://api.yourdomain.com"
```

2. **Deploy**
- Push to Git
- Connect repository on Netlify
- Set root directory to `frontend`
- Add environment variables
- Deploy

---

### Option 3: Docker + VPS

For complete control, deploy using Docker on your own VPS.

#### 1. Create Dockerfile

`frontend/Dockerfile`:
```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Set environment variables for build
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Build application
RUN npm run build

# Production stage
FROM node:20-alpine AS runner

WORKDIR /app

# Set NODE_ENV
ENV NODE_ENV=production

# Copy necessary files from builder
COPY --from=builder /app/next.config.ts ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Expose port
EXPOSE 3000

# Start application
CMD ["npm", "start"]
```

#### 2. Create docker-compose.yml

`frontend/docker-compose.yml`:
```yaml
version: '3.8'

services:
  frontend:
    build:
      context: .
      args:
        NEXT_PUBLIC_API_URL: https://api.yourdomain.com
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
    restart: unless-stopped
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```

#### 3. Build and Deploy

```bash
cd frontend

# Build image
docker build \
  --build-arg NEXT_PUBLIC_API_URL=https://api.yourdomain.com \
  -t whatsapp-ai-frontend .

# Run container
docker run -d \
  -p 3000:3000 \
  --name whatsapp-ai-frontend \
  --restart unless-stopped \
  whatsapp-ai-frontend

# Or use docker-compose
docker-compose up -d
```

#### 4. Nginx Reverse Proxy

`/etc/nginx/sites-available/frontend`:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/frontend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 5. SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

### Option 4: AWS Amplify

#### Steps

1. **Push to Git Repository**

2. **Deploy via AWS Amplify**
- Go to AWS Amplify Console
- Connect repository
- Configure build settings:
  ```yaml
  version: 1
  frontend:
    phases:
      preBuild:
        commands:
          - npm ci
      build:
        commands:
          - npm run build
    artifacts:
      baseDirectory: .next
      files:
        - '**/*'
    cache:
      paths:
        - node_modules/**/*
  ```
- Add environment variables
- Deploy

---

## 🔧 Pre-Deployment Checklist

### 1. Environment Variables
- [ ] Set `NEXT_PUBLIC_API_URL` to production API
- [ ] Verify all environment variables are set
- [ ] Remove development-only variables

### 2. Code Optimization
- [ ] Run production build locally: `npm run build`
- [ ] Test production build: `npm start`
- [ ] Check for console errors
- [ ] Verify API calls work with production backend

### 3. Security
- [ ] Update CORS settings in backend for production domain
- [ ] Enable HTTPS
- [ ] Set secure headers
- [ ] Review authentication flow
- [ ] Test token expiration handling

### 4. Performance
- [ ] Enable CDN for static assets
- [ ] Configure caching headers
- [ ] Optimize images
- [ ] Test page load times
- [ ] Run Lighthouse audit

### 5. Monitoring
- [ ] Set up error tracking (Sentry)
- [ ] Configure analytics (Google Analytics)
- [ ] Set up uptime monitoring
- [ ] Configure logging

---

## 🔐 Security Headers

Add security headers to `next.config.ts`:

```typescript
const nextConfig: NextConfig = {
  // ... existing config

  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on'
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload'
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN'
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block'
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin'
          }
        ]
      }
    ];
  }
};
```

---

## 📊 Performance Optimization

### 1. Image Optimization

Update `next.config.ts`:
```typescript
images: {
  domains: ['your-cdn-domain.com'],
  formats: ['image/avif', 'image/webp'],
}
```

### 2. Compression

Enable compression in your server (Nginx example):
```nginx
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;
```

### 3. Caching

Configure caching headers:
```nginx
location /_next/static {
    alias /app/.next/static;
    expires 365d;
    access_log off;
}

location /static {
    alias /app/public;
    expires 365d;
    access_log off;
}
```

---

## 🚨 Monitoring Setup

### Error Tracking with Sentry

1. **Install Sentry**
```bash
npm install @sentry/nextjs
```

2. **Initialize Sentry**
```bash
npx @sentry/wizard@latest -i nextjs
```

3. **Add DSN to environment**
```env
NEXT_PUBLIC_SENTRY_DSN=your-sentry-dsn
```

### Analytics with Google Analytics

Create `src/lib/gtag.ts`:
```typescript
export const GA_TRACKING_ID = process.env.NEXT_PUBLIC_GA_ID;

export const pageview = (url: string) => {
  window.gtag('config', GA_TRACKING_ID, {
    page_path: url,
  });
};
```

---

## 🔄 CI/CD Setup

### GitHub Actions

Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy Frontend

on:
  push:
    branches: [ main ]
    paths:
      - 'frontend/**'

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '20'
        cache: 'npm'
        cache-dependency-path: frontend/package-lock.json

    - name: Install dependencies
      working-directory: ./frontend
      run: npm ci

    - name: Build
      working-directory: ./frontend
      env:
        NEXT_PUBLIC_API_URL: ${{ secrets.API_URL }}
      run: npm run build

    - name: Deploy to Vercel
      working-directory: ./frontend
      run: |
        npm i -g vercel
        vercel --token ${{ secrets.VERCEL_TOKEN }} --prod
```

---

## 🔍 Health Checks

Create a health check endpoint by adding to API client:

```typescript
// src/lib/api-client.ts
async healthCheck() {
  const response = await this.client.get('/health');
  return response.data;
}
```

Set up monitoring to check this endpoint regularly.

---

## 📱 PWA Configuration (Optional)

For Progressive Web App support:

1. **Install next-pwa**
```bash
npm install next-pwa
```

2. **Update next.config.ts**
```typescript
const withPWA = require('next-pwa')({
  dest: 'public',
  disable: process.env.NODE_ENV === 'development'
});

module.exports = withPWA({
  // ... existing config
});
```

---

## 🧪 Testing Before Production

```bash
# Build for production
npm run build

# Test production build locally
npm start

# Run in production mode on different port
PORT=3001 npm start
```

Test these scenarios:
- [ ] User registration
- [ ] User login
- [ ] Dashboard loads
- [ ] All pages accessible
- [ ] Document upload works
- [ ] Settings save correctly
- [ ] AI agent testing works
- [ ] Mobile responsive
- [ ] API calls successful

---

## 🚀 Post-Deployment

### 1. DNS Configuration
Point your domain to deployment:
- Vercel: Add CNAME record
- VPS: Add A record

### 2. SSL Certificate
- Vercel: Automatic
- VPS: Use Let's Encrypt (certbot)

### 3. Monitoring
- Set up uptime monitoring
- Configure error alerts
- Monitor API performance

### 4. Backup
- Regular database backups
- Code repository backups
- Environment variable backups

---

## 📈 Scaling Considerations

### Horizontal Scaling
- Use load balancer (Nginx/HAProxy)
- Deploy multiple instances
- Configure session persistence

### CDN Integration
- Use Vercel Edge Network
- Or configure Cloudflare CDN
- Cache static assets

### Database Optimization
- Connection pooling
- Query optimization
- Caching layer (Redis)

---

## 🐛 Troubleshooting

### Build Errors
```bash
# Clear Next.js cache
rm -rf .next

# Clear node modules
rm -rf node_modules
npm install

# Rebuild
npm run build
```

### API Connection Issues
- Verify CORS settings in backend
- Check NEXT_PUBLIC_API_URL
- Verify SSL certificates
- Check network/firewall rules

### Performance Issues
- Enable Next.js production mode
- Configure CDN
- Optimize images
- Enable compression

---

## 📞 Support

For deployment issues:
1. Check application logs
2. Review Vercel/deployment platform logs
3. Verify environment variables
4. Test API connectivity
5. Check browser console

---

## ✅ Deployment Verification

After deployment, verify:
- [ ] Website loads correctly
- [ ] SSL certificate valid
- [ ] All pages accessible
- [ ] Authentication works
- [ ] API calls successful
- [ ] Mobile responsive
- [ ] No console errors
- [ ] Analytics tracking
- [ ] Error monitoring active

**Congratulations! Your frontend is now deployed! 🎉**
