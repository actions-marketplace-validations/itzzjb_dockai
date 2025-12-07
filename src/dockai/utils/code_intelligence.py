"""
DockAI Code Intelligence Module.

This module provides AST-based code analysis to extract structured information
from source files. It identifies entry points, imports, environment variables,
and other metadata crucial for accurate Dockerfile generation.

The analysis is 100% local and free - no LLM calls required.

Supported Languages:
- Python (via built-in ast module)
- JavaScript/TypeScript (basic pattern matching)
- Go (basic pattern matching)

Architecture:
    Source File → AST Parser → FileAnalysis
                      ↓
    Extracted: functions, classes, imports, entry points, env vars, ports
"""

import ast
import os
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set

logger = logging.getLogger("dockai")


@dataclass
class CodeSymbol:
    """
    Represents a code element extracted from AST analysis.
    
    Attributes:
        name: Symbol name (e.g., "main", "MyClass").
        type: Symbol type ("function", "class", "import", "variable").
        file: Source file path.
        line_start: Starting line number (1-indexed).
        line_end: Ending line number (1-indexed).
        signature: Function/method signature if applicable.
        docstring: Extracted docstring if present.
    """
    name: str
    type: str
    file: str
    line_start: int
    line_end: int
    signature: Optional[str] = None
    docstring: Optional[str] = None


@dataclass
class FileAnalysis:
    """
    Complete analysis result for a single source file.
    
    This dataclass contains all extracted metadata that helps
    the Dockerfile generator understand how the application works.
    
    Attributes:
        path: Relative file path.
        language: Detected programming language.
        symbols: List of extracted code symbols.
        imports: List of imported modules/packages.
        entry_points: Detected entry points (main functions, etc.).
        exposed_ports: Ports detected from code (e.g., app.listen(3000)).
        env_vars: Environment variable names referenced in code.
        framework_hints: Detected frameworks (e.g., "fastapi", "express").
    """
    path: str
    language: str
    symbols: List[CodeSymbol] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    exposed_ports: List[int] = field(default_factory=list)
    env_vars: List[str] = field(default_factory=list)
    framework_hints: List[str] = field(default_factory=list)


def analyze_python_file(filepath: str, content: str) -> FileAnalysis:
    """
    Analyze a Python file using the built-in ast module.
    
    Extracts:
    - Function and class definitions
    - Import statements
    - Entry points (main(), if __name__ == "__main__")
    - Environment variable usage (os.getenv, os.environ)
    - Port bindings (common patterns)
    - Framework detection (FastAPI, Flask, Django, etc.)
    
    Args:
        filepath: Relative path to the file.
        content: File content as string.
        
    Returns:
        FileAnalysis object with extracted metadata.
    """
    analysis = FileAnalysis(path=filepath, language="python")
    
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        logger.debug(f"Could not parse {filepath}: {e}")
        return analysis
    
    # Track detected patterns
    has_main_block = False
    
    for node in ast.walk(tree):
        # Extract function definitions
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            # Build signature
            args = []
            if hasattr(node, 'args') and node.args:
                for arg in node.args.args:
                    arg_name = arg.arg
                    if arg.annotation:
                        try:
                            arg_name += f": {ast.unparse(arg.annotation)}"
                        except:
                            pass
                    args.append(arg_name)
            
            signature = f"def {node.name}({', '.join(args)})"
            if node.returns:
                try:
                    signature += f" -> {ast.unparse(node.returns)}"
                except:
                    pass
            
            analysis.symbols.append(CodeSymbol(
                name=node.name,
                type="function",
                file=filepath,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                signature=signature,
                docstring=ast.get_docstring(node)
            ))
            
            # Check for main entry point
            if node.name == "main":
                analysis.entry_points.append(f"{filepath}:main()")
        
        # Extract class definitions
        elif isinstance(node, ast.ClassDef):
            analysis.symbols.append(CodeSymbol(
                name=node.name,
                type="class",
                file=filepath,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                signature=f"class {node.name}",
                docstring=ast.get_docstring(node)
            ))
        
        # Extract imports
        elif isinstance(node, ast.Import):
            for alias in node.names:
                analysis.imports.append(alias.name)
                _detect_framework(alias.name, analysis)
        
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                analysis.imports.append(node.module)
                _detect_framework(node.module, analysis)
        
        # Detect environment variable usage
        elif isinstance(node, ast.Call):
            _extract_env_vars(node, analysis)
            _extract_ports(node, analysis)
        
        # Detect if __name__ == "__main__"
        elif isinstance(node, ast.If):
            if _is_main_block(node):
                has_main_block = True
    
    if has_main_block:
        analysis.entry_points.append(f"{filepath}:__main__")
    
    # Deduplicate
    analysis.imports = list(set(analysis.imports))
    analysis.env_vars = list(set(analysis.env_vars))
    analysis.exposed_ports = list(set(analysis.exposed_ports))
    analysis.framework_hints = list(set(analysis.framework_hints))
    
    return analysis


