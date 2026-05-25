#!/usr/bin/env python3
"""
Container Health Monitoring Script for Nativity.ai
Monitors container health and sends alerts

Features:
- Real-time health monitoring
- Slack/Discord notifications
- Automatic restart on failure
- Performance metrics collection
"""

import asyncio
import aiohttp
import docker
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class HealthStatus:
    """Container health status"""
    service_name: str
    status: str
    response_time: float
    timestamp: str
    error: Optional[str] = None


@dataclass
class ContainerStats:
    """Container resource statistics"""
    name: str
    cpu_percent: float
    memory_usage_mb: float
    memory_limit_mb: float
    memory_percent: float
    network_rx_mb: float
    network_tx_mb: float


class HealthMonitor:
    """
    Health monitoring system for Nativity.ai containers
    """
    
    def __init__(self, config_file: str = "monitor-config.json"):
        self.config = self._load_config(config_file)
        self.docker_client = docker.from_env()
        self.session = None
        self.running = False
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('health-monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self, config_file: str) -> dict:
        """Load monitoring configuration"""
        default_config = {
            "services": {
                "api": {
                    "url": "http://localhost:8000/api/health",
                    "timeout": 10,
                    "expected_status": 200,
                    "container_name": "nativity-api-dev"
                },
                "frontend": {
                    "url": "http://localhost:3000",
                    "timeout": 10,
                    "expected_status": 200,
                    "container_name": "nativity-frontend-dev"
                },
                "redis": {
                    "container_name": "nativity-redis-dev",
                    "check_command": ["redis-cli", "ping"]
                },
                "worker": {
                    "container_name": "nativity-worker-dev"
                }
            },
            "monitoring": {
                "check_interval": 30,
                "failure_threshold": 3,
                "restart_on_failure": True,
                "collect_stats": True
            },
            "notifications": {
                "enabled": False,
                "webhook_url": "",
                "channel": "#alerts"
            }
        }
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except FileNotFoundError:
            self.logger.info(f"Config file {config_file} not found, using defaults")
            return default_config
    
    async def start_monitoring(self):
        """Start the health monitoring loop"""
        self.running = True
        self.session = aiohttp.ClientSession()
        
        self.logger.info("🔍 Starting health monitoring...")
        self.logger.info(f"   Monitoring {len(self.config['services'])} services")
        self.logger.info(f"   Check interval: {self.config['monitoring']['check_interval']}s")
        
        failure_counts = {service: 0 for service in self.config['services']}
        
        try:
            while self.running:
                # Check all services
                health_results = await self._check_all_services()
                
                # Process results
                for result in health_results:
                    if result.status == "healthy":
                        failure_counts[result.service_name] = 0
                        self.logger.info(f"✅ {result.service_name}: {result.status} ({result.response_time:.2f}s)")
                    else:
                        failure_counts[result.service_name] += 1
                        self.logger.warning(f"❌ {result.service_name}: {result.status} - {result.error}")
                        
                        # Check if we should restart
                        if (failure_counts[result.service_name] >= self.config['monitoring']['failure_threshold'] and
                            self.config['monitoring']['restart_on_failure']):
                            await self._restart_service(result.service_name)
                            failure_counts[result.service_name] = 0
                
                # Collect container stats
                if self.config['monitoring']['collect_stats']:
                    stats = await self._collect_container_stats()
                    self._log_stats(stats)
                
                # Send notifications if enabled
                if self.config['notifications']['enabled']:
                    await self._send_notifications(health_results)
                
                # Wait for next check
                await asyncio.sleep(self.config['monitoring']['check_interval'])
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Monitoring error: {e}")
        finally:
            await self.stop_monitoring()
    
    async def stop_monitoring(self):
        """Stop monitoring and cleanup"""
        self.running = False
        if self.session:
            await self.session.close()
        self.logger.info("👋 Health monitoring stopped")
    
    async def _check_all_services(self) -> List[HealthStatus]:
        """Check health of all configured services"""
        tasks = []
        
        for service_name, config in self.config['services'].items():
            if 'url' in config:
                # HTTP health check
                tasks.append(self._check_http_service(service_name, config))
            else:
                # Container health check
                tasks.append(self._check_container_service(service_name, config))
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_http_service(self, service_name: str, config: dict) -> HealthStatus:
        """Check HTTP service health"""
        start_time = time.time()
        
        try:
            async with self.session.get(
                config['url'],
                timeout=aiohttp.ClientTimeout(total=config['timeout'])
            ) as response:
                response_time = time.time() - start_time
                
                if response.status == config['expected_status']:
                    return HealthStatus(
                        service_name=service_name,
                        status="healthy",
                        response_time=response_time,
                        timestamp=datetime.utcnow().isoformat()
                    )
                else:
                    return HealthStatus(
                        service_name=service_name,
                        status="unhealthy",
                        response_time=response_time,
                        timestamp=datetime.utcnow().isoformat(),
                        error=f"HTTP {response.status}"
                    )
                    
        except Exception as e:
            response_time = time.time() - start_time
            return HealthStatus(
                service_name=service_name,
                status="unhealthy",
                response_time=response_time,
                timestamp=datetime.utcnow().isoformat(),
                error=str(e)
            )
    
    async def _check_container_service(self, service_name: str, config: dict) -> HealthStatus:
        """Check container-based service health"""
        start_time = time.time()
        
        try:
            container = self.docker_client.containers.get(config['container_name'])
            response_time = time.time() - start_time
            
            if container.status == 'running':
                # Additional command check if specified
                if 'check_command' in config:
                    result = container.exec_run(config['check_command'])
                    if result.exit_code == 0:
                        status = "healthy"
                        error = None
                    else:
                        status = "unhealthy"
                        error = f"Command failed: {result.output.decode()}"
                else:
                    status = "healthy"
                    error = None
            else:
                status = "unhealthy"
                error = f"Container status: {container.status}"
            
            return HealthStatus(
                service_name=service_name,
                status=status,
                response_time=response_time,
                timestamp=datetime.utcnow().isoformat(),
                error=error
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return HealthStatus(
                service_name=service_name,
                status="unhealthy",
                response_time=response_time,
                timestamp=datetime.utcnow().isoformat(),
                error=str(e)
            )
    
    async def _collect_container_stats(self) -> List[ContainerStats]:
        """Collect container resource statistics"""
        stats = []
        
        for service_name, config in self.config['services'].items():
            if 'container_name' not in config:
                continue
                
            try:
                container = self.docker_client.containers.get(config['container_name'])
                
                # Get stats (non-blocking)
                stats_data = container.stats(stream=False)
                
                # Calculate CPU percentage
                cpu_delta = stats_data['cpu_stats']['cpu_usage']['total_usage'] - \
                           stats_data['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats_data['cpu_stats']['system_cpu_usage'] - \
                              stats_data['precpu_stats']['system_cpu_usage']
                
                cpu_percent = 0.0
                if system_delta > 0:
                    cpu_percent = (cpu_delta / system_delta) * 100.0
                
                # Memory stats
                memory_usage = stats_data['memory_stats']['usage']
                memory_limit = stats_data['memory_stats']['limit']
                memory_percent = (memory_usage / memory_limit) * 100.0
                
                # Network stats
                networks = stats_data.get('networks', {})
                rx_bytes = sum(net['rx_bytes'] for net in networks.values())
                tx_bytes = sum(net['tx_bytes'] for net in networks.values())
                
                stats.append(ContainerStats(
                    name=service_name,
                    cpu_percent=cpu_percent,
                    memory_usage_mb=memory_usage / 1024 / 1024,
                    memory_limit_mb=memory_limit / 1024 / 1024,
                    memory_percent=memory_percent,
                    network_rx_mb=rx_bytes / 1024 / 1024,
                    network_tx_mb=tx_bytes / 1024 / 1024
                ))
                
            except Exception as e:
                self.logger.warning(f"Failed to collect stats for {service_name}: {e}")
        
        return stats
    
    def _log_stats(self, stats: List[ContainerStats]):
        """Log container statistics"""
        for stat in stats:
            self.logger.info(
                f"📊 {stat.name}: "
                f"CPU: {stat.cpu_percent:.1f}% | "
                f"Memory: {stat.memory_usage_mb:.1f}MB ({stat.memory_percent:.1f}%) | "
                f"Network: ↓{stat.network_rx_mb:.1f}MB ↑{stat.network_tx_mb:.1f}MB"
            )
    
    async def _restart_service(self, service_name: str):
        """Restart a failed service"""
        self.logger.warning(f"🔄 Restarting service: {service_name}")
        
        try:
            config = self.config['services'][service_name]
            container = self.docker_client.containers.get(config['container_name'])
            
            # Restart container
            container.restart()
            
            # Wait a moment for startup
            await asyncio.sleep(10)
            
            self.logger.info(f"✅ Service {service_name} restarted successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to restart {service_name}: {e}")
    
    async def _send_notifications(self, health_results: List[HealthStatus]):
        """Send notifications for unhealthy services"""
        unhealthy_services = [r for r in health_results if r.status != "healthy"]
        
        if not unhealthy_services:
            return
        
        # Prepare notification message
        message = f"🚨 Nativity.ai Health Alert\n\n"
        for result in unhealthy_services:
            message += f"❌ {result.service_name}: {result.error}\n"
        
        # Send to webhook (Slack/Discord)
        try:
            payload = {
                "text": message,
                "channel": self.config['notifications']['channel']
            }
            
            async with self.session.post(
                self.config['notifications']['webhook_url'],
                json=payload
            ) as response:
                if response.status == 200:
                    self.logger.info("📱 Notification sent successfully")
                else:
                    self.logger.warning(f"Failed to send notification: {response.status}")
                    
        except Exception as e:
            self.logger.error(f"Notification error: {e}")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Nativity.ai Health Monitor')
    parser.add_argument('--config', default='monitor-config.json', help='Configuration file')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    args = parser.parse_args()
    
    monitor = HealthMonitor(args.config)
    
    if args.once:
        # Single health check
        monitor.session = aiohttp.ClientSession()
        try:
            results = await monitor._check_all_services()
            for result in results:
                print(f"{result.service_name}: {result.status}")
                if result.error:
                    print(f"  Error: {result.error}")
        finally:
            await monitor.session.close()
    else:
        # Continuous monitoring
        await monitor.start_monitoring()


if __name__ == "__main__":
    asyncio.run(main())