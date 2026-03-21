"""Tests for the agent loader system."""

import textwrap

import pytest

from aicouncil.agent_loader import (
    get_agents,
    load_agents_from_directory,
    load_all_agents,
    load_builtin_agents,
    parse_manifest,
    parse_persona,
    reset_agents,
)
from aicouncil.exceptions import AgentLoadError
from aicouncil.schemas.agents import Agent, AgentRoster

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_PERSONA = textwrap.dedent("""\
    ---
    name: "Test Agent"
    role: "Test Role"
    type: "expert"
    tier: 1
    domains: ["testing", "quality"]
    include_flag: true
    ---

    ## Identity
    A test agent.

    ## Communication Style
    Direct.

    ## Principles
    - Test everything

    ## Domain Expertise
    - Testing
""")

VALID_MANIFEST_CSV = textwrap.dedent("""\
    name,role,type,tier,domains,include_flag
    test-agent,Test Role,expert,1,testing;quality,true
    another-agent,Another Role,builder,2,backend;api,false
""")


@pytest.fixture()
def valid_persona_file(tmp_path):
    """Create a valid persona .md file."""
    md = tmp_path / "test-agent.md"
    md.write_text(VALID_PERSONA)
    return md


@pytest.fixture()
def valid_manifest_file(tmp_path):
    """Create a valid manifest CSV."""
    csv_file = tmp_path / "agent-manifest.csv"
    csv_file.write_text(VALID_MANIFEST_CSV)
    return csv_file


