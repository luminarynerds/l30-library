# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import contextlib
import ftplib
import io
from app.core.logging import get_logger
import os
import ssl
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import paramiko

from app.models.edi import TransportProtocol, VendorEDIProfile

logger = get_logger(__name__)


@dataclass
class TransportResult:
    success: bool
    message: str
    filename: str | None = None
    file_path: str | None = None
    error: str | None = None
    bytes_transferred: int = 0
    latency_ms: float | None = None
    auth_status: str | None = None


@dataclass
class FileInfo:
    filename: str
    size: int
    modified_time: datetime | None = None
    is_directory: bool = False


class EDITransport:

    def __init__(self, profile: VendorEDIProfile):
        self.profile = profile
        self.protocol = profile.transport_protocol
        self.host = profile.transport_host
        self.port = profile.transport_port
        self.username = profile.transport_username
        self.password = profile.transport_password
        self.ssh_key = profile.ssh_private_key
        self.outbound_dir = profile.transport_directory_outbound
        self.inbound_dir = profile.transport_directory_inbound

        # Set default ports
        if self.port is None:
            if self.protocol == TransportProtocol.SFTP:
                self.port = 22
            elif self.protocol == TransportProtocol.FTPS:
                self.port = 990
            else:
                self.port = 21

    async def test_connection(self) -> TransportResult:
        try:
            if self.protocol == TransportProtocol.SFTP:
                return await self._test_sftp_connection()
            elif self.protocol in [TransportProtocol.FTP, TransportProtocol.FTPS]:
                return await self._test_ftp_connection()
            else:
                return TransportResult(
                    success=False,
                    message=f"Unsupported protocol: {self.protocol}",
                    error=f"Protocol {self.protocol} is not supported"
                )
        except Exception as e:
            logger.exception(f"Connection test failed: {e}")
            return TransportResult(
                success=False,
                message="Connection test failed",
                error=str(e)
            )

    async def _test_sftp_connection(self) -> TransportResult:
        import time

        def _connect():
            import time
            start_time = time.time()
            transport = None
            auth_status = "pending"

            try:
                transport = paramiko.Transport((self.host, self.port))

                if self.ssh_key:
                    # Load private key
                    key_file = io.StringIO(self.ssh_key)
                    try:
                        pkey = paramiko.RSAKey.from_private_key(key_file)
                    except paramiko.SSHException:
                        key_file.seek(0)
                        pkey = paramiko.Ed25519Key.from_private_key(key_file)
                    transport.connect(username=self.username, pkey=pkey)
                    auth_status = "authenticated_with_key"
                else:
                    transport.connect(username=self.username, password=self.password)
                    auth_status = "authenticated_with_password"

                sftp = paramiko.SFTPClient.from_transport(transport)

                # Test directory access; absence is fine, we just need
                # to confirm we can issue the call.
                with contextlib.suppress(FileNotFoundError):
                    sftp.listdir(self.outbound_dir)

                sftp.close()
                transport.close()

                latency_ms = (time.time() - start_time) * 1000
                return True, "SFTP connection successful", latency_ms, auth_status
            except Exception as e:
                if transport:
                    transport.close()
                latency_ms = (time.time() - start_time) * 1000
                raise e from e

        success, message, latency_ms, auth_status = await asyncio.get_event_loop().run_in_executor(
            None, _connect
        )
        return TransportResult(
            success=success,
            message=message,
            latency_ms=latency_ms,
            auth_status=auth_status
        )

    async def _test_ftp_connection(self) -> TransportResult:
        import time

        def _connect():
            import time
            start_time = time.time()
            auth_status = "pending"

            try:
                if self.protocol == TransportProtocol.FTPS:
                    context = ssl.create_default_context()
                    ftp = ftplib.FTP_TLS(context=context)
                else:
                    ftp = ftplib.FTP()

                ftp.connect(self.host, self.port, timeout=30)
                ftp.login(self.username, self.password or "")
                auth_status = "authenticated_with_password"

                if self.protocol == TransportProtocol.FTPS:
                    ftp.prot_p()  # Switch to secure data connection

                # Test directory access; missing dir is fine for the probe.
                with contextlib.suppress(ftplib.error_perm):
                    ftp.cwd(self.outbound_dir)

                ftp.quit()

                latency_ms = (time.time() - start_time) * 1000
                return True, "FTP connection successful", latency_ms, auth_status
            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                raise e from e

        success, message, latency_ms, auth_status = await asyncio.get_event_loop().run_in_executor(
            None, _connect
        )
        return TransportResult(
            success=success,
            message=message,
            latency_ms=latency_ms,
            auth_status=auth_status
        )

    async def upload_file(
        self,
        content: str,
        filename: str,
        directory: str | None = None
    ) -> TransportResult:
        if directory is None:
            directory = self.outbound_dir

        try:
            if self.protocol == TransportProtocol.SFTP:
                return await self._upload_sftp(content, filename, directory)
            elif self.protocol in [TransportProtocol.FTP, TransportProtocol.FTPS]:
                return await self._upload_ftp(content, filename, directory)
            else:
                return TransportResult(
                    success=False,
                    message=f"Unsupported protocol: {self.protocol}",
                    error=f"Protocol {self.protocol} is not supported"
                )
        except Exception as e:
            logger.exception(f"Upload failed: {e}")
            return TransportResult(
                success=False,
                message="Upload failed",
                filename=filename,
                error=str(e)
            )

    async def _upload_sftp(
        self,
        content: str,
        filename: str,
        directory: str
    ) -> TransportResult:
        def _upload():
            transport = paramiko.Transport((self.host, self.port))
            try:
                if self.ssh_key:
                    key_file = io.StringIO(self.ssh_key)
                    try:
                        pkey = paramiko.RSAKey.from_private_key(key_file)
                    except paramiko.SSHException:
                        key_file.seek(0)
                        pkey = paramiko.Ed25519Key.from_private_key(key_file)
                    transport.connect(username=self.username, pkey=pkey)
                else:
                    transport.connect(username=self.username, password=self.password)

                sftp = paramiko.SFTPClient.from_transport(transport)

                # Ensure directory exists
                self._ensure_remote_dir_sftp(sftp, directory)

                # Upload file
                remote_path = f"{directory}/{filename}"
                file_obj = io.BytesIO(content.encode("utf-8"))
                sftp.putfo(file_obj, remote_path)

                bytes_transferred = len(content.encode("utf-8"))

                sftp.close()
                transport.close()

                return TransportResult(
                    success=True,
                    message="File uploaded successfully",
                    filename=filename,
                    file_path=remote_path,
                    bytes_transferred=bytes_transferred
                )
            except Exception as e:
                transport.close()
                raise e from e

        return await asyncio.get_event_loop().run_in_executor(None, _upload)

    def _ensure_remote_dir_sftp(self, sftp: paramiko.SFTPClient, directory: str) -> None:
        parts = directory.strip("/").split("/")
        current = ""
        for part in parts:
            current = f"{current}/{part}"
            try:
                sftp.stat(current)
            except FileNotFoundError:
                # Best-effort mkdir; directory may already exist owned
                # by a different uid, in which case the stat above just
                # raced us.
                with contextlib.suppress(PermissionError):
                    sftp.mkdir(current)

    async def _upload_ftp(
        self,
        content: str,
        filename: str,
        directory: str
    ) -> TransportResult:
        def _upload():
            if self.protocol == TransportProtocol.FTPS:
                context = ssl.create_default_context()
                ftp = ftplib.FTP_TLS(context=context)
            else:
                ftp = ftplib.FTP()

            ftp.connect(self.host, self.port, timeout=30)
            ftp.login(self.username, self.password or "")

            if self.protocol == TransportProtocol.FTPS:
                ftp.prot_p()

            # Change to directory (create if needed)
            self._ensure_remote_dir_ftp(ftp, directory)

            # Upload file
            file_obj = io.BytesIO(content.encode("utf-8"))
            ftp.storbinary(f"STOR {filename}", file_obj)

            bytes_transferred = len(content.encode("utf-8"))
            ftp.quit()

            return TransportResult(
                success=True,
                message="File uploaded successfully",
                filename=filename,
                file_path=f"{directory}/{filename}",
                bytes_transferred=bytes_transferred
            )

        return await asyncio.get_event_loop().run_in_executor(None, _upload)

    def _ensure_remote_dir_ftp(self, ftp: ftplib.FTP, directory: str) -> None:
        parts = directory.strip("/").split("/")
        for part in parts:
            try:
                ftp.cwd(part)
            except ftplib.error_perm:
                try:
                    ftp.mkd(part)
                    ftp.cwd(part)
                except ftplib.error_perm as e:
                    logger.warning("Failed to create FTP directory %s: %s", part, e)

    async def download_file(
        self,
        filename: str,
        directory: str | None = None
    ) -> tuple[str | None, TransportResult]:
        if directory is None:
            directory = self.inbound_dir

        try:
            if self.protocol == TransportProtocol.SFTP:
                return await self._download_sftp(filename, directory)
            elif self.protocol in [TransportProtocol.FTP, TransportProtocol.FTPS]:
                return await self._download_ftp(filename, directory)
            else:
                return None, TransportResult(
                    success=False,
                    message=f"Unsupported protocol: {self.protocol}",
                    error=f"Protocol {self.protocol} is not supported"
                )
        except Exception as e:
            logger.exception(f"Download failed: {e}")
            return None, TransportResult(
                success=False,
                message="Download failed",
                filename=filename,
                error=str(e)
            )

    async def _download_sftp(
        self,
        filename: str,
        directory: str
    ) -> tuple[str | None, TransportResult]:
        def _download():
            transport = paramiko.Transport((self.host, self.port))
            try:
                if self.ssh_key:
                    key_file = io.StringIO(self.ssh_key)
                    try:
                        pkey = paramiko.RSAKey.from_private_key(key_file)
                    except paramiko.SSHException:
                        key_file.seek(0)
                        pkey = paramiko.Ed25519Key.from_private_key(key_file)
                    transport.connect(username=self.username, pkey=pkey)
                else:
                    transport.connect(username=self.username, password=self.password)

                sftp = paramiko.SFTPClient.from_transport(transport)

                remote_path = f"{directory}/{filename}"
                file_obj = io.BytesIO()
                sftp.getfo(remote_path, file_obj)

                content = file_obj.getvalue().decode("utf-8")
                bytes_transferred = len(file_obj.getvalue())

                sftp.close()
                transport.close()

                return content, TransportResult(
                    success=True,
                    message="File downloaded successfully",
                    filename=filename,
                    file_path=remote_path,
                    bytes_transferred=bytes_transferred
                )
            except Exception as e:
                transport.close()
                raise e from e

        return await asyncio.get_event_loop().run_in_executor(None, _download)

    async def _download_ftp(
        self,
        filename: str,
        directory: str
    ) -> tuple[str | None, TransportResult]:
        def _download():
            if self.protocol == TransportProtocol.FTPS:
                context = ssl.create_default_context()
                ftp = ftplib.FTP_TLS(context=context)
            else:
                ftp = ftplib.FTP()

            ftp.connect(self.host, self.port, timeout=30)
            ftp.login(self.username, self.password or "")

            if self.protocol == TransportProtocol.FTPS:
                ftp.prot_p()

            ftp.cwd(directory)

            file_obj = io.BytesIO()
            ftp.retrbinary(f"RETR {filename}", file_obj.write)

            content = file_obj.getvalue().decode("utf-8")
            bytes_transferred = len(file_obj.getvalue())

            ftp.quit()

            return content, TransportResult(
                success=True,
                message="File downloaded successfully",
                filename=filename,
                file_path=f"{directory}/{filename}",
                bytes_transferred=bytes_transferred
            )

        return await asyncio.get_event_loop().run_in_executor(None, _download)

    async def list_files(
        self,
        directory: str | None = None,
        pattern: str | None = None
    ) -> tuple[list[FileInfo], TransportResult]:
        if directory is None:
            directory = self.inbound_dir

        try:
            if self.protocol == TransportProtocol.SFTP:
                return await self._list_files_sftp(directory, pattern)
            elif self.protocol in [TransportProtocol.FTP, TransportProtocol.FTPS]:
                return await self._list_files_ftp(directory, pattern)
            else:
                return [], TransportResult(
                    success=False,
                    message=f"Unsupported protocol: {self.protocol}",
                    error=f"Protocol {self.protocol} is not supported"
                )
        except Exception as e:
            logger.exception(f"List files failed: {e}")
            return [], TransportResult(
                success=False,
                message="Failed to list files",
                error=str(e)
            )

    async def _list_files_sftp(
        self,
        directory: str,
        pattern: str | None
    ) -> tuple[list[FileInfo], TransportResult]:
        def _list():
            transport = paramiko.Transport((self.host, self.port))
            try:
                if self.ssh_key:
                    key_file = io.StringIO(self.ssh_key)
                    try:
                        pkey = paramiko.RSAKey.from_private_key(key_file)
                    except paramiko.SSHException:
                        key_file.seek(0)
                        pkey = paramiko.Ed25519Key.from_private_key(key_file)
                    transport.connect(username=self.username, pkey=pkey)
                else:
                    transport.connect(username=self.username, password=self.password)

                sftp = paramiko.SFTPClient.from_transport(transport)

                files = []
                for attr in sftp.listdir_attr(directory):
                    # Skip directories
                    if attr.st_mode and (attr.st_mode & 0o40000):
                        continue

                    # Apply pattern filter
                    if pattern:
                        import fnmatch
                        if not fnmatch.fnmatch(attr.filename, pattern):
                            continue

                    files.append(FileInfo(
                        filename=attr.filename,
                        size=attr.st_size or 0,
                        modified_time=datetime.fromtimestamp(attr.st_mtime) if attr.st_mtime else None,
                        is_directory=False
                    ))

                sftp.close()
                transport.close()

                return files, TransportResult(
                    success=True,
                    message=f"Found {len(files)} files"
                )
            except Exception as e:
                transport.close()
                raise e from e

        return await asyncio.get_event_loop().run_in_executor(None, _list)

    async def _list_files_ftp(
        self,
        directory: str,
        pattern: str | None
    ) -> tuple[list[FileInfo], TransportResult]:
        def _list():
            if self.protocol == TransportProtocol.FTPS:
                context = ssl.create_default_context()
                ftp = ftplib.FTP_TLS(context=context)
            else:
                ftp = ftplib.FTP()

            ftp.connect(self.host, self.port, timeout=30)
            ftp.login(self.username, self.password or "")

            if self.protocol == TransportProtocol.FTPS:
                ftp.prot_p()

            ftp.cwd(directory)

            files = []
            listing = []
            ftp.retrlines("LIST", listing.append)

            for line in listing:
                parts = line.split()
                if len(parts) >= 9:
                    filename = " ".join(parts[8:])

                    # Skip directories (lines starting with 'd')
                    if line.startswith("d"):
                        continue

                    # Apply pattern filter
                    if pattern:
                        import fnmatch
                        if not fnmatch.fnmatch(filename, pattern):
                            continue

                    try:
                        size = int(parts[4])
                    except ValueError:
                        size = 0

                    files.append(FileInfo(
                        filename=filename,
                        size=size,
                        is_directory=False
                    ))

            ftp.quit()

            return files, TransportResult(
                success=True,
                message=f"Found {len(files)} files"
            )

        return await asyncio.get_event_loop().run_in_executor(None, _list)

    async def delete_file(
        self,
        filename: str,
        directory: str | None = None
    ) -> TransportResult:
        if directory is None:
            directory = self.inbound_dir

        try:
            if self.protocol == TransportProtocol.SFTP:
                return await self._delete_sftp(filename, directory)
            elif self.protocol in [TransportProtocol.FTP, TransportProtocol.FTPS]:
                return await self._delete_ftp(filename, directory)
            else:
                return TransportResult(
                    success=False,
                    message=f"Unsupported protocol: {self.protocol}",
                    error=f"Protocol {self.protocol} is not supported"
                )
        except Exception as e:
            logger.exception(f"Delete failed: {e}")
            return TransportResult(
                success=False,
                message="Delete failed",
                filename=filename,
                error=str(e)
            )

    async def _delete_sftp(self, filename: str, directory: str) -> TransportResult:
        def _delete():
            transport = paramiko.Transport((self.host, self.port))
            try:
                if self.ssh_key:
                    key_file = io.StringIO(self.ssh_key)
                    try:
                        pkey = paramiko.RSAKey.from_private_key(key_file)
                    except paramiko.SSHException:
                        key_file.seek(0)
                        pkey = paramiko.Ed25519Key.from_private_key(key_file)
                    transport.connect(username=self.username, pkey=pkey)
                else:
                    transport.connect(username=self.username, password=self.password)

                sftp = paramiko.SFTPClient.from_transport(transport)

                remote_path = f"{directory}/{filename}"
                sftp.remove(remote_path)

                sftp.close()
                transport.close()

                return TransportResult(
                    success=True,
                    message="File deleted successfully",
                    filename=filename,
                    file_path=remote_path
                )
            except Exception as e:
                transport.close()
                raise e from e

        return await asyncio.get_event_loop().run_in_executor(None, _delete)

    async def _delete_ftp(self, filename: str, directory: str) -> TransportResult:
        def _delete():
            if self.protocol == TransportProtocol.FTPS:
                context = ssl.create_default_context()
                ftp = ftplib.FTP_TLS(context=context)
            else:
                ftp = ftplib.FTP()

            ftp.connect(self.host, self.port, timeout=30)
            ftp.login(self.username, self.password or "")

            if self.protocol == TransportProtocol.FTPS:
                ftp.prot_p()

            ftp.cwd(directory)
            ftp.delete(filename)
            ftp.quit()

            return TransportResult(
                success=True,
                message="File deleted successfully",
                filename=filename,
                file_path=f"{directory}/{filename}"
            )

        return await asyncio.get_event_loop().run_in_executor(None, _delete)

    async def move_file(
        self,
        filename: str,
        source_dir: str,
        dest_dir: str
    ) -> TransportResult:
        try:
            if self.protocol == TransportProtocol.SFTP:
                return await self._move_sftp(filename, source_dir, dest_dir)
            elif self.protocol in [TransportProtocol.FTP, TransportProtocol.FTPS]:
                return await self._move_ftp(filename, source_dir, dest_dir)
            else:
                return TransportResult(
                    success=False,
                    message=f"Unsupported protocol: {self.protocol}",
                    error=f"Protocol {self.protocol} is not supported"
                )
        except Exception as e:
            logger.exception(f"Move failed: {e}")
            return TransportResult(
                success=False,
                message="Move failed",
                filename=filename,
                error=str(e)
            )

    async def _move_sftp(
        self,
        filename: str,
        source_dir: str,
        dest_dir: str
    ) -> TransportResult:
        def _move():
            transport = paramiko.Transport((self.host, self.port))
            try:
                if self.ssh_key:
                    key_file = io.StringIO(self.ssh_key)
                    try:
                        pkey = paramiko.RSAKey.from_private_key(key_file)
                    except paramiko.SSHException:
                        key_file.seek(0)
                        pkey = paramiko.Ed25519Key.from_private_key(key_file)
                    transport.connect(username=self.username, pkey=pkey)
                else:
                    transport.connect(username=self.username, password=self.password)

                sftp = paramiko.SFTPClient.from_transport(transport)

                source_path = f"{source_dir}/{filename}"
                dest_path = f"{dest_dir}/{filename}"

                # Ensure destination directory exists
                self._ensure_remote_dir_sftp(sftp, dest_dir)

                sftp.rename(source_path, dest_path)

                sftp.close()
                transport.close()

                return TransportResult(
                    success=True,
                    message="File moved successfully",
                    filename=filename,
                    file_path=dest_path
                )
            except Exception as e:
                transport.close()
                raise e from e

        return await asyncio.get_event_loop().run_in_executor(None, _move)

    async def _move_ftp(
        self,
        filename: str,
        source_dir: str,
        dest_dir: str
    ) -> TransportResult:
        def _move():
            if self.protocol == TransportProtocol.FTPS:
                context = ssl.create_default_context()
                ftp = ftplib.FTP_TLS(context=context)
            else:
                ftp = ftplib.FTP()

            ftp.connect(self.host, self.port, timeout=30)
            ftp.login(self.username, self.password or "")

            if self.protocol == TransportProtocol.FTPS:
                ftp.prot_p()

            source_path = f"{source_dir}/{filename}"
            dest_path = f"{dest_dir}/{filename}"

            # Ensure destination directory exists
            self._ensure_remote_dir_ftp(ftp, dest_dir)

            ftp.rename(source_path, dest_path)
            ftp.quit()

            return TransportResult(
                success=True,
                message="File moved successfully",
                filename=filename,
                file_path=dest_path
            )

        return await asyncio.get_event_loop().run_in_executor(None, _move)
