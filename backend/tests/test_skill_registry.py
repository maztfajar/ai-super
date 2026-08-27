import pytest
from core.skill_registry import SkillRegistry, Skill

def test_skill_serialization():
    skill = Skill(
        id="test_sk1",
        name="Build React App",
        description="Steps to build a Vite React application",
        category="frontend",
        tags=["react", "vite", "frontend"],
        steps=["npm install", "npm run build"],
        examples=["Build todo app"],
        trigger_keywords=["react build", "vite bundle"],
        content="Important: check node version first."
    )
    
    md = skill.to_markdown()
    assert "id: test_sk1" in md
    assert "name: Build React App" in md
    assert "npm run build" in md
    
    parsed = Skill.from_markdown(md, skill_id="test_sk1")
    assert parsed.id == "test_sk1"
    assert parsed.name == "Build React App"
    assert parsed.category == "frontend"
    assert len(parsed.steps) == 2
    assert "npm run build" in parsed.steps

def test_skill_safety_validation():
    registry = SkillRegistry()
    
    # Safe skill
    safe_skill = Skill(
        name="Python Virtualenv Setup",
        description="Setup venv",
        steps=["python -m venv venv", "source venv/bin/activate"]
    )
    is_safe, _ = registry.validate_safety(safe_skill)
    assert is_safe is True
    
    # Dangerous skill (destructive command)
    dangerous_skill = Skill(
        name="Clean disk",
        description="Clear everything",
        steps=["rm -rf /", "reboot"]
    )
    is_safe, reason = registry.validate_safety(dangerous_skill)
    assert is_safe is False
    assert "Dangerous command pattern" in reason
    
    # Try creating dangerous skill should raise ValueError
    with pytest.raises(ValueError, match="safety engine"):
        registry.create_skill({
            "name": "Dangerous cleanup",
            "description": "Exploit script",
            "steps": ["rm -rf /"]
        })

def test_skill_similarity_hash():
    s1 = Skill(name="Deploy Docker Container", description="Deploying on port 80")
    s2 = Skill(name="deploy docker container", description="deploying on port 80")
    s3 = Skill(name="Setup Postgres", description="Install database")
    
    assert s1.similarity_hash() == s2.similarity_hash()
    assert s1.similarity_hash() != s3.similarity_hash()
