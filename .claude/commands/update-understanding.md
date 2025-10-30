# Project Understanding Update

To ensure the LLM is always primed with complete and comprehensive project context, follow these steps:

1. **Mandatory Resource Ingestion**

- Ingest the full content of all existing `README.md` files for project overview and usage instructions.
- Ingest the full content of `PROJECT_UNDERSTANDING.md` for a high-level summary of the project and its components.
- Ingest every file from the `specs` directory for specifications and requirements, reading each file in its entirety.
- List every file from all `src` directories using `git ls-files`, and read each file completely.

2. **Analysis & Comprehension**

- Analyze all ingested resources in their entirety to develop a thorough understanding of the project's goals, architecture, coding standards, and requirements.
- Be prepared to answer questions or generate code that strictly follows the project's guidelines and objectives.

3. **Documentation Maintenance**

- Update `PROJECT_UNDERSTANDING.md` to reflect any new insights or changes in project understanding. If the file does not exist, create it.
  - Do not add a section for this priming snapshot, make the updates in place.
  - Make sure the updated document still makes sense wholistically.

**Note:**  
Do not modify any files other than `PROJECT_UNDERSTANDING.md`.  
Always prioritize clarity, completeness, and alignment with project standards when summarizing or generating content.