def _is_main_block(node: ast.If) -> bool:
    """Check if an If node is: if __name__ == "__main__"."""
    try:
        if isinstance(node.test, ast.Compare):
            left = node.test.left
            if isinstance(left, ast.Name) and left.id == "__name__":
                for comparator in node.test.comparators:
                    if isinstance(comparator, ast.Constant) and comparator.value == "__main__":
                        return True
    except:
        pass
    return False


def _extract_env_vars(node: ast.Call, analysis: FileAnalysis) -> None:
    """Extract environment variable references from a Call node."""
    try:
        # os.getenv("VAR") or os.environ.get("VAR")
        if hasattr(node.func, 'attr') and node.func.attr in ('getenv', 'get'):
            if node.args and isinstance(node.args[0], ast.Constant):
                var_name = node.args[0].value
                if isinstance(var_name, str):
                    analysis.env_vars.append(var_name)
        
        # os.environ["VAR"]
        if isinstance(node.func, ast.Subscript):
            if hasattr(node.func.value, 'attr') and node.func.value.attr == 'environ':
                if isinstance(node.func.slice, ast.Constant):
                    var_name = node.func.slice.value
                    if isinstance(var_name, str):
                        analysis.env_vars.append(var_name)
    except:
        pass


def _extract_ports(node: ast.Call, analysis: FileAnalysis) -> None:
    """Extract port numbers from common patterns."""
    try:
        # Look for patterns like: run(port=8000), listen(3000), bind(("", 5000))
        func_name = ""
        if hasattr(node.func, 'attr'):
            func_name = node.func.attr
        elif hasattr(node.func, 'id'):
            func_name = node.func.id
        
        if func_name in ('run', 'listen', 'bind', 'serve'):
            # Check keyword arguments
            for kw in node.keywords:
                if kw.arg == 'port' and isinstance(kw.value, ast.Constant):
                    port = kw.value.value
                    if isinstance(port, int) and 1 <= port <= 65535:
                        analysis.exposed_ports.append(port)
            
            # Check positional arguments for port numbers
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                    port = arg.value
                    if 1000 <= port <= 65535:  # Likely a port
                        analysis.exposed_ports.append(port)
    except:
        pass


def _detect_framework(module_name: str, analysis: FileAnalysis) -> None:
    """Detect frameworks from import statements."""
    framework_map = {
        'fastapi': 'FastAPI',
        'flask': 'Flask',
        'django': 'Django',
        'starlette': 'Starlette',
        'tornado': 'Tornado',
        'aiohttp': 'aiohttp',
        'sanic': 'Sanic',
        'uvicorn': 'Uvicorn',
        'gunicorn': 'Gunicorn',
        'celery': 'Celery',
        'dramatiq': 'Dramatiq',
        'pytest': 'pytest',
        'streamlit': 'Streamlit',
        'gradio': 'Gradio',
    }
    
    base_module = module_name.split('.')[0].lower()
    if base_module in framework_map:
        analysis.framework_hints.append(framework_map[base_module])


