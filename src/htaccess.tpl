# ==========================================================================
# Relais Populaire — configuration du serveur (Apache / IONOS)
# ==========================================================================

Options -Indexes
DirectoryIndex index.html
AddDefaultCharset utf-8
ErrorDocument 404 /404.html

AddType font/woff2 .woff2
AddType application/manifest+json .webmanifest
AddType image/svg+xml .svg

# --- Redirections : HTTPS + adresse sans « www » ---------------------------
<IfModule mod_rewrite.c>
  RewriteEngine On

  RewriteCond %{HTTPS} off [OR]
  RewriteCond %{HTTP_HOST} ^www\. [NC]
  RewriteRule ^ https://relaispopulaire.fr%{REQUEST_URI} [L,R=301]

  # /index.html -> /
  RewriteCond %{THE_REQUEST} \s/+index\.html[\s?] [NC]
  RewriteRule ^index\.html$ / [L,R=301]
</IfModule>

# --- En-têtes de sécurité --------------------------------------------------
<IfModule mod_headers.c>
  Header always set X-Content-Type-Options "nosniff"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
  Header always set X-Frame-Options "SAMEORIGIN"
  Header always set Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
  Header always set Cross-Origin-Opener-Policy "same-origin"
  Header always set Content-Security-Policy "default-src 'self'; img-src 'self' data: https://i.ytimg.com; frame-src https://www.youtube-nocookie.com https://www.youtube.com; script-src 'self' '{{HEAD_SCRIPT_HASH}}'; style-src 'self'; font-src 'self'; connect-src 'self'; manifest-src 'self'; base-uri 'self'; form-action 'self' mailto:; frame-ancestors 'self'; object-src 'none'; upgrade-insecure-requests"
  Header always set Strict-Transport-Security "max-age=31536000" "expr=%{HTTPS} == 'on'"
</IfModule>

# --- Cache navigateur -------------------------------------------------------
<IfModule mod_expires.c>
  ExpiresActive On
  ExpiresDefault "access plus 1 hour"
  ExpiresByType text/html "access plus 0 seconds"
  ExpiresByType text/css "access plus 1 year"
  ExpiresByType application/javascript "access plus 1 year"
  ExpiresByType text/javascript "access plus 1 year"
  ExpiresByType font/woff2 "access plus 1 year"
  ExpiresByType image/svg+xml "access plus 1 month"
  ExpiresByType image/png "access plus 1 month"
  ExpiresByType image/jpeg "access plus 1 month"
  ExpiresByType image/x-icon "access plus 1 month"
  ExpiresByType application/manifest+json "access plus 1 week"
  ExpiresByType application/xml "access plus 1 day"
  ExpiresByType text/xml "access plus 1 day"
</IfModule>

# --- Compression ------------------------------------------------------------
<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE text/html text/css text/plain text/xml application/xml application/javascript text/javascript application/json application/manifest+json image/svg+xml
</IfModule>