@pytest.fixture()
def agent_dir(tmp_path):
    """Create a directory with a manifest and matching persona files."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    # Manifest
    manifest = agents_dir / "agent-manifest.csv"
    manifest.write_text(
        "name,role,type,tier,domains,include_flag\n"
        "alpha,Alpha Agent,expert,1,arch;design,true\n"
        "beta,Beta Agent,builder,2,backend;api,true\n"
    )

    # Persona files
    (agents_dir / "alpha.md").write_text(
        textwrap.dedent("""\
        ---
        name: "Alpha"
        role: "Alpha Agent"
        type: "expert"
        tier: 1
        domains: ["arch", "design"]
        include_flag: true
        ---

        ## Identity
        Alpha agent.
    """)
    )

    (agents_dir / "beta.md").write_text(
        textwrap.dedent("""\
        ---
        name: "Beta"
        role: "Beta Agent"
        type: "builder"
        tier: 2
        domains: ["backend", "api"]
        include_flag: true
        ---

        ## Identity
        Beta agent.
    """)
    )

    return agents_dir


@pytest.fixture()
def user_project(tmp_path):
    """Create a project root with user agents directory."""
    user_agents = tmp_path / "aicouncil" / "agents"
    user_agents.mkdir(parents=True)
    return tmp_path


# ---------------------------------------------------------------------------
# CSV Manifest Parsing
# ---------------------------------------------------------------------------


class TestParseManifest:
    def test_valid_manifest(self, valid_manifest_file):
        rows = parse_manifest(valid_manifest_file)
        assert len(rows) == 2
        assert rows[0]["name"] == "test-agent"
        assert rows[1]["name"] == "another-agent"

    def test_missing_file(self, tmp_path):
        with pytest.raises(AgentLoadError, match="not found"):
            parse_manifest(tmp_path / "nonexistent.csv")

    def test_empty_file(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")
        with pytest.raises(AgentLoadError, match="empty"):
            parse_manifest(csv_file)

    def test_whitespace_only_file(self, tmp_path):
        csv_file = tmp_path / "whitespace.csv"
        csv_file.write_text("   \n\n  ")
        with pytest.raises(AgentLoadError, match="empty"):
            parse_manifest(csv_file)

    def test_missing_required_headers(self, tmp_path):
        csv_file = tmp_path / "bad.csv"
        csv_file.write_text("name,role\nalpha,Alpha\n")
        with pytest.raises(AgentLoadError, match="missing required headers"):
            parse_manifest(csv_file)

    def test_domains_semicolon_format(self, valid_manifest_file):
        rows = parse_manifest(valid_manifest_file)
        assert rows[0]["domains"] == "testing;quality"


# ---------------------------------------------------------------------------
# Markdown Persona Parsing
# ---------------------------------------------------------------------------


class TestParsePersona:
    def test_valid_persona(self, valid_persona_file):
        agent = parse_persona(valid_persona_file)
        assert agent.name == "Test Agent"
        assert agent.role == "Test Role"
        assert agent.type == "expert"
        assert agent.tier == 1
        assert agent.domains == ["testing", "quality"]
        assert agent.include_flag is True
        assert "## Identity" in agent.persona

    def test_missing_frontmatter(self, tmp_path):
        md = tmp_path / "bad.md"
        md.write_text("No frontmatter here.")
        with pytest.raises(AgentLoadError, match="missing YAML frontmatter"):
            parse_persona(md)

    def test_missing_closing_delimiter(self, tmp_path):
        md = tmp_path / "bad.md"
        md.write_text("---\nname: test\n")
        with pytest.raises(AgentLoadError, match="malformed frontmatter"):
            parse_persona(md)

    def test_missing_required_fields(self, tmp_path):
        md = tmp_path / "bad.md"
        md.write_text('---\nname: "Test"\nrole: "Role"\n---\nBody\n')
        with pytest.raises(AgentLoadError, match="missing required fields"):
            parse_persona(md)

    def test_invalid_type(self, tmp_path):
        md = tmp_path / "bad.md"
        md.write_text(
            textwrap.dedent("""\
            ---
            name: "Bad"
            role: "Bad Role"
            type: "invalid_type"
            tier: 1
            domains: ["test"]
            include_flag: true
            ---
            Body
        """)
        )
        with pytest.raises(AgentLoadError, match="invalid type"):
            parse_persona(md)

    def test_invalid_tier(self, tmp_path):
        md = tmp_path / "bad.md"
        md.write_text(
            textwrap.dedent("""\
            ---
            name: "Bad"
            role: "Bad Role"
            type: "expert"
            tier: 5
            domains: ["test"]
            include_flag: true
            ---
            Body
        """)
        )
        with pytest.raises(AgentLoadError, match="invalid tier"):
            parse_persona(md)

    def test_tier_as_string(self, tmp_path):
        md = tmp_path / "good.md"
        md.write_text(
            textwrap.dedent("""\
            ---
            name: "Good"
            role: "Good Role"
            type: "expert"
            tier: "2"
            domains: ["test"]
            include_flag: true
            ---
            Body
        """)
        )
        agent = parse_persona(md)
        assert agent.tier == 2

    def test_domains_as_semicolon_string(self, tmp_path):
        md = tmp_path / "good.md"
        md.write_text(
            textwrap.dedent("""\
            ---
            name: "Good"
            role: "Good Role"
            type: "expert"
            tier: 1
            domains: "arch;design;patterns"
            include_flag: true
            ---
            Body
        """)
        )
        agent = parse_persona(md)
        assert agent.domains == ["arch", "design", "patterns"]

    def test_include_flag_string_true(self, tmp_path):
        md = tmp_path / "good.md"
        md.write_text(
            textwrap.dedent("""\
            ---
            name: "Good"
            role: "Good Role"
            type: "expert"
            tier: 1
            domains: ["test"]
            include_flag: "true"
            ---
            Body
        """)
        )
        agent = parse_persona(md)
        assert agent.include_flag is True

    def test_include_flag_string_false(self, tmp_path):
        md = tmp_path / "good.md"
        md.write_text(
            textwrap.dedent("""\
            ---
            name: "Good"
            role: "Good Role"
            type: "expert"
            tier: 1
            domains: ["test"]
            include_flag: "false"
            ---
            Body
        """)
        )
        agent = parse_persona(md)
        assert agent.include_flag is False

    def test_invalid_yaml(self, tmp_path):
        md = tmp_path / "bad.md"
        md.write_text("---\n: [invalid yaml\n---\nBody\n")
        with pytest.raises(AgentLoadError, match="invalid YAML"):
            parse_persona(md)

    def test_frontmatter_not_mapping(self, tmp_path):
        md = tmp_path / "bad.md"
        md.write_text("---\n- just a list\n---\nBody\n")
        with pytest.raises(AgentLoadError, match="must be a YAML mapping"):
            parse_persona(md)


# ---------------------------------------------------------------------------
# Directory Loading
# ---------------------------------------------------------------------------


class TestLoadAgentsFromDirectory:
    def test_with_manifest_and_personas(self, agent_dir):
        agents = load_agents_from_directory(agent_dir)
        assert len(agents) == 2
        names = {a.name for a in agents}
        assert "Alpha" in names
        assert "Beta" in names

    def test_with_only_personas_no_manifest(self, tmp_path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "solo.md").write_text(
            textwrap.dedent("""\
            ---
            name: "Solo"
            role: "Solo Agent"
            type: "user"
            tier: 3
            domains: ["solo"]
            include_flag: true
            ---
            Solo persona.
        """)
        )
        agents = load_agents_from_directory(agents_dir)
        assert len(agents) == 1
        assert agents[0].name == "Solo"

    def test_empty_directory(self, tmp_path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        agents = load_agents_from_directory(agents_dir)
        assert agents == []

    def test_nonexistent_directory(self, tmp_path):
        agents = load_agents_from_directory(tmp_path / "nonexistent")
        assert agents == []

    def test_manifest_references_missing_file(self, tmp_path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        manifest = agents_dir / "agent-manifest.csv"
        manifest.write_text(
            "name,role,type,tier,domains,include_flag\nmissing-agent,Missing,expert,1,test,true\n"
        )
        agents = load_agents_from_directory(agents_dir)
        assert agents == []

    def test_md_outside_manifest_still_loaded(self, agent_dir):
        """Files not in manifest are still discovered and loaded."""
        (agent_dir / "extra.md").write_text(
            textwrap.dedent("""\
            ---
            name: "Extra"
            role: "Extra Agent"
            type: "user"
            tier: 3
            domains: ["misc"]
            include_flag: false
            ---
            Extra persona.
        """)
        )
        agents = load_agents_from_directory(agent_dir)
        names = {a.name for a in agents}
        assert "Extra" in names
        assert len(agents) == 3

    def test_malformed_file_skipped_others_load(self, agent_dir):
        """One bad file doesn't crash the whole load."""
        (agent_dir / "bad.md").write_text("No frontmatter.")
        agents = load_agents_from_directory(agent_dir)
        # Alpha and Beta still load
        assert len(agents) == 2