def analyze_javascript_file(filepath: str, content: str) -> FileAnalysis:
    """
    Analyze a JavaScript/TypeScript file using regex patterns.
    
    Note: This is a lightweight analysis without a full parser.
    For production use, consider using tree-sitter.
    
    Args:
        filepath: Relative path to the file.
        content: File content as string.
        
    Returns:
        FileAnalysis object with extracted metadata.
    """
    ext = os.path.splitext(filepath)[1].lower()
    language = "typescript" if ext in ('.ts', '.tsx') else "javascript"
    analysis = FileAnalysis(path=filepath, language=language)
    
    # Detect imports
    import_patterns = [
        r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]',
        r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
    ]
    for pattern in import_patterns:
        for match in re.finditer(pattern, content):
            analysis.imports.append(match.group(1))
    
    # Detect framework hints
    js_frameworks = {
        'express': 'Express',
        'fastify': 'Fastify',
        'koa': 'Koa',
        'hapi': 'Hapi',
        'next': 'Next.js',
        'nuxt': 'Nuxt.js',
        'react': 'React',
        'vue': 'Vue',
        'angular': 'Angular',
        'nest': 'NestJS',
    }
    for imp in analysis.imports:
        base = imp.split('/')[0].lower()
        if base in js_frameworks:
            analysis.framework_hints.append(js_frameworks[base])
    
    # Detect ports
    port_patterns = [
        r'\.listen\s*\(\s*(\d+)',
        r'port\s*[=:]\s*(\d+)',
        r'PORT\s*[=:]\s*(\d+)',
    ]
    for pattern in port_patterns:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            try:
                port = int(match.group(1))
                if 1000 <= port <= 65535:
                    analysis.exposed_ports.append(port)
            except:
                pass
    
    # Detect env vars
    env_patterns = [
        r'process\.env\.(\w+)',
        r'process\.env\[[\'"](\w+)[\'"]\]',
    ]
    for pattern in env_patterns:
        for match in re.finditer(pattern, content):
            analysis.env_vars.append(match.group(1))
    
    # Detect entry points
    if re.search(r'app\.listen|server\.listen|createServer', content):
        analysis.entry_points.append(f"{filepath}:server")
    
    # Deduplicate
    analysis.imports = list(set(analysis.imports))
    analysis.env_vars = list(set(analysis.env_vars))
    analysis.exposed_ports = list(set(analysis.exposed_ports))
    analysis.framework_hints = list(set(analysis.framework_hints))
    
    return analysis


def analyze_go_file(filepath: str, content: str) -> FileAnalysis:
    """
    Analyze a Go file using regex patterns.
    
    Note: This is a lightweight analysis without a full parser.
    
    Args:
        filepath: Relative path to the file.
        content: File content as string.
        
    Returns:
        FileAnalysis object with extracted metadata.
    """
    analysis = FileAnalysis(path=filepath, language="go")
    
    # Detect package
    pkg_match = re.search(r'package\s+(\w+)', content)
    if pkg_match and pkg_match.group(1) == "main":
        # Check for main function
        if re.search(r'func\s+main\s*\(\s*\)', content):
            analysis.entry_points.append(f"{filepath}:main()")
    
    # Detect imports
    import_block = re.search(r'import\s*\((.*?)\)', content, re.DOTALL)
    if import_block:
        for match in re.finditer(r'[\'"]([^\'"]+)[\'"]', import_block.group(1)):
            analysis.imports.append(match.group(1))
    
    single_imports = re.finditer(r'import\s+[\'"]([^\'"]+)[\'"]', content)
    for match in single_imports:
        analysis.imports.append(match.group(1))
    
    # Detect ports
    port_patterns = [
        r'ListenAndServe\s*\(\s*[\'"]?:(\d+)',
        r'Listen\s*\(\s*[\'"]?:?(\d+)',
        r':(\d+)',
    ]
    for pattern in port_patterns:
        for match in re.finditer(pattern, content):
            try:
                port = int(match.group(1))
                if 1000 <= port <= 65535:
                    analysis.exposed_ports.append(port)
                    break  # Take first match
            except:
                pass
    
    # Detect env vars
    env_patterns = [
        r'os\.Getenv\s*\(\s*[\'"](\w+)[\'"]\s*\)',
        r'os\.LookupEnv\s*\(\s*[\'"](\w+)[\'"]\s*\)',
    ]
    for pattern in env_patterns:
        for match in re.finditer(pattern, content):
            analysis.env_vars.append(match.group(1))
    
    # Detect frameworks
    go_frameworks = {
        'gin-gonic/gin': 'Gin',
        'labstack/echo': 'Echo',
        'gorilla/mux': 'Gorilla',
        'go-chi/chi': 'Chi',
        'gofiber/fiber': 'Fiber',
    }
    for imp in analysis.imports:
        for pattern, framework in go_frameworks.items():
            if pattern in imp:
                analysis.framework_hints.append(framework)
    
    # Deduplicate
    analysis.imports = list(set(analysis.imports))
    analysis.env_vars = list(set(analysis.env_vars))
    analysis.exposed_ports = list(set(analysis.exposed_ports))
    analysis.framework_hints = list(set(analysis.framework_hints))
    
    return analysis


