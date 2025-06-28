import asyncio
import random
from typing import Dict, List
from app.core.config import settings

class CDNService:
    """Service for CDN selection and health monitoring"""

    def __init__(self):
        self.cdn_servers = {
            "cdn1": {
                "name": "US-East",
                "base_latency": 45,
                "variance": 15,
                "load": 0.3,
                "status": "healthy"
            },
            "cdn2": {
                "name": "US-West", 
                "base_latency": 85,
                "variance": 20,
                "load": 0.5,
                "status": "healthy"
            },
            "cdn3": {
                "name": "EU-Central",
                "base_latency": 120,
                "variance": 25,
                "load": 0.2,
                "status": "healthy"
            }
        }

    async def measure_cdn_latency(self, cdn_id: str) -> float:
        """Simulate CDN latency measurement"""
        if cdn_id not in self.cdn_servers:
            return 999.0

        server = self.cdn_servers[cdn_id]
        if server["status"] != "healthy":
            return 999.0

        # Simulate network measurement with random variance
        base = server["base_latency"]
        variance = server["variance"]
        latency = base + random.uniform(-variance, variance)

        # Factor in server load
        load_penalty = server["load"] * 50
        return max(latency + load_penalty, 10.0)

    async def select_optimal_cdn(self, user_location: str = None) -> Dict[str, any]:
        """Select the best CDN based on latency and load"""
        latencies = {}

        # Measure all CDN latencies
        for cdn_id in self.cdn_servers.keys():
            latencies[cdn_id] = await self.measure_cdn_latency(cdn_id)

        # Select CDN with lowest latency
        best_cdn = min(latencies.items(), key=lambda x: x[1])

        return {
            "cdn_id": best_cdn[0],
            "latency": best_cdn[1],
            "server_info": self.cdn_servers[best_cdn[0]],
            "all_latencies": latencies
        }

    def get_cdn_health(self) -> Dict[str, Dict]:
        """Get health status of all CDN servers"""
        return self.cdn_servers.copy()

    def update_cdn_load(self, cdn_id: str, load: float):
        """Update CDN server load"""
        if cdn_id in self.cdn_servers:
            self.cdn_servers[cdn_id]["load"] = max(0.0, min(1.0, load))

    def set_cdn_status(self, cdn_id: str, status: str):
        """Set CDN server status"""
        if cdn_id in self.cdn_servers:
            self.cdn_servers[cdn_id]["status"] = status

# Global CDN service instance
cdn_service = CDNService()
