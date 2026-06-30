import pytest
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.core import skill_repo
from app.tools.skill_repo_tools import import_skills_repo, load_skill, list_skills

@pytest.fixture
def mock_skill_md_content():
    return (
        "---\n"
        "name: test-auditor\n"
        "description: Expert in scanning test code quality.\n"
        "tags:\n"
        "  - testing\n"
        "  - python\n"
        "---\n"
        "Instructions: Make sure to check assertions and fixtures."
    )

def test_frontmatter_extraction(tmp_path, mock_skill_md_content):
    # Set REPO_PATH locally to temp path
    with patch("app.core.skill_repo.REPO_PATH", tmp_path):
        with patch("app.core.skill_repo.INDEX_PATH", tmp_path / "index.json"):
            # Create a mock SKILL.md under a whitelisted domain
            skill_dir = tmp_path / "engineering" / "test_auditor"
            skill_dir.mkdir(parents=True)
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(mock_skill_md_content, encoding="utf-8")
            
            # Rebuild index
            index = skill_repo.build_skill_index()
            
            # Assert index contains the correct skill details
            assert len(index) == 1
            assert index[0]["name"] == "test-auditor"
            assert index[0]["description"] == "Expert in scanning test code quality."
            assert index[0]["domain"] == "engineering"

def test_domain_filtering_exclusion(tmp_path, mock_skill_md_content):
    with patch("app.core.skill_repo.REPO_PATH", tmp_path):
        with patch("app.core.skill_repo.INDEX_PATH", tmp_path / "index.json"):
            # Create a mock SKILL.md under a non-whitelisted domain (e.g. marketing)
            skill_dir = tmp_path / "marketing" / "ad_campaign"
            skill_dir.mkdir(parents=True)
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(mock_skill_md_content, encoding="utf-8")
            
            # Rebuild index
            index = skill_repo.build_skill_index()
            
            # Assert index is empty because "marketing" is not in RELEVANT_DOMAINS
            assert len(index) == 0

def test_git_missing_fallback():
    with patch("subprocess.run") as mock_run:
        # Simulate git command missing (FileNotFoundError)
        mock_run.side_effect = FileNotFoundError()
        
        # Test cloner
        res = skill_repo.clone_or_update_repo()
        assert "git is not installed" in res

def test_git_command_failed_fallback():
    with patch("subprocess.run") as mock_run:
        # Simulate Git error process
        mock_error = subprocess.CalledProcessError(
            returncode=128,
            cmd="git pull",
            stderr=b"fatal: not a git repository"
        )
        mock_run.side_effect = mock_error
        
        # Test cloner
        res = skill_repo.clone_or_update_repo()
        assert "git command failed" in res
        assert "not a git repository" in res

def test_load_skill_full_text(tmp_path, mock_skill_md_content):
    with patch("app.core.skill_repo.INDEX_PATH", tmp_path / "index.json"):
        # Write dummy index.json
        skill_file_path = tmp_path / "SKILL.md"
        skill_file_path.write_text(mock_skill_md_content, encoding="utf-8")
        
        index_data = [
            {
                "name": "test-auditor",
                "description": "Expert description",
                "path": str(skill_file_path.resolve()),
                "domain": "engineering"
            }
        ]
        (tmp_path / "index.json").write_text(json.dumps(index_data), encoding="utf-8")
        
        # Match exactly
        text = skill_repo.load_skill_full_text("test-auditor")
        assert "test-auditor" in text
        assert "Expert in scanning" in text
        
        # Match case insensitively/partially
        text2 = skill_repo.load_skill_full_text("test-Aud")
        assert text2 is not None
        
        # Match unknown
        assert skill_repo.load_skill_full_text("unknown-skill") is None

def test_get_skill_summaries_budget(tmp_path):
    with patch("app.core.skill_repo.INDEX_PATH", tmp_path / "index.json"):
        # 1. Non-existent index path
        assert skill_repo.get_skill_summaries() == ""
        
        # 2. Populated index
        index_data = [
            {"name": f"skill-{i}", "description": f"desc-{i}", "path": "path", "domain": "engineering"}
            for i in range(10)
        ]
        (tmp_path / "index.json").write_text(json.dumps(index_data), encoding="utf-8")
        
        summaries = skill_repo.get_skill_summaries()
        assert len(summaries.splitlines()) == 10
        assert "- skill-0: desc-0" in summaries
