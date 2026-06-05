"""Infrastructure layer: adapters implementing domain ports.

api/        driving adapters (DRF controllers, serializers, urls)
messaging/  outbox writer, relay, PgListener, consumers, delta publisher
repositories.py, langchain_provider.py  driven adapters
container.py  composition root (factory functions per process)
"""
