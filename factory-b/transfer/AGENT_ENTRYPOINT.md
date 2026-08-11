# AGENT ENTRYPOINT — Factory B Transfer System

You are receiving a self-contained Factory B task. Treat the files in the transfer packet as the entire authorized task context unless the packet explicitly names another source.

1. Read `transfer_packet.json` first.
2. Read only the paths listed in `relevant_files` plus any repository-local instructions explicitly referenced there.
3. Do not rely on prior chat, unstated memory, unrelated repository files, or hidden context.
4. Change only paths inside `allowed_write_scope`.
5. Run every command in `required_tests` that is executable in the environment. Record the actual command and result.
6. Do not claim an action, test, release, or verification you did not perform.
7. Do not merge, deploy, publish, alter permissions, or modify external systems unless the packet explicitly authorizes that action.
8. Return a receipt conforming to `agent_result_receipt.schema.json`.

If a required input is missing, return `BLOCKED` with the smallest precise clarification needed. Do not invent missing requirements.