def analyze_file(filepath: str, content: str) -> Optional[FileAnalysis]:
    """
    Analyze a source file based on its extension.
    
    This is the main entry point for code analysis. It detects the
    language from the file extension and dispatches to the appropriate
    analyzer.
    
    Args:
        filepath: Relative path to the file.
        content: File content as string.
        
    Returns:
        FileAnalysis object if the file type is supported, None otherwise.
    """
    ext = os.path.splitext(filepath)[1].lower()
    filename = os.path.basename(filepath)
    
    # Python
    if ext == ".py":
        return analyze_python_file(filepath, content)
    
    # JavaScript/TypeScript
    if ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
        return analyze_javascript_file(filepath, content)
    
    # Go
    if ext == ".go":
        return analyze_go_file(filepath, content)
        
    # Manifest Files (Better Framework Detection)
    if filename == "package.json":
        return analyze_package_json(filepath, content)
    if filename == "go.mod":
        return analyze_go_mod(filepath, content)
    if filename == "requirements.txt":
        return analyze_requirements_txt(filepath, content)
    if filename == "pyproject.toml":
        return analyze_pyproject_toml(filepath, content)
    
    # Generic analysis for all other text-based files
    return analyze_generic_file(filepath, content)


def analyze_package_json(filepath: str, content: str) -> FileAnalysis:
    """Analyze package.json for JS/TS frameworks."""
    analysis = FileAnalysis(path=filepath, language="json")
    try:
        # Simple string matching to avoid json parse errors on loose files
        # framework_map key: (dependency_name, Display Name)
        frameworks = {
            '"express"': "Express",
            '"@nestjs/core"': "NestJS",
            '"next"': "Next.js",
            '"nuxt"': "Nuxt.js",
            '"react"': "React",
            '"vue"': "Vue",
            '"svelte"': "Svelte",
            '"@sveltejs/kit"': "SvelteKit",
            '"fastify"': "Fastify",
            '"koa"': "Koa",
            '"hapi"': "Hapi",
            '"@remix-run/node"': "Remix",
            '"astro"': "Astro",
            '"adonis"': "AdonisJS",
            '"meteor"': "Meteor"
        }
        
        for key, name in frameworks.items():
            if key in content:
                analysis.framework_hints.append(name)
                
        # Also Extract scripts as "entry points" hints
        if '"start":' in content:
            # simple extraction
            start_script = re.search(r'"start":\s*"([^"]+)"', content)
            if start_script:
                analysis.entry_points.append(f"npm run start ({start_script.group(1)})")
                
    except Exception as e:
        logger.debug(f"Error parsing package.json: {e}")
        
    return analysis


def analyze_go_mod(filepath: str, content: str) -> FileAnalysis:
    """Analyze go.mod for Go frameworks."""
    analysis = FileAnalysis(path=filepath, language="go-mod")
    
    frameworks = {
        'github.com/gin-gonic/gin': 'Gin',
        'github.com/labstack/echo': 'Echo',
        'github.com/gofiber/fiber': 'Fiber',
        'github.com/go-chi/chi': 'Chi',
        'github.com/beego/beego': 'Beego',
        'github.com/revel/revel': 'Revel',
        'github.com/kataras/iris': 'Iris',
        'github.com/gorilla/mux': 'Gorilla Mux'
    }
    
    for pkg, name in frameworks.items():
        if pkg in content:
            analysis.framework_hints.append(name)
            
    return analysis


def analyze_requirements_txt(filepath: str, content: str) -> FileAnalysis:
    """Analyze requirements.txt for Python frameworks."""
    analysis = FileAnalysis(path=filepath, language="pip-requirements")
    
    frameworks = {
        'fastapi': 'FastAPI',
        'flask': 'Flask',
        'django': 'Django',
        'pyramid': 'Pyramid',
        'bottle': 'Bottle',
        'tornado': 'Tornado',
        'falcon': 'Falcon',
        'sanic': 'Sanic',
        'starlette': 'Starlette',
        'litestar': 'Litestar',
        'quart': 'Quart',
        'streamlit': 'Streamlit',
        'dash': 'Dash'
    }
    
    # Case insensitive search
    content_lower = content.lower()
    for pkg, name in frameworks.items():
        # Match start of line, optional whitespace, package name, boundary
        if re.search(rf'^\s*{pkg}\b', content_lower, re.MULTILINE):
            analysis.framework_hints.append(name)
            
    return analysis


def analyze_pyproject_toml(filepath: str, content: str) -> FileAnalysis:
    """Analyze pyproject.toml for Python frameworks."""
    # Similar to requirements but looks for key names
    analysis = FileAnalysis(path=filepath, language="toml")
    
    # Re-use logic mostly
    return analyze_requirements_txt(filepath, content)




