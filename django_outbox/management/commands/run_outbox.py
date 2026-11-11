import signal
import time

from django.core.management.base import BaseCommand

from django_outbox.dispatcher import process_pending


class Command(BaseCommand):
    help = "Deliver pending outbox messages to their webhook endpoints."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Run a single pass and exit.")
        parser.add_argument("--interval", type=float, default=5.0, help="Idle sleep in seconds.")
        parser.add_argument("--batch-size", type=int, default=None)

    def handle(self, *args, **options):
        self._stop = False
        previous = {
            sig: signal.signal(sig, self._request_stop) for sig in (signal.SIGTERM, signal.SIGINT)
        }
        try:
            while not self._stop:
                stats = process_pending(batch_size=options["batch_size"])
                if stats.processed:
                    self.stdout.write(
                        f"delivered={stats.delivered} retried={stats.retried} dead={stats.dead}"
                    )
                if options["once"]:
                    break
                if not stats.processed:
                    time.sleep(options["interval"])
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)

    def _request_stop(self, signum, frame):
        self._stop = True
