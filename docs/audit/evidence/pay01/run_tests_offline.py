import os
import socket
import sys

# Harness local : aucune connexion TCP/IP possible, y compris télémétrie.
os.environ['SENTRY_DSN'] = ''
os.environ['OTEL_SDK_DISABLED'] = 'true'
os.environ['OTEL_EXPORTER_OTLP_ENDPOINT'] = ''
_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex

def offline_connect(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        raise RuntimeError('Offline test harness forbids TCP/IP connections')
    return _original_connect(self, address)

def offline_connect_ex(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        raise RuntimeError('Offline test harness forbids TCP/IP connections')
    return _original_connect_ex(self, address)

socket.socket.connect = offline_connect
socket.socket.connect_ex = offline_connect_ex


def main():
    import pytest

    return pytest.main(sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main())
