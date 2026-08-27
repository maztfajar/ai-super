import pytest
import os
import tempfile
from core.sandbox_executor import SandboxedExecutor, SandboxProfile, NetworkPolicy

def test_sandbox_profile_detection():
    executor = SandboxedExecutor()
    
    assert executor.detect_profile("ls -la") == SandboxProfile.READ_ONLY
    assert executor.detect_profile("cat package.json") == SandboxProfile.READ_ONLY
    assert executor.detect_profile("mkdir build") == SandboxProfile.WRITE_SAFE
    assert executor.detect_profile("npm install axios") == SandboxProfile.FULL_ACCESS
    assert executor.detect_profile("pip install fastapi") == SandboxProfile.FULL_ACCESS

def test_sandbox_should_bypass():
    executor = SandboxedExecutor()
    assert executor.should_bypass("echo hello") is True
    assert executor.should_bypass("pwd") is True
    assert executor.should_bypass("npm run build") is False

def test_sandbox_bwrap_command_builder():
    executor = SandboxedExecutor()
    from core.sandbox_executor import PROFILE_CONFIGS
    
    config = PROFILE_CONFIGS[SandboxProfile.WRITE_SAFE]
    bwrap_cmd = executor._build_bwrap_command(
        command="echo 'test inside sandbox'",
        workspace_dir="/tmp/test_workspace",
        config=config,
        network=NetworkPolicy.OFFLINE
    )
    
    assert "bwrap" in bwrap_cmd
    assert "--proc /proc" in bwrap_cmd
    assert "--unshare-net" in bwrap_cmd
    assert "--unshare-pid" in bwrap_cmd
    assert "/tmp/test_workspace" in bwrap_cmd

@pytest.mark.asyncio
async def test_sandbox_execution_fallback():
    executor = SandboxedExecutor()
    with tempfile.TemporaryDirectory() as temp_dir:
        stdout, stderr, code = await executor.execute(
            command="echo 'sandbox execution test'",
            workspace_dir=temp_dir,
            profile=SandboxProfile.READ_ONLY
        )
        assert code == 0
        assert "sandbox execution test" in stdout
        
        # Check audit trail
        history = executor.get_audit_history(limit=5)
        assert len(history) > 0
        assert history[-1]["command_preview"].startswith("echo")
