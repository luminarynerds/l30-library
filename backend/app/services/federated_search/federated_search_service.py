# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import contextlib
from app.core.logging import get_logger
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .base_client import (
    BaseSearchClient,
    ClientError,
    NormalizedSearchResult,
    ProtocolType,
    ServerConfig,
)
from .config_manager import config_manager
from .deduplication import DeduplicationEngine
from .local_client import LocalCatalogClient
from .sru_client import SRUClient, SRUQueryBuilder
from .z3950_client import Z3950Client

logger = get_logger(__name__)


@dataclass
class SourceStatus:
    source_id: str
    source_name: str
    status: str = "pending"  # pending | searching | completed | error | timeout
    result_count: int = 0
    error_message: Optional[str] = None
    elapsed_ms: float = 0.0


@dataclass
class FederatedSearchResponse:
    results: List[Dict[str, Any]] = field(default_factory=list)
    total_results: int = 0
    sources_queried: int = 0
    sources_succeeded: int = 0
    source_statuses: List[Dict[str, Any]] = field(default_factory=list)
    deduplicated_count: int = 0
    elapsed_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "results": self.results,
            "total_results": self.total_results,
            "sources_queried": self.sources_queried,
            "sources_succeeded": self.sources_succeeded,
            "source_statuses": self.source_statuses,
            "deduplicated_count": self.deduplicated_count,
            "elapsed_ms": round(self.elapsed_ms, 1),
        }


def _create_client(config: ServerConfig, db: Optional[AsyncSession] = None) -> Optional[BaseSearchClient]:
    try:
        if config.protocol == ProtocolType.Z3950:
            return Z3950Client(config)
        elif config.protocol in (ProtocolType.SRU_REST, ProtocolType.SRU_SOAP, ProtocolType.SRU):
            return SRUClient(config)
        else:
            logger.warning("Unsupported protocol %s for %s", config.protocol, config.id)
            return None
    except Exception as e:  # noqa: BLE001  # client factory boundary - skip misconfigured source not crash search
        logger.warning("Failed to create client for %s: %s", config.id, e)
        return None


