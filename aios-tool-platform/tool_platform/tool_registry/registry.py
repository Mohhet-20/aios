"""CategoryRegistry: the data-driven catalog of all 37 built-in tool
categories. Each entry describes policy/metadata only — sensible
default capabilities, whether tools of this category are sandboxed by
default, what kind of auth they typically need, and (when a reference
connector exists) which key into `connectors/registry.py` actually
executes calls of that category. Adding a 38th category, or a new
*preset* within an existing category, is a row insert here — not a
change to the execution engine, which only ever looks up a category or
connector_key, never branches on either by name."""
from __future__ import annotations

from dataclasses import dataclass, field

from tool_platform.domain.enums import ToolCategory


@dataclass(frozen=True)
class CategorySpec:
    key: str
    name: str
    description: str
    default_capabilities: list[str] = field(default_factory=list)
    default_auth_type: str = "none"
    sandboxed_by_default: bool = False
    network_access_by_default: bool = False
    connector_key: str | None = None


CATEGORY_SPECS: list[CategorySpec] = [
    CategorySpec(ToolCategory.WEB_SEARCH.value, "Web Search", "Query a web search engine.",
                 default_capabilities=["network_access"], default_auth_type="api_key", network_access_by_default=True, connector_key="web_search"),
    CategorySpec(ToolCategory.HTTP_CLIENT.value, "HTTP Client", "Generic HTTP request execution.",
                 default_capabilities=["network_access"], network_access_by_default=True, connector_key="http_client"),
    CategorySpec(ToolCategory.REST_API.value, "REST API", "Call a REST endpoint per an OpenAPI-style contract.",
                 default_capabilities=["network_access"], default_auth_type="api_key", network_access_by_default=True, connector_key="http_client"),
    CategorySpec(ToolCategory.GRAPHQL_API.value, "GraphQL API", "Call a GraphQL endpoint.",
                 default_capabilities=["network_access"], default_auth_type="api_key", network_access_by_default=True, connector_key="http_client"),
    CategorySpec(ToolCategory.PYTHON_EXECUTION.value, "Python Execution", "Run arbitrary Python in a sandbox.",
                 default_capabilities=["code_execution"], sandboxed_by_default=True, connector_key="python_execution"),
    CategorySpec(ToolCategory.SHELL_COMMAND.value, "Shell Commands", "Run a shell command in a sandbox.",
                 default_capabilities=["code_execution"], sandboxed_by_default=True, connector_key="shell_command"),
    CategorySpec(ToolCategory.FILE_MANAGER.value, "File Manager", "Read/write/list files in a scoped workspace directory.",
                 default_capabilities=["read_file", "write_file"], sandboxed_by_default=True, connector_key="file_manager"),
    CategorySpec(ToolCategory.PDF_READER.value, "PDF Reader", "Extract text/tables from a PDF.",
                 default_capabilities=["read_file"], connector_key="document_reader"),
    CategorySpec(ToolCategory.WORD_READER.value, "Word Reader", "Extract text from a .docx document.",
                 default_capabilities=["read_file"], connector_key="document_reader"),
    CategorySpec(ToolCategory.EXCEL_READER.value, "Excel Reader", "Extract tabular data from a spreadsheet.",
                 default_capabilities=["read_file"], connector_key="document_reader"),
    CategorySpec(ToolCategory.CSV_PROCESSOR.value, "CSV Processor", "Parse/transform CSV data.",
                 default_capabilities=["read_file"], connector_key="document_reader"),
    CategorySpec(ToolCategory.IMAGE_PROCESSING.value, "Image Processing", "Transform/analyze an image.",
                 default_capabilities=["read_file"], connector_key="media_processing"),
    CategorySpec(ToolCategory.OCR.value, "OCR", "Extract text from an image or scanned document.",
                 default_capabilities=["read_file"], connector_key="media_processing"),
    CategorySpec(ToolCategory.AUDIO_PROCESSING.value, "Audio Processing", "Transcribe or transform audio.",
                 default_capabilities=["read_file"], connector_key="media_processing"),
    CategorySpec(ToolCategory.VIDEO_PROCESSING.value, "Video Processing", "Transform or extract frames/audio from video.",
                 default_capabilities=["read_file"], connector_key="media_processing"),
    CategorySpec(ToolCategory.DOCUMENT_PARSER.value, "Document Parser", "Generic structured document parsing.",
                 default_capabilities=["read_file"], connector_key="document_reader"),
    CategorySpec(ToolCategory.EMBEDDING_GENERATOR.value, "Embedding Generator", "Generate vector embeddings via the AI Core.",
                 default_capabilities=["network_access"], connector_key="embedding_generator"),
    CategorySpec(ToolCategory.DATABASE_QUERY.value, "Database Query", "Run a parameterized query against a configured database.",
                 default_capabilities=["network_access"], default_auth_type="managed", network_access_by_default=True, connector_key="database_query"),
    CategorySpec(ToolCategory.SQL.value, "SQL", "Run a SQL statement against a relational database.",
                 default_capabilities=["network_access"], default_auth_type="managed", network_access_by_default=True, connector_key="database_query"),
    CategorySpec(ToolCategory.NOSQL.value, "NoSQL", "Run a query against a document/key-value store.",
                 default_capabilities=["network_access"], default_auth_type="managed", network_access_by_default=True, connector_key="database_query"),
    CategorySpec(ToolCategory.VECTOR_DATABASE.value, "Vector Database", "Query a vector index for nearest neighbors.",
                 default_capabilities=["network_access"], default_auth_type="managed", network_access_by_default=True, connector_key="database_query"),
    CategorySpec(ToolCategory.KNOWLEDGE_GRAPH.value, "Knowledge Graph", "Query a graph database / knowledge graph.",
                 default_capabilities=["network_access"], default_auth_type="managed", network_access_by_default=True, connector_key="database_query"),
    CategorySpec(ToolCategory.EMAIL.value, "Email", "Send or read email.",
                 default_capabilities=["network_access", "sends_email"], default_auth_type="oauth2", network_access_by_default=True, connector_key="notification"),
    CategorySpec(ToolCategory.CALENDAR.value, "Calendar", "Read/write calendar events.",
                 default_capabilities=["network_access"], default_auth_type="oauth2", network_access_by_default=True, connector_key="notification"),
    CategorySpec(ToolCategory.NOTIFICATION.value, "Notification", "Send a notification to a channel/user.",
                 default_capabilities=["network_access"], default_auth_type="api_key", network_access_by_default=True, connector_key="notification"),
    CategorySpec(ToolCategory.CLOUD_STORAGE.value, "Cloud Storage", "Read/write objects in cloud object storage.",
                 default_capabilities=["network_access", "read_file", "write_file"], default_auth_type="managed", network_access_by_default=True, connector_key="cloud_storage"),
    CategorySpec(ToolCategory.GITHUB.value, "GitHub", "Interact with GitHub repos/issues/PRs.",
                 default_capabilities=["network_access"], default_auth_type="oauth2", network_access_by_default=True, connector_key="github"),
    CategorySpec(ToolCategory.GITLAB.value, "GitLab", "Interact with GitLab projects/issues/MRs.",
                 default_capabilities=["network_access"], default_auth_type="oauth2", network_access_by_default=True, connector_key="github"),
    CategorySpec(ToolCategory.SLACK.value, "Slack", "Post messages / read channels in Slack.",
                 default_capabilities=["network_access", "sends_message"], default_auth_type="oauth2", network_access_by_default=True, connector_key="slack"),
    CategorySpec(ToolCategory.DISCORD.value, "Discord", "Post messages / read channels in Discord.",
                 default_capabilities=["network_access", "sends_message"], default_auth_type="oauth2", network_access_by_default=True, connector_key="slack"),
    CategorySpec(ToolCategory.JIRA.value, "Jira", "Create/query issues in Jira.",
                 default_capabilities=["network_access"], default_auth_type="oauth2", network_access_by_default=True, connector_key="github"),
    CategorySpec(ToolCategory.CONFLUENCE.value, "Confluence", "Create/query pages in Confluence.",
                 default_capabilities=["network_access"], default_auth_type="oauth2", network_access_by_default=True, connector_key="github"),
    CategorySpec(ToolCategory.CRM.value, "CRM", "Read/write CRM records (contacts, deals, accounts).",
                 default_capabilities=["network_access"], default_auth_type="oauth2", network_access_by_default=True, connector_key="http_client"),
    CategorySpec(ToolCategory.ERP.value, "ERP", "Read/write ERP records (orders, inventory, invoices).",
                 default_capabilities=["network_access"], default_auth_type="oauth2", network_access_by_default=True, connector_key="http_client"),
    CategorySpec(ToolCategory.CUSTOM_ENTERPRISE_API.value, "Custom Enterprise API", "A bespoke internal API integration.",
                 default_capabilities=["network_access"], default_auth_type="api_key", network_access_by_default=True, connector_key="http_client"),
    CategorySpec(ToolCategory.MCP_SERVER.value, "MCP Server", "A tool backed by a Model Context Protocol server.",
                 default_capabilities=["network_access"], default_auth_type="managed", network_access_by_default=True, connector_key="mcp_server"),
    CategorySpec(ToolCategory.CUSTOM.value, "Custom", "A fully custom tool with no built-in connector.",
                 default_capabilities=[]),
]

_BY_KEY = {spec.key: spec for spec in CATEGORY_SPECS}


def get_category_spec(category: str) -> CategorySpec | None:
    return _BY_KEY.get(category)
