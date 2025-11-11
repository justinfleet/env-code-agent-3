"""
Specification Ingestion Agent - parses formal specs into internal format
"""

from ..core.base_agent import BaseAgent
from ..core.llm_client import LLMClient
from typing import Dict, Any, Optional
import json
import requests
import yaml


SPEC_INGESTION_SYSTEM_PROMPT = """You are an expert at parsing API specifications and documentation. Your job is to extract API information from various sources and convert it to a standardized internal format.

## Your Task:
Parse specifications from documentation pages, API specs, or structured files and convert to our internal specification format.

## Input Sources You Support:
1. **Documentation URLs** - HTML/Markdown pages with API documentation (e.g., RealWorld docs, REST API docs)
2. **OpenAPI 3.x Specs** (JSON or YAML) - Standard REST API spec format
3. **Custom JSON Specs** - Structured API specifications
4. **Multi-page Documentation** - May need to fetch multiple related pages

## Workflow for Documentation URLs:
1. Use `fetch_spec` to get the main documentation page
2. Analyze the content to understand the structure
3. If the spec is spread across multiple pages, use `fetch_spec` again for additional pages
4. **CRITICAL**: Extract and parse ALL endpoint information from the HTML/text:
   - Parse each endpoint's method, path, description
   - Extract request/response examples from the documentation
   - Identify all data fields and their types
   - Infer database schema from the data structures
5. **Build the complete specification object** with all endpoints and database tables
6. Call `output_specification` with the **full specification object** (not empty!)

## Output Format:
You must output valid JSON with this exact structure:
{
  "api_name": "string",
  "base_path": "string (e.g., /api)",
  "endpoints": [
    {
      "method": "GET|POST|PUT|DELETE",
      "path": "/api/resource",
      "description": "What this endpoint does",
      "query_params": ["param1", "param2"],
      "request_body": {
        "field1": "type",
        "field2": "type"
      },
      "response": {
        "field1": "type",
        "field2": "type"
      },
      "logic": "How it works and what data operations it performs"
    }
  ],
  "database": {
    "tables": [
      {
        "name": "table_name",
        "fields": [
          {"name": "id", "type": "INTEGER", "constraints": "PRIMARY KEY AUTOINCREMENT"},
          {"name": "field", "type": "TEXT|INTEGER|REAL", "constraints": "NOT NULL"}
        ]
      }
    ]
  }
}

## Database Schema Rules:
- Use SQLite types: TEXT, INTEGER, REAL, BLOB
- PRIMARY KEY should use INTEGER AUTOINCREMENT
- Infer table structure from request/response bodies
- Create foreign key relationships where appropriate (e.g., article_id → articles.id)
- Add indexes for commonly queried fields
- Include NOT NULL constraints where fields are required

## Important Guidelines:
1. **Parse Documentation Pages**: Extract endpoint info from HTML/Markdown documentation, not just structured specs
2. **Multi-page Specs**: If documentation spans multiple pages, fetch all relevant pages
3. **Infer Data Models**: From request/response schemas, infer complete database tables
4. **Relationships**: Identify foreign keys and relationships between entities
5. **Authentication**: Note which endpoints require auth (include auth_required field)
6. **Be Complete**: Include ALL endpoints from the documentation, don't skip any
7. **Logic**: For each endpoint, describe what database operations it performs
8. **Handle Various Formats**: HTML tables, markdown lists, JSON examples - extract the key information

## Examples:

### OpenAPI Schema to Table:
```
components:
  schemas:
    Article:
      properties:
        id: integer
        title: string
        body: string
        author_id: integer
```
→ Creates table "articles" with fields: id, title, body, author_id

### RealWorld Endpoint to Spec:
```
POST /api/articles
Body: { "article": { "title": "...", "body": "..." } }
Response: { "article": { "id": 1, "title": "...", ... } }
```
→ Creates endpoint + infers articles table structure
"""


