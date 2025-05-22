#!/usr/bin/env python3
"""
Cache monitoring utility for the agentic workflow.
Provides real-time cache statistics and management.
"""

import requests
import time
import json
import argparse
from datetime import datetime

class CacheMonitor:
    """Monitor and manage cache statistics."""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def get_stats(self):
        """Get current cache statistics."""
        try:
            response = requests.get(f"{self.base_url}/api/cache/stats")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching cache stats: {e}")
            return None
    
    def clear_cache(self):
        """Clear all cache entries."""
        try:
            response = requests.post(f"{self.base_url}/api/cache/clear")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error clearing cache: {e}")
            return None
    
    def get_health(self):
        """Get health status including cache info."""
        try:
            response = requests.get(f"{self.base_url}/api/health")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching health status: {e}")
            return None
    
    def print_stats(self, stats):
        """Pretty print cache statistics."""
        if not stats:
            print("❌ Unable to fetch cache statistics")
            return
        
        print(f"📊 Cache Statistics - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        print(f"Size: {stats['size']}/{stats['max_size']} entries")
        print(f"Hit Rate: {stats['hit_rate_percent']:.1f}%")
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Hits: {stats['hits']}")
        print(f"Misses: {stats['misses']}")
        print(f"Evictions: {stats['evictions']}")
        print(f"Default TTL: {stats['default_ttl']}s")
        
        # Calculate efficiency
        if stats['total_requests'] > 0:
            efficiency = "🟢 Excellent" if stats['hit_rate_percent'] > 70 else \
                        "🟡 Good" if stats['hit_rate_percent'] > 40 else \
                        "🔴 Poor"
            print(f"Efficiency: {efficiency}")
        
        print()
    
    def monitor_live(self, interval=5):
        """Monitor cache statistics in real-time."""
        print("🔄 Starting live cache monitoring (Ctrl+C to stop)")
        print(f"Update interval: {interval} seconds\n")
        
        try:
            while True:
                stats = self.get_stats()
                
                # Clear screen
                print("\033[H\033[J", end="")
                
                self.print_stats(stats)
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped")
    
    def benchmark_cache(self, queries=None):
        """Run a simple cache benchmark."""
        if queries is None:
            queries = [
                "artificial intelligence",
                "machine learning",
                "python programming",
                "web development",
                "data science"
            ]
        
        print("🏃 Running cache benchmark...")
        print(f"Testing {len(queries)} queries\n")
        
        # Get initial stats
        initial_stats = self.get_stats()
        if not initial_stats:
            print("❌ Cannot run benchmark - server not responding")
            return
        
        print(f"Initial cache state: {initial_stats['size']} entries, {initial_stats['hit_rate_percent']:.1f}% hit rate")
        
        # Note: This would require actually making search requests through the API
        # For now, just show how to monitor the cache
        print("\n💡 To see cache in action:")
        print("1. Make some Wikipedia or web searches through the UI")
        print("2. Repeat the same searches to see cache hits")
        print("3. Monitor with: python cache_monitor.py --monitor")

def main():
    parser = argparse.ArgumentParser(description="Cache monitoring utility")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the server")
    parser.add_argument("--monitor", action="store_true", help="Start live monitoring")
    parser.add_argument("--interval", type=int, default=5, help="Monitoring interval in seconds")
    parser.add_argument("--clear", action="store_true", help="Clear cache")
    parser.add_argument("--health", action="store_true", help="Show health status")
    parser.add_argument("--benchmark", action="store_true", help="Run cache benchmark")
    
    args = parser.parse_args()
    
    monitor = CacheMonitor(args.url)
    
    if args.clear:
        print("🧹 Clearing cache...")
        result = monitor.clear_cache()
        if result:
            print(f"✅ {result['message']}")
        return
    
    if args.health:
        print("🔍 Checking health status...")
        health = monitor.get_health()
        if health:
            print(f"Status: {health['status']}")
            print(f"Active conversations: {health['active_conversations']}")
            monitor.print_stats(health['cache'])
        return
    
    if args.benchmark:
        monitor.benchmark_cache()
        return
    
    if args.monitor:
        monitor.monitor_live(args.interval)
        return
    
    # Default: show current stats
    stats = monitor.get_stats()
    monitor.print_stats(stats)

if __name__ == "__main__":
    main()