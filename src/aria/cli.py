"""Command-line interface for ARIA Hotel AI."""

import asyncio
from pathlib import Path

import typer
import uvicorn
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from aria.core.config import settings
from aria.core.logging import get_logger

logger = get_logger(__name__)
console = Console()
app = typer.Typer(
    name="aria",
    help="ARIA Hotel AI - Command Line Interface",
    add_completion=False,
)


@app.command()
def serve(
    host: str = typer.Option(settings.api_host, "--host", "-h", help="Host to bind"),
    port: int = typer.Option(settings.api_port, "--port", "-p", help="Port to bind"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of workers"),
):
    """Start the ARIA Hotel AI API server."""
    rprint(f"[bold green]Starting ARIA Hotel AI API[/bold green]")
    rprint(f"[dim]Environment: {settings.app_env}[/dim]")
    rprint(f"[dim]Host: {host}:{port}[/dim]")
    
    if settings.is_production and reload:
        rprint("[bold yellow]Warning: Auto-reload disabled in production[/bold yellow]")
        reload = False
    
    uvicorn.run(
        "aria.api.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers if not reload else 1,
        log_level=settings.log_level.lower(),
    )


@app.command()
def info():
    """Show ARIA configuration and status."""
    table = Table(title="ARIA Hotel AI Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    # Basic info
    table.add_row("Environment", settings.app_env)
    table.add_row("Debug Mode", str(settings.app_debug))
    table.add_row("Log Level", settings.log_level)
    
    # API Keys status
    table.add_row("OpenAI API", "✓" if settings.openai_api_key else "✗")
    table.add_row("Groq API", "✓" if settings.groq_api_key else "✗")
    table.add_row("Twilio", "✓" if settings.twilio_account_sid else "✗")
    
    # Features
    table.add_row("Voice Calls", "✓" if settings.enable_voice_calls else "✗")
    table.add_row("Vision Analysis", "✓" if settings.enable_vision_analysis else "✗")
    table.add_row("Proactive Messaging", "✓" if settings.enable_proactive_messaging else "✗")
    
    console.print(table)


@app.command()
def test_whatsapp(
    phone: str = typer.Argument(..., help="Phone number to send test message"),
    message: str = typer.Option("Olá! Este é um teste do sistema ARIA.", help="Test message"),
):
    """Send a test WhatsApp message."""
    async def send_test():
        from aria.integrations.whatsapp import WhatsAppClient
        
        try:
            client = WhatsAppClient()
            message_sid = await client.send_message(phone, message)
            rprint(f"[bold green]✓ Message sent successfully![/bold green]")
            rprint(f"[dim]Message SID: {message_sid}[/dim]")
        except Exception as e:
            rprint(f"[bold red]✗ Failed to send message: {e}[/bold red]")
    
    asyncio.run(send_test())


@app.command()
def test_ana(
    message: str = typer.Argument(..., help="Message to test with Ana"),
    phone: str = typer.Option("+5511999999999", help="Simulated phone number"),
):
    """Test Ana agent with a message."""
    async def test():
        from aria.agents.ana import AnaAgent
        
        try:
            ana = AnaAgent()
            response = await ana.process_message(
                phone=phone,
                message=message
            )
            
            rprint(f"[bold cyan]Ana's Response:[/bold cyan]")
            rprint(response.text)
            
            if response.media_urls:
                rprint(f"\n[dim]Media URLs: {response.media_urls}[/dim]")
            
            if response.action:
                rprint(f"\n[dim]Action: {response.action}[/dim]")
                
        except Exception as e:
            rprint(f"[bold red]✗ Error: {e}[/bold red]")
    
    asyncio.run(test())


@app.command()
def calculate_price(
    check_in: str = typer.Argument(..., help="Check-in date (YYYY-MM-DD)"),
    check_out: str = typer.Argument(..., help="Check-out date (YYYY-MM-DD)"),
    adults: int = typer.Argument(..., help="Number of adults"),
    children: str = typer.Option("", help="Children ages comma-separated (e.g., 5,8)"),
):
    """Calculate accommodation pricing."""
    async def calculate():
        from datetime import datetime
        from aria.agents.ana.calculator import PricingCalculator
        from aria.agents.ana.models import ReservationRequest
        
        try:
            # Parse children ages
            children_ages = []
            if children:
                children_ages = [int(age.strip()) for age in children.split(",")]
            
            # Create request
            request = ReservationRequest(
                check_in=datetime.strptime(check_in, "%Y-%m-%d").date(),
                check_out=datetime.strptime(check_out, "%Y-%m-%d").date(),
                adults=adults,
                children=children_ages
            )
            
            # Calculate
            calculator = PricingCalculator()
            prices = calculator.calculate(request)
            
            # Display results
            table = Table(title=f"Pricing for {request.nights} nights")
            table.add_column("Room Type", style="cyan")
            table.add_column("Meal Plan", style="yellow")
            table.add_column("Total", style="green")
            table.add_column("Per Night", style="dim")
            
            for price in prices:
                table.add_row(
                    price.room_type.value.title(),
                    price.meal_plan.value.replace("_", " ").title(),
                    price.format_price(),
                    f"R$ {price.total_per_night:,.2f}"
                )
            
            console.print(table)
            
        except Exception as e:
            rprint(f"[bold red]✗ Error: {e}[/bold red]")
    
    asyncio.run(calculate())


@app.command()
def init_db():
    """Initialize database schema."""
    rprint("[bold yellow]Database initialization not implemented yet[/bold yellow]")
    # TODO: Implement database initialization


@app.command()
def webhook_url():
    """Show webhook URLs for configuration."""
    base_url = settings.webhook_base_url
    
    table = Table(title="Webhook URLs")
    table.add_column("Service", style="cyan")
    table.add_column("URL", style="green")
    
    table.add_row("WhatsApp", f"{base_url}/webhooks/whatsapp")
    table.add_row("WhatsApp Status", f"{base_url}/webhooks/whatsapp/status")
    table.add_row("Voice", f"{base_url}/webhooks/voice/incoming")
    table.add_row("Voice Status", f"{base_url}/webhooks/voice/status")
    
    console.print(table)
    
    rprint("\n[dim]Configure these URLs in your Twilio console[/dim]")


@app.command()
def version():
    """Show ARIA version."""
    from aria import __version__
    
    rprint(f"[bold cyan]ARIA Hotel AI[/bold cyan] version [green]{__version__}[/green]")


def main():
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()
