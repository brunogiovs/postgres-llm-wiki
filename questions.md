# Hermes Chat Prompts

Prompts for asking the Hermes agent about this wiki. Hermes runs with `WIKI_AGENT_WORKDIR=/data/repos/pg-wiki`, so it has direct file access. The canonical reading rules live in `AGENTS.md`.

## Reusable Template

```
You are working in /data/repos/pg-wiki. Follow the rules in AGENTS.md.

Before answering:
1. Read wiki/versions.md to find the primary PostgreSQL version.
2. Read wiki/index.md and wiki/v<NN>/index.md for the relevant version.
3. If a wiki page already covers this, cite it with an Obsidian link
   (e.g. [[v18/code-paths/simple-select-query]]).
4. If you need to verify a claim, search raw/postgres-<NN>/ and cite
   file:symbol (e.g. src/backend/executor/execMain.c:ExecutorRun).
5. Do not answer about one version using another version's checkout.
6. If something is uncertain, say so under "Open Questions" instead of guessing.

Question: <your question here>
```

## Pure Wiki Lookup

Use when the answer should already be in the wiki and you do not want Hermes to open the source tree.

```
Read wiki/index.md and wiki/v18/index.md, then summarize what the wiki
already says about the simple SELECT code path in PG 18. Quote the
Obsidian links to the pages you used. Do not open raw/postgres-18/.
```

## Wiki Plus Source Verification

Use when you need a grounded answer, including file and symbol citations.

```
In /data/repos/pg-wiki, follow AGENTS.md.

Question: in PostgreSQL 18, where does ExecutorRun decide whether to
push the tuple to the destination receiver vs. just count it? Cite the
relevant wiki page under wiki/v18/ if it exists, plus the file:symbol
in raw/postgres-18/. Assume the primary version from wiki/versions.md.
```

## Answer And File

Use when the answer should become a durable wiki page.

```
Follow AGENTS.md. Answer this for the primary version, then file the
answer as wiki/v<NN>/questions/<slug>.md and update wiki/v<NN>/index.md,
wiki/index.md, and wiki/log.md per the "Answer And File" workflow.

Question: <...>
```

## Prompting Tips

- Name the version explicitly when it matters (`for PG 18, ...`); otherwise Hermes assumes the primary version from `wiki/versions.md` and should say so.
- Keep one subsystem or one code path per prompt. The local 9B model loses the call chain on multi-topic queries (see the operating rules in `AGENTS.md`).
- Ask for citations explicitly (`cite file:symbol`); without that, the model will sometimes paraphrase without grounding.
- For durable questions, say "file the answer" so Hermes runs the Answer-And-File workflow and updates the indexes plus `wiki/log.md`.
