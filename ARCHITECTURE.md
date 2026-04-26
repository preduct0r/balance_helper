# Architecture

The MVP is a layered Python application. The goal is a narrow platform/application agent today, with clear extension points for broader fundraising agents later.

## Layers

- `domain`: dataclasses and schemas that represent fundraising records.
- `clients`: external IO clients for Yandex LLM, Yandex Search, and page fetching.
- `extractors`: HTML/text/document normalization and LLM JSON parsing.
- `services`: business workflows such as discovery, analysis, checklists, drafts, and digests.
- `adapters`: storage, Telegram, Google Sheets, and CLI entrypoints.

## Dependency Direction

Domain code has no external dependencies. Services depend on domain models and interfaces. Adapters depend on services. External clients are lazy about optional dependencies so tests can run without network credentials.

## Stores

`LocalJsonStore` is the development and test store. `GoogleSheetsStore` implements the same logical table shape for production:

- `Opportunities`
- `Applications`
- `FundWiki`
- `Documents`
- `ActivityLog`

## Future Agents

Future modules should reuse the same domain/store/client boundaries:

- B2B partnerships
- private donor communication
- blogger and ambassador collaboration
- events and merch
- paid services and educational products

Do not add future-agent code until the feature is requested. Keep extension points small and explicit.

