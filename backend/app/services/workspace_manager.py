import os
import shutil
import tempfile
import zipfile
import subprocess
from pathlib import Path
from fastapi import HTTPException

class WorkspaceManager:
    @staticmethod
    def create_sandbox() -> Path:
        # --> Create a temporary directory
        return Path(tempfile.mkdtemp(prefix="codepulse_repo_"))

    @staticmethod
    async def extract_zip(zip_bytes: bytes, target_dir: Path) -> Path:
        # --> Extract the uploaded zip file to the target directory
        zip_path = target_dir / "upload.zip"
        zip_path.write_bytes(zip_bytes)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for member in zip_ref.infolist():
                resolved_path = (target_dir / member.filename).resolve()
                if not str(resolved_path).startswith(str(target_dir.resolve())):
                    raise HTTPException(status_code=400, detail="Security error: Path traversal detected.")
            zip_ref.extractall(target_dir)

        if zip_path.exists():
            os.remove(zip_path)
        return target_dir

    @staticmethod
    def clone_github_repo(repo_url: str, target_dir: Path) -> Path:
        # --> Clone a GitHub repository into the target directory
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "--single-branch", repo_url, str(target_dir)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60
            )
            return target_dir
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to clone repository: {str(e)}")

    @staticmethod
    def cleanup(target_dir: Path) -> None:
        # --> Delete the workspace folder after job execution
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)