import pytest
from core.approval_system import ApprovalSystem, RiskLevel, detect_sandbox_profile

def test_approval_system_detect_bash_risk():
    app_sys = ApprovalSystem()
    
    # Safe commands
    risk, _ = app_sys.detect_bash_risk("ls -la")
    assert risk == RiskLevel.LOW
    
    risk, _ = app_sys.detect_bash_risk("cat file.txt")
    assert risk == RiskLevel.LOW
    
    # Risky commands
    risk, reason = app_sys.detect_bash_risk("sudo rm -rf /")
    assert risk == RiskLevel.HIGH
    assert "risky" in reason.lower()
    
    risk, reason = app_sys.detect_bash_risk("mkfs.ext4 /dev/sdb")
    assert risk == RiskLevel.HIGH
    
    # Warning commands
    risk, _ = app_sys.detect_bash_risk("rm test.txt")
    assert risk == RiskLevel.MEDIUM

def test_approval_system_detect_file_risk():
    app_sys = ApprovalSystem()
    
    risk, _ = app_sys.detect_file_risk("/home/user/projects/test.py")
    assert risk == RiskLevel.LOW
    
    risk, reason = app_sys.detect_file_risk("/etc/nginx/nginx.conf")
    assert risk == RiskLevel.HIGH
    
    risk, reason = app_sys.detect_file_risk("/etc/passwd")
    assert risk == RiskLevel.CRITICAL

def test_approval_flow():
    app_sys = ApprovalSystem()
    req = app_sys.create_approval_request(
        operation_type="execute_bash",
        operation_detail="sudo systemctl restart nginx",
        risk_level=RiskLevel.HIGH,
        reason="Restarting system service"
    )
    
    assert req.status == "pending"
    assert app_sys.is_approved(req.request_id) is True  # means pending check returns True for awaiting
    
    # Approve
    success = app_sys.approve_request(req.request_id, user_id="admin_1")
    assert success is True
    
    saved_req = app_sys.get_request(req.request_id)
    assert saved_req["status"] == "approved"
    assert saved_req["approved_by"] == "admin_1"

def test_sandbox_profile_detection():
    assert detect_sandbox_profile("ls -l") == "bypass"
    assert detect_sandbox_profile("cat README.md") == "bypass"
    assert detect_sandbox_profile("npm install express") == "full_access"
    assert detect_sandbox_profile("mkdir -p src") == "write_safe"
    assert detect_sandbox_profile("python3 script.py") == "write_safe"