# ---------------------------------------------------------------------------
# Built-in Agent Loading
# ---------------------------------------------------------------------------


class TestLoadBuiltinAgents:
    def test_loads_seed_agents(self):
        agents = load_builtin_agents()
        assert len(agents) == 40
        names = {a.name for a in agents}
        assert "Software Architect" in names
        assert "Security Engineer" in names
        assert "Tax Advisor" in names
        assert "Backend Developer" in names
        assert "Entrepreneur" in names

    def test_agent_types(self):
        agents = load_builtin_agents()
        types = {a.name: a.type for a in agents}
        assert types["Software Architect"] == "expert"
        assert types["Backend Developer"] == "builder"
        assert types["Entrepreneur"] == "user"

    def test_agent_tiers(self):
        agents = load_builtin_agents()
        tiers = {a.name: a.tier for a in agents}
        assert tiers["Software Architect"] == 1
        assert tiers["Security Engineer"] == 2
        assert tiers["Tax Advisor"] == 3


# ---------------------------------------------------------------------------
# Dual-Directory Overlay
# ---------------------------------------------------------------------------


class TestLoadAllAgents:
    def test_user_overrides_builtin(self, user_project):
        """User agent with same name overrides built-in."""
        user_agents_dir = user_project / "aicouncil" / "agents"
        (user_agents_dir / "software-architect.md").write_text(
            textwrap.dedent("""\
            ---
            name: "Software Architect"
            role: "Custom Architect"
            type: "expert"
            tier: 1
            domains: ["custom"]
            include_flag: true
            ---
            Custom persona.
        """)
        )
        roster = load_all_agents(project_root=user_project)
        architect = roster.get_by_name("Software Architect")
        assert architect is not None
        assert architect.role == "Custom Architect"
        assert architect.domains == ["custom"]

    def test_user_adds_new_agent(self, user_project):
        """User agents that don't collide are added alongside built-ins."""
        user_agents_dir = user_project / "aicouncil" / "agents"
        (user_agents_dir / "custom-expert.md").write_text(
            textwrap.dedent("""\
            ---
            name: "Custom Expert"
            role: "Custom Role"
            type: "expert"
            tier: 2
            domains: ["custom_domain"]
            include_flag: true
            ---
            Custom persona.
        """)
        )
        roster = load_all_agents(project_root=user_project)
        custom = roster.get_by_name("Custom Expert")
        assert custom is not None
        # Built-ins still present
        assert roster.get_by_name("Software Architect") is not None
        assert len(roster.agents) == 41  # 40 built-in + 1 user

    def test_no_user_agents(self, tmp_path):
        """Works fine when no user agents directory exists."""
        roster = load_all_agents(project_root=tmp_path)
        assert len(roster.agents) == 40  # Just built-ins


# ---------------------------------------------------------------------------
# AgentRoster Query Methods
# ---------------------------------------------------------------------------


