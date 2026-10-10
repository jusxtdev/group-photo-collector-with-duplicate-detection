## Persistent Instruction: Maintain the API Contract

From now on, maintain `docs/api-contract.md` as the source of truth for the backend's externally observable API behavior.

### Before implementing a change

1. Read the relevant sections of `docs/api-contract.md`.
2. Inspect the existing implementation and tests.
3. Identify whether the requested change affects the API contract.

### After implementing a change

If the change affects the API contract, update `docs/api-contract.md` as part of the same task, after implementation and verification.

Document relevant changes to:

* Endpoints, HTTP methods, paths, and route parameters
* Query parameters, request headers, and request bodies
* Successful response status codes and response bodies
* Error status codes, error response formats, and relevant error conditions
* Authentication and authorization requirements
* Validation rules and constraints visible to API clients
* Pagination, filtering, sorting, and other externally observable behavior
* Resource relationships and important side effects
* Breaking changes or deprecated behavior

### Accuracy rules

* Treat the actual implementation and verified tests as the primary evidence. Use existing API documentation and tests as supporting evidence.
* Never invent endpoints, fields, response examples, status codes, or behavior.
* Distinguish verified behavior from behavior that remains uncertain.
* Preserve unrelated existing contract documentation.
* If behavior changes, update the existing entry rather than creating contradictory duplicate entries.
* If an endpoint is removed or a breaking change occurs, document it explicitly.
* Do not document internal implementation details unless they affect API consumers.

### Workflow

1. Implement the requested change.
2. Run relevant tests or other appropriate verification.
3. Update `docs/api-contract.md` to reflect the resulting behavior.
4. Review the code diff and contract diff for consistency.
5. Report implementation results, verification results, and contract updates in your final summary.

If the implementation fails or the behavior cannot be verified, do not document the intended behavior as if it were implemented successfully. Clearly report what remains incomplete.

If a change does not affect the externally observable API, leave the contract unchanged.

Do not modify unrelated code or expand the scope of the requested task just to update documentation.

This is a persistent project instruction. Follow it for all future backend tasks in this session.
