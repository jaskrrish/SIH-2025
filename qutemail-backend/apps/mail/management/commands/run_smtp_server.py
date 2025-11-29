"""
Django management command to run SMTP server.

Usage:
    python manage.py run_smtp_server            # Run all servers (MTA + MSA + SMTPS)
    python manage.py run_smtp_server --mta-only # Run only MTA (port 25)
    python manage.py run_smtp_server --msa-only # Run only MSA (ports 587/465)
"""

import signal
import sys
import logging
from django.core.management.base import BaseCommand
from infra.smtp_server import SMTPServerManager

logger = logging.getLogger('smtp_server')


class Command(BaseCommand):
    help = 'Run SMTP server (MTA + MSA + SMTPS)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mta-only',
            action='store_true',
            help='Run only MTA server (port 25)'
        )
        parser.add_argument(
            '--msa-only',
            action='store_true',
            help='Run only MSA servers (ports 587/465)'
        )

    def handle(self, *args, **options):
        """Main command handler"""

        # Initialize server manager
        manager = SMTPServerManager()

        # Setup signal handlers for graceful shutdown
        def signal_handler(sig, frame):
            self.stdout.write(self.style.WARNING('\nShutting down SMTP servers...'))
            manager.stop_all()
            self.stdout.write(self.style.SUCCESS('SMTP servers stopped'))
            sys.exit(0)

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start appropriate servers based on options
        try:
            self.stdout.write(self.style.SUCCESS('Starting SMTP servers...'))

            if options['mta_only']:
                self.stdout.write('Mode: MTA only (port 25)')
                manager.start_mta()
                self.stdout.write(self.style.SUCCESS('MTA server started on port 25'))

            elif options['msa_only']:
                self.stdout.write('Mode: MSA only (ports 587/465)')
                manager.start_msa()
                manager.start_smtps()
                self.stdout.write(self.style.SUCCESS('MSA servers started on ports 587/465'))

            else:
                self.stdout.write('Mode: All servers (MTA + MSA)')
                manager.start_all()
                self.stdout.write(self.style.SUCCESS('All SMTP servers started:'))
                self.stdout.write('  - MTA:   port 25  (receiving external emails)')
                self.stdout.write('  - MSA:   port 587 (authenticated submission with STARTTLS)')
                self.stdout.write('  - SMTPS: port 465 (authenticated submission with implicit TLS)')

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('SMTP servers are running'))
            self.stdout.write(self.style.WARNING('Press Ctrl+C to stop'))
            self.stdout.write('')

            # Keep the process alive
            signal.pause()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error starting SMTP servers: {str(e)}'))
            logger.error(f'Failed to start SMTP servers: {str(e)}', exc_info=True)
            manager.stop_all()
            sys.exit(1)
