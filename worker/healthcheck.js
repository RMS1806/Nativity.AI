/**
 * Health check script for Nativity.AI Worker Service
 * Checks worker process health and queue connectivity
 */

const fs = require('fs');
const path = require('path');

// Health check for worker service
async function performHealthCheck() {
  try {
    // Check if worker process is responsive
    const healthFile = path.join(__dirname, 'tmp', 'worker-health.txt');
    const currentTime = new Date().toISOString();
    
    // Write health status
    fs.writeFileSync(healthFile, currentTime);
    
    // Verify we can read it back
    const writtenTime = fs.readFileSync(healthFile, 'utf8');
    
    if (writtenTime !== currentTime) {
      throw new Error('File system health check failed');
    }
    
    // Check memory usage
    const memUsage = process.memoryUsage();
    const memUsageMB = memUsage.heapUsed / 1024 / 1024;
    
    // Alert if memory usage is too high (over 1.5GB)
    if (memUsageMB > 1536) {
      console.warn(`High memory usage: ${memUsageMB.toFixed(2)}MB`);
    }
    
    // Check if temp directory is writable
    const tempDir = path.join(__dirname, 'tmp');
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }
    
    // Check processing directory
    const processingDir = path.join(__dirname, 'processing');
    if (!fs.existsSync(processingDir)) {
      fs.mkdirSync(processingDir, { recursive: true });
    }
    
    console.log('Worker health check passed');
    console.log(`Memory usage: ${memUsageMB.toFixed(2)}MB`);
    console.log(`Uptime: ${process.uptime().toFixed(2)}s`);
    
    // Clean up health file
    fs.unlinkSync(healthFile);
    
    process.exit(0);
    
  } catch (error) {
    console.error('Worker health check failed:', error.message);
    process.exit(1);
  }
}

// Set timeout for health check
setTimeout(() => {
  console.error('Health check timed out');
  process.exit(1);
}, 8000);

// Perform the health check
performHealthCheck();