class FederatedSearchService:

    def __init__(
        self,
        db: AsyncSession,
        source_timeout: float = 15.0,
        overall_timeout: float = 30.0,
        include_local: bool = True,
        source_ids: Optional[List[str]] = None,
    ):
        self.db = db
        self.source_timeout = source_timeout
        self.overall_timeout = overall_timeout
        self.include_local = include_local
        self.source_ids = source_ids
        self.dedup_engine = DeduplicationEngine()

    async def search(
        self,
        query: Optional[str] = None,
        isbn: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        max_results_per_source: int = 10,
    ) -> FederatedSearchResponse:
        start = time.monotonic()
        all_results: List[NormalizedSearchResult] = []
        statuses: List[SourceStatus] = []

        # Build list of clients to query
        clients = await self._build_clients()

        if not clients:
            return FederatedSearchResponse(
                elapsed_ms=(time.monotonic() - start) * 1000
            )

        # Fan-out: search all sources concurrently with per-source timeouts
        tasks = []
        for client_info in clients:
            task = self._search_source(
                client_info["client"],
                query=query, isbn=isbn, title=title, author=author,
                max_results=max_results_per_source,
            )
            tasks.append((client_info, task))

        # Execute with overall timeout
        try:
            coros = [t for _, t in tasks]
            results_list = await asyncio.wait_for(
                asyncio.gather(*coros, return_exceptions=True),
                timeout=self.overall_timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("Overall federated search timeout (%.1fs)", self.overall_timeout)
            results_list = [asyncio.TimeoutError() for _ in tasks]

        # Process results from each source
        for i, (client_info, _) in enumerate(tasks):
            source_status = SourceStatus(
                source_id=client_info["config"].id,
                source_name=client_info["config"].name,
            )

            result = results_list[i] if i < len(results_list) else asyncio.TimeoutError()

            if isinstance(result, asyncio.TimeoutError):
                source_status.status = "timeout"
                source_status.error_message = "Search timed out"
            elif isinstance(result, Exception):
                source_status.status = "error"
                source_status.error_message = str(result)
                logger.warning("Source %s error: %s", client_info["config"].id, result)
            else:
                source_status.status = "completed"
                source_status.result_count = len(result)
                all_results.extend(result)

            statuses.append(source_status)

        # Disconnect all clients; cleanup must not break response delivery.
        for client_info in clients:
            with contextlib.suppress(Exception):  # noqa: BLE001 - disconnect cleanup must not break response delivery
                await client_info["client"].disconnect()

        # Deduplicate
        original_count = len(all_results)
        merged_results = self.dedup_engine.deduplicate_and_merge(all_results)
        deduplicated_count = original_count - len(merged_results)

        elapsed_ms = (time.monotonic() - start) * 1000

        return FederatedSearchResponse(
            results=[r.to_dict() for r in merged_results],
            total_results=len(merged_results),
            sources_queried=len(clients),
            sources_succeeded=sum(1 for s in statuses if s.status == "completed"),
            source_statuses=[
                {
                    "source_id": s.source_id,
                    "source_name": s.source_name,
                    "status": s.status,
                    "result_count": s.result_count,
                    "error_message": s.error_message,
                    "elapsed_ms": round(s.elapsed_ms, 1),
                }
                for s in statuses
            ],
            deduplicated_count=deduplicated_count,
            elapsed_ms=elapsed_ms,
        )

    async def _build_clients(self) -> List[Dict[str, Any]]:
        clients = []

        # Always include local catalog first
        if self.include_local:
            local_client = LocalCatalogClient(self.db)
            clients.append({
                "client": local_client,
                "config": local_client.config,
            })

        # Load configured external sources
        config_manager.load_from_environment()
        servers = config_manager.list_servers(enabled_only=True)

        # Filter by source_ids if specified
        if self.source_ids:
            servers = [s for s in servers if s.id in self.source_ids]

        for server_config in servers:
            client = _create_client(server_config, self.db)
            if client:
                clients.append({
                    "client": client,
                    "config": server_config,
                })

        return clients

    async def _search_source(
        self,
        client: BaseSearchClient,
        query: Optional[str] = None,
        isbn: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        max_results: int = 10,
    ) -> List[NormalizedSearchResult]:
        try:
            await client.connect()

            # Use structured search if available
            if hasattr(client, "search_by_fields") and (isbn or title or author):
                return await asyncio.wait_for(
                    client.search_by_fields(
                        isbn=isbn, title=title, author=author,
                        max_results=max_results,
                    ),
                    timeout=self.source_timeout,
                )

            # Fall back to query string search
            search_query = query
            if not search_query:
                # Build a query from the fields
                search_query = SRUQueryBuilder.build_cql_query(
                    isbn=isbn, title=title, author=author,
                )

            return await asyncio.wait_for(
                client.search(search_query, max_results),
                timeout=self.source_timeout,
            )

        except asyncio.TimeoutError:
            raise
        except ClientError:
            raise
        except Exception as e:
            raise ClientError(f"Search failed: {e}") from e

    async def get_source_health(self) -> List[Dict[str, Any]]:
        clients = await self._build_clients()
        health = []

        for client_info in clients:
            client = client_info["client"]
            config = client_info["config"]
            start = time.monotonic()

            try:
                await asyncio.wait_for(client.connect(), timeout=5.0)
                elapsed = (time.monotonic() - start) * 1000
                health.append({
                    "source_id": config.id,
                    "source_name": config.name,
                    "status": "healthy",
                    "response_time_ms": round(elapsed, 1),
                })
                await client.disconnect()
            except Exception as e:  # noqa: BLE001  # health probe records any external source failure as unhealthy
                elapsed = (time.monotonic() - start) * 1000
                health.append({
                    "source_id": config.id,
                    "source_name": config.name,
                    "status": "unhealthy",
                    "error": str(e),
                    "response_time_ms": round(elapsed, 1),
                })

        return health
