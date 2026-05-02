import subprocess
import os
import structlog
from pathlib import Path

log = structlog.get_logger()

class SnapshotManager:
    def __init__(self, root_dir: str = None):
        # Default root adalah folder root proyek (ai-super/)
        self.root_dir = root_dir or str(Path(__file__).parent.parent.parent)
        
    def create_snapshot(self, message: str) -> bool:
        """
        Simpan state saat ini ke Git jika ada perubahan.
        Digunakan sebagai 'Save Point' sebelum AI melakukan aksi destruktif.
        """
        try:
            # 1. Cek apakah ini git repo
            if not os.path.exists(os.path.join(self.root_dir, ".git")):
                # Inisialisasi jika belum ada (opsional, tapi aman)
                subprocess.run(["git", "init"], cwd=self.root_dir)

            # 2. Cek apakah ada perubahan (staged atau unstaged)
            status = subprocess.run(
                ["git", "status", "--short"],
                cwd=self.root_dir, capture_output=True, text=True
            )
            
            if not status.stdout.strip():
                # Tidak ada perubahan, tidak perlu snapshot
                return False
                
            # 3. Simpan perubahan
            subprocess.run(["git", "add", "."], cwd=self.root_dir)
            
            # 4. Commit dengan prefix khusus agar mudah di-identifikasi untuk rollback
            commit_msg = f"AI_SNAPSHOT: {message}"
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg, "--no-verify"],
                cwd=self.root_dir, capture_output=True, text=True
            )
            
            if result.returncode == 0:
                log.info("Snapshot created successfully", action=message)
                return True
            else:
                log.debug("Git commit skipped or failed", output=result.stderr.strip())
                
        except Exception as e:
            log.warning("Snapshot manager error", error=str(e)[:100])
        return False

    async def create_snapshot_async(self, message: str) -> bool:
        """
        Versi asinkronus dari create_snapshot untuk menghindari pemblokiran event loop.
        """
        import asyncio
        try:
            # 1. Cek apakah ini git repo
            if not os.path.exists(os.path.join(self.root_dir, ".git")):
                p_init = await asyncio.create_subprocess_exec("git", "init", cwd=self.root_dir, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                await p_init.communicate()

            # 2. Cek apakah ada perubahan
            p_status = await asyncio.create_subprocess_exec(
                "git", "status", "--short",
                cwd=self.root_dir, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await p_status.communicate()
            if not stdout.strip():
                return False

            # 3. Simpan perubahan
            p_add = await asyncio.create_subprocess_exec("git", "add", ".", cwd=self.root_dir, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            await p_add.communicate()

            # 4. Commit
            commit_msg = f"AI_SNAPSHOT: {message}"
            p_commit = await asyncio.create_subprocess_exec(
                "git", "commit", "-m", commit_msg, "--no-verify",
                cwd=self.root_dir, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await p_commit.communicate()
            
            if p_commit.returncode == 0:
                log.info("Snapshot created successfully (async)", action=message)
                return True
            else:
                log.debug("Git commit skipped or failed (async)", output=stderr.decode().strip())
                
        except Exception as e:
            log.warning("Async Snapshot manager error", error=str(e)[:100])
        return False

    def rollback(self) -> dict:
        """
        Kembalikan sistem ke Snapshot AI terakhir.
        Hati-hati: ini akan menghapus perubahan yang belum di-commit.
        """
        try:
            # 1. Cari hash commit terakhir dengan prefix AI_SNAPSHOT
            result = subprocess.run(
                ["git", "log", "--grep=AI_SNAPSHOT", "-n", "1", "--format=%H"],
                cwd=self.root_dir, capture_output=True, text=True
            )
            commit_hash = result.stdout.strip()
            
            if not commit_hash:
                return {"success": False, "error": "Tidak ditemukan Snapshot AI untuk di-rollback."}

            # 2. Eksekusi reset hard
            # Hapus semua perubahan setelah commit tersebut
            subprocess.run(["git", "reset", "--hard", commit_hash], cwd=self.root_dir)
            # Bersihkan file baru yang tidak terlacak (untracked)
            subprocess.run(["git", "clean", "-fd"], cwd=self.root_dir)
            
            log.info("Rollback executed", commit=commit_hash)
            return {"success": True, "commit": commit_hash}
            
        except Exception as e:
            log.error("Rollback execution failed", error=str(e))
            return {"success": False, "error": str(e)}

    def get_history(self, limit: int = 10):
        """Ambil daftar snapshot terakhir."""
        try:
            result = subprocess.run(
                ["git", "log", "--grep=AI_SNAPSHOT", f"-n {limit}", "--format=%H|%ar|%s"],
                cwd=self.root_dir, capture_output=True, text=True
            )
            history = []
            for line in result.stdout.splitlines():
                if "|" in line:
                    h, t, m = line.split("|", 2)
                    history.append({"hash": h, "time": t, "message": m.replace("AI_SNAPSHOT: ", "")})
            return history
        except:
            return []

snapshot_manager = SnapshotManager()