class SpecificationIngestionAgent(BaseAgent):
    """Agent that ingests formal specifications and converts to internal format"""

    def __init__(self, llm: LLMClient):
        # Define tools for spec ingestion
        tools = [
            {
                "name": "fetch_spec",
                "description": "Fetch a specification from a URL",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL of the specification to fetch"
                        }
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "read_local_spec",
                "description": "Read a specification from a local file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the specification file"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "output_specification",
                "description": "Output the final parsed specification in internal format. IMPORTANT: You must provide the complete specification object with all endpoints and database schema. Do not call this with empty input!",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "specification": {
                            "type": "object",
                            "description": "Complete API specification in internal format with 'api_name', 'endpoints' array, and 'database' object with tables. Must be fully populated!",
                            "properties": {
                                "api_name": {"type": "string"},
                                "base_path": {"type": "string"},
                                "endpoints": {"type": "array"},
                                "database": {"type": "object"}
                            },
                            "required": ["api_name", "endpoints", "database"]
                        }
                    },
                    "required": ["specification"]
                }
            }
        ]

        super().__init__(
            llm=llm,
            tools=tools,
            tool_executor=self._execute_tool,
            system_prompt=SPEC_INGESTION_SYSTEM_PROMPT,
            max_iterations=25  # Increased for documentation crawling
        )
        self.specification = None
        self.spec_content = None

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Execute spec ingestion tools"""
        if tool_name == "fetch_spec":
            return self._fetch_spec(tool_input)
        elif tool_name == "read_local_spec":
            return self._read_local_spec(tool_input)
        elif tool_name == "output_specification":
            spec = tool_input.get("specification")

            # Validate spec is not empty
            if not spec:
                return {
                    "complete": False,
                    "success": False,
                    "error": "specification parameter is required and cannot be empty!",
                    "message": "❌ You must provide the complete specification object. Do not call output_specification with empty input!"
                }

            # Validate required fields
            required_fields = ["api_name", "endpoints", "database"]
            missing = [f for f in required_fields if f not in spec]
            if missing:
                return {
                    "complete": False,
                    "success": False,
                    "error": f"Missing required fields: {missing}",
                    "message": f"❌ Specification must include: {', '.join(required_fields)}"
                }

            self.specification = spec
            return {
                "complete": True,
                "message": "✅ Specification parsed and converted successfully"
            }
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _fetch_spec(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch specification from URL"""
        url = params.get("url")

        try:
            print(f"📥 Fetching spec from {url}...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            content = response.text
            self.spec_content = content

            # Try to parse as JSON/YAML
            try:
                data = json.loads(content)
                content_type = "JSON"
                # For structured specs, return as-is (already compact)
                print(f"✅ Fetched {len(content)} characters ({content_type} format)")
                return {
                    "success": True,
                    "content": content,
                    "content_type": content_type,
                    "url": url,
                    "message": f"Successfully fetched specification from {url}"
                }
            except json.JSONDecodeError:
                try:
                    data = yaml.safe_load(content)
                    content_type = "YAML"
                    # For structured specs, return as-is
                    print(f"✅ Fetched {len(content)} characters ({content_type} format)")
                    return {
                        "success": True,
                        "content": content,
                        "content_type": content_type,
                        "url": url,
                        "message": f"Successfully fetched specification from {url}"
                    }
                except:
                    # HTML/Markdown - needs extraction
                    content_type = "HTML/Markdown"
                    print(f"✅ Fetched {len(content)} characters ({content_type} format)")
                    print(f"🔍 Extracting structured data from HTML...")

                    # Extract summary instead of returning full HTML
                    summary = self._extract_html_summary(content)

                    print(f"✅ Extracted summary ({len(summary)} chars, reduced from {len(content)})")

                    return {
                        "success": True,
                        "content": summary,  # Return summary, not full HTML!
                        "content_type": content_type,
                        "url": url,
                        "original_size": len(content),
                        "summary_size": len(summary),
                        "message": f"Successfully fetched and extracted from {url} (reduced {len(content)} → {len(summary)} chars)"
                    }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Failed to fetch spec: {str(e)}"
            }

    def _extract_html_summary(self, html_content: str) -> str:
        """Extract key information from HTML, discarding markup"""
        from html.parser import HTMLParser

        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text_parts = []
                self.in_script = False
                self.in_style = False

            def handle_starttag(self, tag, attrs):
                if tag in ['script', 'style']:
                    self.in_script = True

            def handle_endtag(self, tag):
                if tag in ['script', 'style']:
                    self.in_script = False

            def handle_data(self, data):
                if not self.in_script and data.strip():
                    self.text_parts.append(data.strip())

        # Extract text from HTML
        parser = TextExtractor()
        try:
            parser.feed(html_content)
            text = '\n'.join(parser.text_parts)
        except:
            # Fallback: simple tag stripping
            import re
            text = re.sub(r'<[^>]+>', '', html_content)
            text = re.sub(r'\s+', ' ', text).strip()

        # Further reduce: Keep only lines with API-relevant keywords
        lines = text.split('\n')
        relevant_lines = []
        keywords = ['endpoint', 'api', 'request', 'response', 'post', 'get', 'put', 'delete',
                   'path', 'parameter', 'body', 'schema', 'authentication', 'token', 'header',
                   'example', 'json', 'field', 'type', 'required', 'optional']

        for line in lines:
            line_lower = line.lower()
            # Keep lines that contain API-relevant keywords or look like endpoints
            if any(kw in line_lower for kw in keywords) or '/' in line or '{' in line:
                relevant_lines.append(line)

        # Limit to reasonable size (max 10K chars)
        summary = '\n'.join(relevant_lines)
        if len(summary) > 10000:
            summary = summary[:10000] + "\n\n[Content truncated for token efficiency...]"

        return summary

    def _read_local_spec(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read specification from local file"""
        file_path = params.get("file_path")

        try:
            print(f"📂 Reading spec from {file_path}...")
            with open(file_path, 'r') as f:
                content = f.read()

            self.spec_content = content

            # Detect format
            if file_path.endswith('.json'):
                content_type = "JSON"
            elif file_path.endswith(('.yaml', '.yml')):
                content_type = "YAML"
            else:
                content_type = "Markdown/Text"

            print(f"✅ Read {len(content)} characters ({content_type} format)")

            return {
                "success": True,
                "content": content,
                "content_type": content_type,
                "file_path": file_path,
                "message": f"Successfully read specification from {file_path}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Failed to read spec: {str(e)}"
            }

    def ingest_spec(self, spec_source: str, source_type: str = "auto") -> Dict[str, Any]:
        """
        Ingest and parse a formal specification

        Args:
            spec_source: URL or file path to the specification
            source_type: "url", "file", or "auto" (default: auto-detect)

        Returns:
            Parsed specification in internal format
        """
        # Auto-detect source type if not specified
        if source_type == "auto":
            if spec_source.startswith(("http://", "https://")):
                source_type = "url"
            else:
                source_type = "file"

        # Create initial prompt
        if source_type == "url":
            initial_prompt = f"""Please parse the specification from this URL: {spec_source}

This URL may be:
- A documentation page (HTML/Markdown) with endpoint descriptions
- A structured API spec (OpenAPI JSON/YAML)
- A multi-page documentation site

Steps:
1. Use the fetch_spec tool to retrieve the content from the URL
2. Analyze the format and content:
   - If it's a documentation page, extract ALL endpoint information from the text/HTML
   - If it's structured JSON/YAML, parse the schema
   - If you see references to other pages with more endpoints, fetch those pages too
3. **Parse and extract the data** - Read through the fetched HTML/text and extract:
   - Every endpoint (method + path)
   - Request bodies and parameters
   - Response structures
   - Authentication requirements
4. **Build the complete specification object** with:
   - api_name, base_path
   - endpoints array (ALL endpoints you found)
   - database schema (inferred from request/response structures)
5. **Call output_specification with the FULL specification object** - Do NOT call it with empty input!

Be thorough - parse all endpoint details including:
- HTTP methods and paths
- Request parameters and bodies
- Response structures
- Authentication requirements
- Any business logic or validation rules mentioned

Then infer complete database schema with:
- All tables needed to store the data
- Proper field types (SQLite: TEXT, INTEGER, REAL)
- Foreign key relationships
- Primary keys (INTEGER AUTOINCREMENT)"""
        else:
            initial_prompt = f"""Please parse the specification from this file: {spec_source}

Steps:
1. Use the read_local_spec tool to read the specification
2. Analyze the spec format (OpenAPI, RealWorld, custom, etc.)
3. Convert it to our internal specification format
4. Use output_specification to provide the final result

Focus on:
- All endpoints with complete details
- Data models and their relationships
- Database schema (SQLite tables)
- Business logic for each endpoint"""

        print(f"\n{'='*70}")
        print(f"📋 PARSING SPECIFICATION")
        print(f"{'='*70}\n")
        print(f"Source: {spec_source}")
        print(f"Type: {source_type}\n")

        result = self.run(initial_prompt)

        if self.specification:
            print(f"\n✅ Specification parsed successfully!")
            print(f"   API: {self.specification.get('api_name', 'Unknown')}")
            print(f"   Endpoints: {len(self.specification.get('endpoints', []))}")
            print(f"   Tables: {len(self.specification.get('database', {}).get('tables', []))}\n")

            return {
                "success": True,
                "specification": self.specification,
                "source": spec_source,
                "source_type": source_type
            }
        else:
            return {
                "success": False,
                "error": "Failed to parse specification",
                "source": spec_source
            }
