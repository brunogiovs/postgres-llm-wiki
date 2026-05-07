# PostgreSQL Engine Wiki

An LLM-maintained knowledge base for PostgreSQL engine internals, built with source-backed accuracy and version-aware documentation.

## Overview

This repository contains a comprehensive wiki focused on PostgreSQL's internal architecture, implementation details, and operational characteristics. Unlike traditional documentation, this wiki is maintained by AI agents that cite actual PostgreSQL source code, ensuring claims are grounded in the implementation rather than speculation.

The wiki emphasizes **source-backed knowledge**: all technical claims must cite specific PostgreSQL source files, functions, structures, or commits. Uncertain information is explicitly marked under "Open Questions" rather than presented as fact.

## Key Features

- **Version-Aware**: Supports multiple PostgreSQL versions with dedicated content for each major release
- **Source-Cited**: Every technical claim links to the actual PostgreSQL source code
- **AI-Maintained**: Content is generated and maintained by specialized AI agents
- **Operational Focus**: Emphasis on production deployment, tuning, and troubleshooting scenarios
- **Tool-Assisted**: Includes custom tooling for source navigation and wiki maintenance

## Supported Versions

| Version | Status | Branch | Key Features |
|---------|--------|--------|--------------|
| 18 | Primary | `REL_18_STABLE` | Current primary version with full project-context packs |
| 12 | Legacy | `REL_12_STABLE` | Legacy support with extensive operational questions |

## Project Structure

```
├── wiki/                          # Wiki content
│   ├── index.md                   # Global wiki catalog
│   ├── overview.md                # Architecture overview
│   ├── versions.md                # Version index and pins
│   ├── log.md                     # Activity changelog
│   ├── v18/                       # PostgreSQL 18 content
│   │   ├── index.md              # Version landing page
│   │   ├── concepts/             # Architecture concepts
│   │   ├── questions/            # Answered questions
│   │   └── subsystems/           # Subsystem documentation
│   └── v12/                      # PostgreSQL 12 content
├── raw/                          # PostgreSQL source checkouts
│   ├── postgres-18/              # PG 18 source (pinned commit)
│   └── postgres-12/              # PG 12 source (pinned commit)
├── .wiki-runtime/                # Generated artifacts
│   └── context/postgres-NN/      # Per-version context packs
├── scripts/                      # Maintenance tooling
│   ├── source_lookup             # Source code search
│   ├── source_deps               # Dependency analysis
│   ├── source_context            # Context pack generation
│   ├── wiki_lint                 # Wiki health checks
│   └── ...
└── templates/                    # Content templates
```

## Getting Started

### Prerequisites

- Git
- Python 3.8+ (for tooling scripts)
- PostgreSQL development tools (optional, for building source)

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/person123git/postgres-llm-wiki.git
   cd postgres-llm-wiki
   ```

2. **Explore the wiki:**
   - Start with [[wiki/index]] for the global catalog
   - Visit [[wiki/versions]] for version information
   - Check [[wiki/overview]] for architecture concepts

3. **Use the maintenance tools:**
   ```bash
   # View recent wiki activity
   ./scripts/recent_log --limit 10

   # Search PostgreSQL 18 source code
   ./scripts/source_lookup --version 18 --symbol ExecutorRun

   # Check wiki health
   ./scripts/wiki_lint
   ```

## Source Navigation

The wiki includes powerful tools for exploring PostgreSQL's source code:

### Source Lookup
```bash
# Find a specific function
./scripts/source_lookup --version 18 --symbol ExecutorRun

# Search with regex patterns
./scripts/source_lookup --version 18 --symbol '\bXLogRead\b' --regex

# View source file contents
./scripts/source_lookup --version 18 --path src/backend/executor/execMain.c --start 1 --limit 50
```

### Dependency Analysis
```bash
# Find what files include a header
./scripts/source_deps --version 18 --includes src/backend/executor/execMain.c

# Find reverse dependencies
./scripts/source_deps --version 18 --included-by executor/executor.h

# Get compile flags for a file
./scripts/source_deps --version 18 --compile-unit src/backend/executor/execMain.c
```

### Context Packs

Each supported PostgreSQL version has a generated "context pack" containing:
- Source tree structure (`tree-L4.txt`)
- Build configuration and compiler databases (`compile_commands.json`)
- Include dependency graphs (`include-deps.txt`)
- Focused call graphs for key entry points (`callgraphs/`)

## Content Organization

### Wiki Structure
- **Concepts**: Architecture and design explanations
- **Questions**: Specific technical questions with detailed answers
- **Subsystems**: Component-level documentation
- **Operations**: Deployment and maintenance guidance

### Version-Specific Content
Content is organized under `wiki/vNN/` directories where `NN` is the PostgreSQL major version. This ensures version accuracy and prevents confusion between releases.

### Citation Format
All technical claims cite source code using the format:
```
[[raw/postgres-NN/src/backend/executor/execMain.c#ExecutorRun]]
```

## Maintenance Tooling

The repository includes comprehensive tooling for wiki maintenance:

| Script | Purpose |
|--------|---------|
| `source_lookup` | Search and display PostgreSQL source code |
| `source_deps` | Analyze include dependencies and compile contexts |
| `source_context` | Generate per-version context packs |
| `source_context_check` | Validate context pack integrity |
| `wiki_lint` | Check wiki health and fix issues |
| `recent_log` | Display recent wiki activity |
| `version_diff` | Compare source across versions |

## Contributing

### For AI Agents
This wiki is designed to be maintained by AI agents following specific protocols:

1. **Read AGENTS.md** for complete operating instructions
2. **Use deep inquiry mode** for all technical questions
3. **Cite source evidence** for every behavioral claim
4. **Mark uncertainty** under "Open Questions"
5. **Update indexes** after creating/modifying content

### For Humans
- **Report issues** with source citations or technical accuracy
- **Suggest questions** that need answering
- **Contribute tooling** improvements
- **Review agent-generated content** for accuracy

## Key Principles

1. **Source-Backed**: Claims must cite actual PostgreSQL source code
2. **Version-Aware**: Content is scoped to specific PostgreSQL versions
3. **Uncertainty-Preserved**: Unknown information is explicitly marked
4. **Tool-Assisted**: Maintenance uses specialized tooling
5. **AI-Maintained**: Content is generated and verified by AI agents

## License

This project is licensed under the MIT License - see the [LICENCE](LICENCE) file for details.

## Related Resources

- [PostgreSQL Official Documentation](https://www.postgresql.org/docs/)
- [PostgreSQL Source Code](https://github.com/postgres/postgres)
- [PostgreSQL Developer Documentation](https://www.postgresql.org/docs/current/internals.html)