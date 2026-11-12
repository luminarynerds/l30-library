# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
import os
from typing import Dict, List, Optional

from .base_client import ProtocolType, ServerConfig

logger = get_logger(__name__)


class ServerConfigManager:

    def __init__(self):
        self.servers: Dict[str, ServerConfig] = {}
        self._predefined_configs = self._build_predefined_configs()

    # =========================================================================
    # Predefined Server Configurations
    # =========================================================================

    @staticmethod
    def _build_predefined_configs() -> Dict[str, ServerConfig]:
        configs = {}

        # =====================================================================
        # Library of Congress (Z39.50)
        # =====================================================================
        configs["loc_z3950"] = ServerConfig(
            id="loc_z3950",
            name="Library of Congress (Z39.50)",
            host="lx2.loc.gov",
            port=210,
            protocol=ProtocolType.Z3950,
            database="LCDB",
            timeout_seconds=30,
            max_retries=3,
            description="LC's Z39.50 server for bibliographic record searching",
            enabled=False,  # Requires PyZ3950
        )

        # =====================================================================
        # Library of Congress (SRU)
        # =====================================================================
        configs["loc_sru"] = ServerConfig(
            id="loc_sru",
            name="Library of Congress (SRU)",
            host="lx2.loc.gov",
            port=443,
            protocol=ProtocolType.SRU_REST,
            database="sru/lcdb",
            timeout_seconds=30,
            max_retries=3,
            description="LC's SRU interface (lx2 gateway) - public access, no authentication required",
            enabled=True,
        )

        # =====================================================================
        # OCLC WorldCat (SRU)
        # =====================================================================
        configs["oclc_worldcat_sru"] = ServerConfig(
            id="oclc_worldcat_sru",
            name="OCLC WorldCat (SRU)",
            host="www.oclc.org",
            port=443,
            protocol=ProtocolType.SRU_REST,
            database="webservices/sru",
            timeout_seconds=30,
            max_retries=3,
            requires_auth=True,
            description="OCLC WorldCat SRU interface - requires OCLC authentication",
            enabled=False,  # Requires OCLC credentials
        )

        # =====================================================================
        # OCLC WorldCat (Z39.50)
        # =====================================================================
        configs["oclc_worldcat_z3950"] = ServerConfig(
            id="oclc_worldcat_z3950",
            name="OCLC WorldCat (Z39.50)",
            host="z3950.oclc.org",
            port=210,
            protocol=ProtocolType.Z3950,
            database="OLUCWorldCat",
            timeout_seconds=30,
            max_retries=3,
            requires_auth=True,
            description="OCLC WorldCat Z39.50 interface - requires OCLC subscription",
            enabled=False,  # Requires OCLC credentials and PyZ3950
        )

        # =====================================================================
        # GILS (Government Information Locator Service)
        # =====================================================================
        configs["gils_sru"] = ServerConfig(
            id="gils_sru",
            name="GILS SRU Server",
            host="lx2.loc.gov",
            port=443,
            protocol=ProtocolType.SRU_REST,
            database="gils",
            timeout_seconds=30,
            max_retries=3,
            description="Government Information Locator Service (defunct - endpoint returns 404)",
            enabled=False,
        )

        # =====================================================================
        # Library of Congress Name Authority
        # =====================================================================
        configs["loc_name_authority_z3950"] = ServerConfig(
            id="loc_name_authority_z3950",
            name="LC Name Authority (Z39.50)",
            host="lx2.loc.gov",
            port=210,
            protocol=ProtocolType.Z3950,
            database="NAF",  # Name Authority File
            timeout_seconds=30,
            max_retries=3,
            description="LC Name Authority File for author and subject searching",
            enabled=False,  # Requires PyZ3950
        )

        # =====================================================================
        # Consortium of University and Research Libraries (Voyager)
        # =====================================================================
        configs["curl_voyager_z3950"] = ServerConfig(
            id="curl_voyager_z3950",
            name="CURL Voyager (Z39.50)",
            host="z3950.cul.columbia.edu",
            port=210,
            protocol=ProtocolType.Z3950,
            database="voyager",
            timeout_seconds=30,
            max_retries=3,
            description="Columbia University Libraries Voyager system",
            enabled=False,  # Requires PyZ3950
        )

        # =====================================================================
        # British Library (BLPC)
        # =====================================================================
        configs["bl_z3950"] = ServerConfig(
            id="bl_z3950",
            name="British Library (Z39.50)",
            host="blpc.bl.uk",
            port=210,
            protocol=ProtocolType.Z3950,
            database="BLPC-ALL",
            timeout_seconds=30,
            max_retries=3,
            description="British Library Public Catalogue",
            enabled=False,  # Requires PyZ3950
        )

        # =====================================================================
        # Europeana (SRU)
        # =====================================================================
        configs["europeana_sru"] = ServerConfig(
            id="europeana_sru",
            name="Europeana SRU",
            host="www.europeana.eu",
            port=443,
            protocol=ProtocolType.SRU_REST,
            database="api",
            timeout_seconds=30,
            max_retries=3,
            requires_auth=True,
            description="Europeana aggregated digital resources (requires API key)",
            enabled=False,
        )

        return configs

    # =========================================================================
    # Configuration Loading
    # =========================================================================

    def load_from_environment(self) -> None:
        # Try JSON format first
        servers_json = os.getenv("FEDERATED_SEARCH_SERVERS_JSON")
        if servers_json:
            try:
                configs = json.loads(servers_json)
                for config_dict in configs:
                    try:
                        self._register_from_dict(config_dict)
                    except (KeyError, ValueError, TypeError) as e:
                        logger.error(f"Failed to load server config: {e}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse FEDERATED_SEARCH_SERVERS_JSON: {e}")

        # Load predefined servers if enabled
        enable_defaults = os.getenv("FEDERATED_SEARCH_ENABLE_DEFAULTS", "true").lower() == "true"
        if enable_defaults:
            self._load_predefined_defaults()

        # Load individual server configurations
        for key, value in os.environ.items():
            if key.startswith("FEDERATED_SEARCH_SERVER_"):
                try:
                    config_dict = json.loads(value)
                    self._register_from_dict(config_dict)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse {key}: {e}")

        logger.info(f"Loaded {len(self.servers)} federated search servers")

    def load_from_file(self, file_path: str) -> None:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Config file not found: {file_path}")

        with open(file_path, "r") as f:
            configs = json.load(f)

        if isinstance(configs, dict):
            # Single config or dict of configs
            if "id" in configs:
                # Single config
                self._register_from_dict(configs)
            else:
                # Dict of configs
                for server_id, config_dict in configs.items():
                    config_dict["id"] = server_id
                    self._register_from_dict(config_dict)
        elif isinstance(configs, list):
            # Array of configs
            for config_dict in configs:
                self._register_from_dict(config_dict)

        logger.info(f"Loaded {len(self.servers)} servers from {file_path}")

    def _load_predefined_defaults(self) -> None:
        # Register servers from predefined configs
        for server_id, config in self._predefined_configs.items():
            # Check for environment overrides
            env_key = f"FEDERATED_SEARCH_{server_id.upper()}_ENABLED"
            if os.getenv(env_key):
                config.enabled = os.getenv(env_key).lower() == "true"

            # Check for host/port overrides
            host_env = f"FEDERATED_SEARCH_{server_id.upper()}_HOST"
            port_env = f"FEDERATED_SEARCH_{server_id.upper()}_PORT"

            if os.getenv(host_env):
                config.host = os.getenv(host_env)
            if os.getenv(port_env):
                config.port = int(os.getenv(port_env))

            if config.enabled:
                self.servers[server_id] = config

    def _register_from_dict(self, config_dict: Dict) -> None:
        # Extract and convert protocol
        protocol_str = config_dict.get("protocol", "sru_rest")
        try:
            protocol = ProtocolType(protocol_str)
        except ValueError:
            protocol = ProtocolType.SRU_REST

        config = ServerConfig(
            id=config_dict.get("id", "unknown"),
            name=config_dict.get("name", "Unknown Server"),
            host=config_dict.get("host"),
            port=config_dict.get("port", 443),
            protocol=protocol,
            database=config_dict.get("database", ""),
            requires_auth=config_dict.get("requires_auth", False),
            username=config_dict.get("username"),
            password=config_dict.get("password"),
            timeout_seconds=config_dict.get("timeout_seconds", 30),
            max_retries=config_dict.get("max_retries", 3),
            encoding=config_dict.get("encoding", "UTF-8"),
            description=config_dict.get("description", ""),
            enabled=config_dict.get("enabled", True),
        )

        self.register_server(config)

    # =========================================================================
    # Server Registration
    # =========================================================================

    def register_server(self, config: ServerConfig) -> None:
        if not config.id:
            raise ValueError("Server ID is required")

        self.servers[config.id] = config
        logger.debug(f"Registered server: {config.name} ({config.id})")

    def unregister_server(self, server_id: str) -> bool:
        if server_id in self.servers:
            del self.servers[server_id]
            logger.debug(f"Unregistered server: {server_id}")
            return True
        return False

    # =========================================================================
    # Server Query and Management
    # =========================================================================

    def get_server(self, server_id: str) -> Optional[ServerConfig]:
        return self.servers.get(server_id)

    def list_servers(self, enabled_only: bool = True) -> List[ServerConfig]:
        servers = list(self.servers.values())
        if enabled_only:
            servers = [s for s in servers if s.enabled]
        return sorted(servers, key=lambda s: s.name)

    def enable_server(self, server_id: str) -> bool:
        server = self.get_server(server_id)
        if server:
            server.enabled = True
            return True
        return False

    def disable_server(self, server_id: str) -> bool:
        server = self.get_server(server_id)
        if server:
            server.enabled = False
            return True
        return False

    # =========================================================================
    # Server Filtering
    # =========================================================================

    def get_servers_by_protocol(self, protocol: ProtocolType) -> List[ServerConfig]:
        return [s for s in self.list_servers() if s.protocol == protocol]

    def get_servers_by_type(self, protocol_type: str) -> List[ServerConfig]:
        try:
            protocol = ProtocolType(protocol_type)
            return self.get_servers_by_protocol(protocol)
        except ValueError:
            return []

    # =========================================================================
    # Validation and Health
    # =========================================================================

    def validate_config(self, config: ServerConfig) -> List[str]:
        errors = []

        if not config.id:
            errors.append("Server ID is required")

        if not config.name:
            errors.append("Server name is required")

        if not config.host:
            errors.append("Server host is required")

        if config.port < 1 or config.port > 65535:
            errors.append(f"Invalid port: {config.port}")

        if not config.database:
            errors.append("Database name is required")

        if config.timeout_seconds < 1:
            errors.append("Timeout must be positive")

        if config.requires_auth and not config.username:
            errors.append("Username required for authenticated server")

        return errors

    def export_config(self, server_id: str) -> Optional[Dict]:
        server = self.get_server(server_id)
        if not server:
            return None

        return {
            "id": server.id,
            "name": server.name,
            "host": server.host,
            "port": server.port,
            "protocol": str(server.protocol),
            "database": server.database,
            "requires_auth": server.requires_auth,
            "username": server.username if server.requires_auth else None,
            "timeout_seconds": server.timeout_seconds,
            "max_retries": server.max_retries,
            "encoding": server.encoding,
            "description": server.description,
            "enabled": server.enabled,
        }

    def export_all_configs(self) -> List[Dict]:
        return [
            self.export_config(server.id)
            for server in self.list_servers(enabled_only=False)
        ]


# Global instance
config_manager = ServerConfigManager()
