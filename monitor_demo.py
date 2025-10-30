#!/usr/bin/env python3
"""
Demonstration script for Prometheus metrics and Rich logging integration.
Shows how to monitor the facial processing service with beautiful logging and metrics.
"""

import asyncio
import aiohttp
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.align import Align
from datetime import datetime
import random
import requests

console = Console()

class ServiceMonitor:
    def __init__(self, api_url: str = "http://localhost:8000", metrics_url: str = "http://localhost:8000/metrics"):
        self.api_url = api_url
        self.metrics_url = metrics_url
        self.metrics_data = {}
        
    def fetch_metrics(self):
        """Fetch current Prometheus metrics."""
        try:
            response = requests.get(self.metrics_url, timeout=5)
            if response.status_code == 200:
                return self.parse_metrics(response.text)
            else:
                return None
        except Exception as e:
            console.print(f"[red]Failed to fetch metrics: {e}[/red]")
            return None
    
    def parse_metrics(self, metrics_text: str) -> dict:
        """Parse Prometheus metrics format."""
        metrics = {}
        for line in metrics_text.split('\n'):
            if line.startswith('#') or not line.strip():
                continue
            
            try:
                if ' ' in line:
                    parts = line.rsplit(' ', 1)
                    metric_name_labels = parts[0]
                    value = float(parts[1])
                    
                    if '{' in metric_name_labels:
                        metric_name = metric_name_labels.split('{')[0]
                    else:
                        metric_name = metric_name_labels
                    
                    if metric_name not in metrics:
                        metrics[metric_name] = []
                    metrics[metric_name].append({
                        'labels': metric_name_labels,
                        'value': value
                    })
            except (ValueError, IndexError):
                continue
        
        return metrics
    
    def create_metrics_table(self, metrics: dict) -> Table:
        """Create a rich table showing current metrics."""
        table = Table(title="📊 Live Metrics Dashboard")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta", justify="right")
        table.add_column("Description", style="green")
        
        # Key metrics to display
        key_metrics = {
            'api_requests_total': 'Total API Requests',
            'task_submissions_total': 'Tasks Submitted',
            'task_completions_total': 'Tasks Completed',
            'landmarks_processed_total': 'Landmarks Processed',
            'regions_generated_total': 'Regions Generated',
            'active_tasks_count': 'Active Tasks',
        }
        
        for metric_name, description in key_metrics.items():
            if metric_name in metrics:
                total_value = sum(entry['value'] for entry in metrics[metric_name])
                table.add_row(metric_name, f"{total_value:,.0f}", description)
            else:
                table.add_row(metric_name, "0", description)
        
        return table
    
    def check_health(self) -> dict:
        """Check service health."""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def submit_test_task(self, session: aiohttp.ClientSession) -> str:
        """Submit a test facial processing task."""
        # Generate minimal test data
        test_request = {
            "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
            "landmarks": [{"x": random.uniform(0, 100), "y": random.uniform(0, 100)} for _ in range(478)],
            "segmentation_map": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        }
        
        async with session.post(
            f"{self.api_url}/api/v1/frontal/crop/submit",
            json=test_request,
            params={"show_landmarks": False, "region_opacity": 0.7}
        ) as response:
            if response.status == 200:
                result = await response.json()
                return result.get('task_id', 'unknown')
            else:
                console.print(f"[red]Failed to submit task: {response.status}[/red]")
                return None
    
    def create_status_panel(self, health: dict, metrics_count: int) -> Panel:
        """Create service status panel."""
        status = health.get('status', 'unknown')
        color = "green" if status == "healthy" else "red"
        
        content = f"[{color}]● {status.upper()}[/]\n"
        content += f"[dim]Service:[/] {health.get('service', 'Unknown')}\n"
        content += f"[dim]Version:[/] {health.get('version', 'Unknown')}\n"
        content += f"[dim]Metrics:[/] {metrics_count} collected\n"
        content += f"[dim]Last Update:[/] {datetime.now().strftime('%H:%M:%S')}"
        
        return Panel.fit(
            content,
            title="🚀 Service Status",
            border_style=color
        )
    
    async def run_monitor(self):
        """Run the live monitoring dashboard."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=7),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        with Live(layout, refresh_per_second=2, screen=True):
            while True:
                try:
                    # Fetch current data
                    health = self.check_health()
                    metrics = self.fetch_metrics() or {}
                    
                    # Update layout components
                    layout["header"].update(self.create_status_panel(health, len(metrics)))
                    layout["main"].update(Align.center(self.create_metrics_table(metrics)))
                    layout["footer"].update(
                        Align.center(
                            "[dim]Press Ctrl+C to exit | Refreshing every 2 seconds[/]"
                        )
                    )
                    
                    await asyncio.sleep(2)
                    
                except KeyboardInterrupt:
                    console.print("\n[yellow]Monitoring stopped by user[/yellow]")
                    break
                except Exception as e:
                    console.print(f"[red]Error in monitor: {e}[/red]")
                    await asyncio.sleep(5)

def main():
    """Main function to run the monitoring demo."""
    console.print(Panel.fit(
        "[bold blue]Facial Processing Service Monitor[/]\n"
        "[dim]Real-time monitoring of Prometheus metrics and service health[/]\n"
        "[dim]Make sure the service is running on http://localhost:8000[/]",
        title="🔍 Service Monitor",
        border_style="blue"
    ))
    
    monitor = ServiceMonitor()
    
    # Check if service is available
    health = monitor.check_health()
    if health.get('status') != 'healthy':
        console.print(f"[red]❌ Service is not healthy: {health.get('error', 'Unknown error')}[/red]")
        console.print("[yellow]Please start the service first with: python main.py[/yellow]")
        return
    
    console.print("[green]✅ Service is healthy! Starting monitor...[/green]")
    
    try:
        asyncio.run(monitor.run_monitor())
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Monitor stopped[/yellow]")

if __name__ == "__main__":
    main()