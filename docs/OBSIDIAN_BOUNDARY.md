# Obsidian Boundary

## Current authority

The active canonical vault is:

`/Users/wendellionaire/Documents/Wendellionaire`

Obsidian is the durable canonical knowledge and documentation layer. CADRE is the intelligence and execution layer beneath the Master Operating Doctrine. This application repository is the source of truth for application code only.

## Exact canonical references

| Concern                                                                                                                    | Canonical file and sections                                                                                                                                 |
| -------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Governing hierarchy, preservation, Source of Truth, scoped authority, validation, CADRE position, inheritance, sovereignty | `MASTER OPERATING DOCTRINE/Master_Operating_Doctrine_v1.2.md`, sections X-XIV and XX-XXI-A                                                                  |
| CADRE architecture                                                                                                         | `MASTER OPERATING DOCTRINE/CADRE Integration V2.md`, sections I-IV, VI-XVII, and XXI                                                                        |
| Invocation, authority, validation, handoff, output, write-back, exit                                                       | `MASTER OPERATING DOCTRINE/CADRE Invocation & Assembly Protocol.md`, sections I-III, VI-IX, XIII-XVIII, and XXII-XXIV                                       |
| Mission state and closeout                                                                                                 | `MASTER OPERATING DOCTRINE/CADRE Mission Control.md`, sections I-III, XIX, XXIII-XXIV, and XXVII-XXIX                                                       |
| Canonical status and promotion                                                                                             | `MASTER OPERATING DOCTRINE/Source of Truth Registry.md`, sections I-XII                                                                                     |
| Past / The Now / Next and version control                                                                                  | `MASTER OPERATING DOCTRINE/Change Control & Versioning.md`, sections II, XIII, XXII, and XXIV                                                               |
| Knowledge retrieval and write-back                                                                                         | `MASTER OPERATING DOCTRINE/Knowledge Architecture & Obsidian Protocol.md`, sections XVII and XXII-XXVIII                                                    |
| Software validation                                                                                                        | `MASTER OPERATING DOCTRINE/Validation Standards.md`, sections I-II, VI-VII, XIV-XX                                                                          |
| Automation controls                                                                                                        | `MASTER OPERATING DOCTRINE/Standards, SOP & Automation Protocol.md`, sections VIII-XX                                                                       |
| Repository/file placement                                                                                                  | `13 — System Directory & File Architecture.md`, Links Over Duplication, External File Storage, GitHub, Duplicate Truth Rule, and Interoperability Principle |

The application must retrieve these files from the configured vault location when an adapter is implemented. It must not embed rewritten doctrine in source code or database seed data.

## Initial adapter policy

1. Read-only first.
2. Resolve a configured, allow-listed vault root; reject path traversal.
3. Retrieve only the minimum necessary files or sections.
4. Preserve source path, version/status metadata, and a content checksum.
5. Never infer authority from recency, filename, search rank, or semantic similarity.
6. Never send the whole vault to an AI provider.
7. Fail closed when authority is ambiguous.

The repository includes an Obsidian adapter contract and an intentionally disabled implementation at `src/server/integrations/obsidian/`. No automatic read, write, or synchronization occurs in v0.1. Manual canonical context references are acceptable during the foundation stage.

## Write-back policy

Automatic bidirectional synchronization is deferred. CADRE may prepare a write-back proposal containing:

- record type;
- proposed destination;
- source and provenance;
- authorized scope;
- locked elements;
- change summary;
- validation evidence;
- required approver.

The application must not write, rename, move, merge, delete, or promote canonical vault content without the appropriate explicit authority. A completed application job is not permission to update the vault.

## Repository relationship

The vault should eventually record this repository's verified location, purpose, architecture, decisions, and approved release state. That write-back is a separate governed action after local validation; it is not performed by creating these application docs.