def analyze_generic_file(filepath: str, content: str) -> FileAnalysis:
    """
    Perform generic analysis on any text file using universal patterns.
    
    This ensures DockAI supports "every language there was and will be"
    by falling back to identifying common concepts like:
    - Environment variables (caps with underscores)
    - Port numbers
    - Framework hints (based on common keywords)
    
    Args:
        filepath: Relative path to the file.
        content: File content as string.
        
    Returns:
        FileAnalysis object with generic metadata.
    """
    ext = os.path.splitext(filepath)[1].lower().replace('.', '') or "unknown"
    analysis = FileAnalysis(path=filepath, language=ext)
    
    # Generic Env Var detection (SCREAMING_SNAKE_CASE)
    # Matches words with at least one underscore, all caps, length > 3
    # e.g., DATABASE_URL, API_KEY_V1
    env_pattern = r'\b[A-Z][A-Z0-9_]*_[A-Z0-9_]+\b'
    potential_envs = re.findall(env_pattern, content)
    
    # Filter out common noise
    noise = {'STDIN', 'STDOUT', 'STDERR', 'UTF8', 'UUID', 'JSON', 'HTML', 'HTTP', 'HTTPS', 'TODO', 'FIXME'}
    analysis.env_vars = list(set([e for e in potential_envs if e not in noise]))
    
    # Generic Port detection (1024-65535)
    # Look for assignment-like patterns: port = 8080, port: 8080, port: u16 = 8080
    # We allow some characters between 'port' and the number to handle type hints
    port_pattern = r'(?i)port.{0,20}[=:]\s*(\d{4,5})'
    for match in re.finditer(port_pattern, content):
        try:
            port = int(match.group(1))
            if 1024 <= port <= 65535:
                # Avoid year-like numbers if possible (2020-2030), though hard to distinguish
                analysis.exposed_ports.append(port)
        except:
            pass
            
    analysis.exposed_ports = list(set(analysis.exposed_ports))
    
    # Simple Framework/Language Hinting based on Shebang
    if content.startswith('#!'):
        first_line = content.split('\n')[0]
        if 'python' in first_line:
            analysis.language = 'python'
        elif 'node' in first_line:
            analysis.language = 'javascript'
        elif 'bash' in first_line or 'sh' in first_line:
            analysis.language = 'shell'
        elif 'ruby' in first_line:
            analysis.language = 'ruby'
        elif 'perl' in first_line:
            analysis.language = 'perl'
        elif 'php' in first_line:
            analysis.language = 'php'
            
    return analysis


def analyze_project(root_path: str, file_tree: List[str]) -> Dict[str, FileAnalysis]:
    """
    Analyze all supported source files in a project.
    
    Args:
        root_path: Absolute path to project root.
        file_tree: List of relative file paths.
        
    Returns:
        Dictionary mapping file paths to their analysis results.
    """
    results = {}
    analyzed = 0
    
    for rel_path in file_tree:
        abs_path = os.path.join(root_path, rel_path)
        
        try:
            with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            analysis = analyze_file(rel_path, content)
            if analysis:
                results[rel_path] = analysis
                analyzed += 1
                
        except Exception as e:
            logger.debug(f"Could not analyze {rel_path}: {e}")
    
    logger.info(f"Code intelligence: analyzed {analyzed} files")
    return results


def get_project_summary(analyses: Dict[str, FileAnalysis]) -> Dict:
    """
    Generate a summary of the entire project from individual file analyses.
    
    Args:
        analyses: Dictionary of file analyses.
        
    Returns:
        Summary dictionary with aggregated information.
    """
    summary = {
        "languages": set(),
        "frameworks": set(),
        "entry_points": [],
        "all_env_vars": set(),
        "all_ports": set(),
        "total_functions": 0,
        "total_classes": 0,
    }
    
    for path, analysis in analyses.items():
        summary["languages"].add(analysis.language)
        summary["frameworks"].update(analysis.framework_hints)
        summary["entry_points"].extend(analysis.entry_points)
        summary["all_env_vars"].update(analysis.env_vars)
        summary["all_ports"].update(analysis.exposed_ports)
        
        for sym in analysis.symbols:
            if sym.type == "function":
                summary["total_functions"] += 1
            elif sym.type == "class":
                summary["total_classes"] += 1
    
    # Convert sets to lists for JSON serialization
    summary["languages"] = list(summary["languages"])
    summary["frameworks"] = list(summary["frameworks"])
    summary["all_env_vars"] = list(summary["all_env_vars"])
    summary["all_ports"] = list(summary["all_ports"])
    
    return summary
