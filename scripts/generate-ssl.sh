#!/bin/bash
# SSL Certificate Generation Script for Nativity.ai
# Generates self-signed certificates for development/testing

set -e

# Configuration
SSL_DIR="nginx/ssl"
DOMAIN="nativity.local"
COUNTRY="US"
STATE="California"
CITY="San Francisco"
ORG="Nativity.ai"
OU="Development"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔐 SSL Certificate Generator for Nativity.ai${NC}"
echo "=================================================="

# Create SSL directory
mkdir -p $SSL_DIR

# Generate private key
echo -e "${YELLOW}Generating private key...${NC}"
openssl genrsa -out $SSL_DIR/key.pem 2048

# Generate certificate signing request
echo -e "${YELLOW}Generating certificate signing request...${NC}"
openssl req -new -key $SSL_DIR/key.pem -out $SSL_DIR/cert.csr -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/OU=$OU/CN=$DOMAIN"

# Generate self-signed certificate
echo -e "${YELLOW}Generating self-signed certificate...${NC}"
openssl x509 -req -days 365 -in $SSL_DIR/cert.csr -signkey $SSL_DIR/key.pem -out $SSL_DIR/cert.pem

# Set proper permissions
chmod 600 $SSL_DIR/key.pem
chmod 644 $SSL_DIR/cert.pem

# Clean up CSR
rm $SSL_DIR/cert.csr

echo -e "${GREEN}✅ SSL certificates generated successfully!${NC}"
echo ""
echo "Files created:"
echo "  - $SSL_DIR/cert.pem (Certificate)"
echo "  - $SSL_DIR/key.pem (Private Key)"
echo ""
echo "⚠️  Note: These are self-signed certificates for development only."
echo "   For production, use certificates from a trusted CA like Let's Encrypt."
echo ""
echo "To trust the certificate in your browser:"
echo "  1. Open https://localhost in your browser"
echo "  2. Click 'Advanced' -> 'Proceed to localhost (unsafe)'"
echo "  3. Or add the certificate to your system's trusted certificates"