class TestAgentRoster:
    @pytest.fixture()
    def roster(self):
        return AgentRoster(
            agents=[
                Agent(
                    name="A",
                    role="R",
                    type="expert",
                    tier=1,
                    domains=["arch", "design"],
                    include_flag=True,
                ),
                Agent(
                    name="B",
                    role="R",
                    type="expert",
                    tier=2,
                    domains=["security"],
                    include_flag=True,
                ),
                Agent(
                    name="C",
                    role="R",
                    type="builder",
                    tier=1,
                    domains=["backend", "arch"],
                    include_flag=True,
                ),
                Agent(
                    name="D",
                    role="R",
                    type="user",
                    tier=1,
                    domains=["business"],
                    include_flag=True,
                ),
                Agent(
                    name="E",
                    role="R",
                    type="user",
                    tier=3,
                    domains=["product"],
                    include_flag=False,
                ),
            ]
        )

    def test_by_type(self, roster):
        experts = roster.by_type("expert")
        assert len(experts) == 2
        assert all(a.type == "expert" for a in experts)

    def test_by_tier(self, roster):
        tier1 = roster.by_tier(1)
        assert len(tier1) == 3
        assert all(a.tier == 1 for a in tier1)

    def test_by_domain(self, roster):
        arch = roster.by_domain("arch")
        assert len(arch) == 2
        names = {a.name for a in arch}
        assert names == {"A", "C"}

    def test_experts(self, roster):
        assert len(roster.experts()) == 2

    def test_builders(self, roster):
        assert len(roster.builders()) == 1

    def test_users_include_flagged_only(self, roster):
        users = roster.users(include_flagged_only=True)
        assert len(users) == 1
        assert users[0].name == "D"

    def test_users_all(self, roster):
        users = roster.users(include_flagged_only=False)
        assert len(users) == 2

    def test_get_by_name(self, roster):
        a = roster.get_by_name("A")
        assert a is not None
        assert a.name == "A"

    def test_get_by_name_case_insensitive(self, roster):
        a = roster.get_by_name("a")
        assert a is not None
        assert a.name == "A"

    def test_get_by_name_not_found(self, roster):
        assert roster.get_by_name("nonexistent") is None


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestSingleton:
    def setup_method(self):
        reset_agents()

    def teardown_method(self):
        reset_agents()

    def test_get_agents_returns_roster(self, tmp_path):
        roster = get_agents(project_root=tmp_path)
        assert isinstance(roster, AgentRoster)
        assert len(roster.agents) == 40  # Built-in agents

    def test_get_agents_caches(self, tmp_path):
        roster1 = get_agents(project_root=tmp_path)
        roster2 = get_agents(project_root=tmp_path)
        assert roster1 is roster2

    def test_reset_clears_cache(self, tmp_path):
        roster1 = get_agents(project_root=tmp_path)
        reset_agents()
        roster2 = get_agents(project_root=tmp_path)
        assert roster1 is not roster2

    def test_different_project_root_reloads(self, tmp_path):
        """Singleton reloads when project_root changes."""
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        roster1 = get_agents(project_root=dir_a)
        roster2 = get_agents(project_root=dir_b)
        assert roster1 is not roster2


# ---------------------------------------------------------------------------
# Agent Model
# ---------------------------------------------------------------------------


class TestAgentModel:
    def test_frozen(self):
        agent = Agent(name="T", role="R", type="expert", tier=1, domains=["d"], include_flag=True)
        with pytest.raises(Exception):
            agent.name = "X"

    def test_empty_persona(self):
        agent = Agent(name="T", role="R", type="expert", tier=1, domains=["d"], include_flag=True)
        assert agent.persona == ""


# ---------------------------------------------------------------------------
# Patch Coverage: P1-P3, P5
# ---------------------------------------------------------------------------


class TestPatchFixes:
    def test_include_flag_with_whitespace(self, tmp_path):
        """P1: include_flag string with whitespace is handled."""
        md = tmp_path / "good.md"
        md.write_text(
            textwrap.dedent("""\
            ---
            name: "Good"
            role: "Good Role"
            type: "expert"
            tier: 1
            domains: ["test"]
            include_flag: " true "
            ---
            Body
        """)
        )
        agent = parse_persona(md)
        assert agent.include_flag is True

    def test_null_name_raises(self, tmp_path):
        """P2: null name in frontmatter raises AgentLoadError."""
        md = tmp_path / "bad.md"
        md.write_text(
            "---\nname:\nrole: R\ntype: expert\n"
            "tier: 1\ndomains: [d]\ninclude_flag: true\n---\nBody\n"
        )
        with pytest.raises(AgentLoadError, match="must not be null"):
            parse_persona(md)

    def test_null_role_raises(self, tmp_path):
        """P2: null role in frontmatter raises AgentLoadError."""
        md = tmp_path / "bad.md"
        md.write_text(
            "---\nname: X\nrole:\ntype: expert\n"
            "tier: 1\ndomains: [d]\ninclude_flag: true\n---\nBody\n"
        )
        with pytest.raises(AgentLoadError, match="must not be null"):
            parse_persona(md)

    def test_path_traversal_in_manifest_skipped(self, tmp_path):
        """P3: manifest entries with path traversal are skipped."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        manifest = agents_dir / "agent-manifest.csv"
        manifest.write_text(
            "name,role,type,tier,domains,include_flag\n../../etc/passwd,Evil,expert,1,evil,true\n"
        )
        agents = load_agents_from_directory(agents_dir)
        assert agents == []
