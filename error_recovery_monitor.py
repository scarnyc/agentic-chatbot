#!/usr/bin/env python3
"""
Error recovery monitoring utility for the agentic workflow.
Provides real-time error recovery statistics and circuit breaker status.
"""

import requests
import time
import json
import argparse
from datetime import datetime

class ErrorRecoveryMonitor:
    """Monitor and analyze error recovery statistics."""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def get_stats(self):
        """Get current error recovery statistics."""
        try:
            response = requests.get(f"{self.base_url}/api/error-recovery/stats")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching error recovery stats: {e}")
            return None
    
    def get_health(self):
        """Get health status including error recovery info."""
        try:
            response = requests.get(f"{self.base_url}/api/health")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching health status: {e}")
            return None
    
    def print_stats(self, stats):
        """Pretty print error recovery statistics."""
        if not stats:
            print("❌ Unable to fetch error recovery statistics")
            return
        
        print(f"🔄 Error Recovery Statistics - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Success metrics
        print(f"✅ Success Rate: {stats['success_rate_percent']:.1f}%")
        print(f"📊 Total Attempts: {stats['total_attempts']}")
        print(f"🎯 Successful Calls: {stats['success_count']}")
        print(f"❌ Recent Failures (1h): {stats['recent_failures_1h']}")
        
        # Circuit breaker status
        cb = stats['circuit_breaker']
        cb_status = self._get_circuit_breaker_emoji(cb['state'])
        print(f"🔌 Circuit Breaker: {cb_status} {cb['state']}")
        print(f"⚡ Failure Count: {cb['failure_count']}")
        if cb['last_failure']:
            print(f"🕐 Last Failure: {cb['last_failure']}")
        
        # Failure types
        if stats['failure_types_1h']:
            print("\n🚨 Recent Failure Types (1h):")
            for failure_type, count in stats['failure_types_1h'].items():
                print(f"   {failure_type}: {count}")
        
        # Configuration
        config = stats['retry_config']
        print(f"\n⚙️  Configuration:")
        print(f"   Max Attempts: {config['max_attempts']}")
        print(f"   Base Delay: {config['base_delay']}s")
        print(f"   Max Delay: {config['max_delay']}s")
        
        # Health assessment
        health = self._assess_health(stats)
        print(f"\n💊 Health: {health}")
        
        print()
    
    def _get_circuit_breaker_emoji(self, state):
        """Get emoji for circuit breaker state."""
        if state == "CLOSED":
            return "🟢"
        elif state == "OPEN":
            return "🔴"
        elif state == "HALF_OPEN":
            return "🟡"
        return "⚪"
    
    def _assess_health(self, stats):
        """Assess overall health based on statistics."""
        success_rate = stats['success_rate_percent']
        cb_state = stats['circuit_breaker']['state']
        recent_failures = stats['recent_failures_1h']
        
        if cb_state == "OPEN":
            return "🔴 Critical - Circuit breaker is open"
        elif success_rate < 80:
            return "🟠 Warning - Low success rate"
        elif recent_failures > 10:
            return "🟡 Degraded - High failure rate"
        elif success_rate >= 95:
            return "🟢 Excellent - System stable"
        else:
            return "🟢 Good - System healthy"
    
    def monitor_live(self, interval=10):
        """Monitor error recovery statistics in real-time."""
        print("🔄 Starting live error recovery monitoring (Ctrl+C to stop)")
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
    
    def analyze_trends(self):
        """Analyze error recovery trends over time."""
        print("📈 Error Recovery Trend Analysis")
        print("=" * 40)
        
        # Collect multiple data points
        data_points = []
        print("Collecting data points (30 seconds)...")
        
        for i in range(6):  # 6 points over 30 seconds
            stats = self.get_stats()
            if stats:
                data_points.append({
                    'timestamp': datetime.now(),
                    'success_rate': stats['success_rate_percent'],
                    'failures': stats['recent_failures_1h'],
                    'cb_state': stats['circuit_breaker']['state']
                })
            time.sleep(5)
        
        if not data_points:
            print("❌ Unable to collect trend data")
            return
        
        # Analyze trends
        success_rates = [dp['success_rate'] for dp in data_points]
        failure_counts = [dp['failures'] for dp in data_points]
        
        avg_success = sum(success_rates) / len(success_rates)
        trend = "📈 Improving" if success_rates[-1] > success_rates[0] else \
                "📉 Declining" if success_rates[-1] < success_rates[0] else \
                "➡️  Stable"
        
        print(f"\n📊 Analysis Results:")
        print(f"   Average Success Rate: {avg_success:.1f}%")
        print(f"   Trend: {trend}")
        print(f"   Latest Failure Count: {failure_counts[-1]}")
        
        # Recommendations
        if avg_success < 85:
            print("\n💡 Recommendations:")
            print("   - Check API key validity")
            print("   - Monitor rate limiting")
            print("   - Consider increasing retry delays")
        elif any(dp['cb_state'] == 'OPEN' for dp in data_points):
            print("\n💡 Recommendations:")
            print("   - Circuit breaker activated - investigate root cause")
            print("   - Check external service status")
            print("   - Review error logs")

def main():
    parser = argparse.ArgumentParser(description="Error recovery monitoring utility")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the server")
    parser.add_argument("--monitor", action="store_true", help="Start live monitoring")
    parser.add_argument("--interval", type=int, default=10, help="Monitoring interval in seconds")
    parser.add_argument("--health", action="store_true", help="Show health status")
    parser.add_argument("--trends", action="store_true", help="Analyze error recovery trends")
    
    args = parser.parse_args()
    
    monitor = ErrorRecoveryMonitor(args.url)
    
    if args.health:
        print("🔍 Checking health status...")
        health = monitor.get_health()
        if health:
            print(f"Status: {health['status']}")
            print(f"Active conversations: {health['active_conversations']}")
            monitor.print_stats(health['error_recovery'])
        return
    
    if args.trends:
        monitor.analyze_trends()
        return
    
    if args.monitor:
        monitor.monitor_live(args.interval)
        return
    
    # Default: show current stats
    stats = monitor.get_stats()
    monitor.print_stats(stats)

if __name__ == "__main__":
    main()