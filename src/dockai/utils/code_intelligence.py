"""
DockAI Code Intelligence Module.

This module provides configuration-driven AST-based code analysis.
Instead of hardcoded patterns, it uses the language_configs module for
extensible, maintainable code intelligence.

Key Features:
- Configuration-driven (no hardcoded framework lists)
- Pattern-based matching (easier to extend)
- Support for 15+ languages (Python, JS, TS, Go, Rust, Ruby, PHP, Java, C#, Kotlin, Scala, Elixir, Haskell, Dart, Swift)
- Pluggable architecture for custom analyzers
- Better error handling and fallbacks

Architecture:
    Source File → Language Detection → Config Lookup → Pattern Matching → FileAnalysis
"""

import ast
import os
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set

from .language_configs import (
    get_language_config,
    get_all_supported_extensions,
    FrameworkPattern,
    LanguageConfig
)

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
    
    Attributes:
        path: Relative file path.
        language: Detected programming language.
        symbols: List of extracted code symbols.
        imports: List of imported modules/packages.
        entry_points: Detected entry points (main functions, etc.).
        exposed_ports: Ports detected from code (e.g., app.listen(3000)).
        env_vars: Environment variable names referenced in code.
        framework_hints: Detected frameworks (e.g., "FastAPI", "Express").
    """
    path: str
    language: str
    symbols: List[CodeSymbol] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    exposed_ports: List[int] = field(default_factory=list)
    env_vars: List[str] = field(default_factory=list)
    framework_hints: List[str] = field(default_factory=list)


# ============================================================================
# PATTERN-BASED ANALYZERS
# ============================================================================

def analyze_file(filepath: str, content: str) -> Optional[FileAnalysis]:
    """
    Analyze a source file using configuration-driven pattern matching.
    
    This is the main entry point. It automatically detects the language
    and applies the appropriate analyzer.
    
    Args:
        filepath: Relative path to the file.
        content: File content as string.
        
    Returns:
        FileAnalysis object if supported, None otherwise.
    """
    ext = os.path.splitext(filepath)[1].lower()
    filename = os.path.basename(filepath).lower()
    
    # Check for manifest files first (special handling)
    if filename == "package.json":
        return analyze_package_json(filepath, content)
    if filename == "go.mod":
        return analyze_go_mod(filepath, content)
    if filename in ("requirements.txt", "requirements.in"):
        return analyze_requirements_txt(filepath, content)
    if filename == "pyproject.toml":
        return analyze_pyproject_toml(filepath, content)
    if filename == "cargo.toml":
        return analyze_cargo_toml(filepath, content)
    if filename == "gemfile":
        return analyze_gemfile(filepath, content)
    if filename == "composer.json":
        return analyze_composer_json(filepath, content)
    
    # Get language configuration
    lang_config = get_language_config(ext)
    
    if not lang_config:
        # Fallback to generic analysis
        return analyze_generic_file(filepath, content)
    
    # Use Python's built-in AST for Python files (most accurate)
    if ext == ".py":
        return analyze_python_file(filepath, content, lang_config)
    
    # Use pattern-based analysis for other languages
    return analyze_with_patterns(filepath, content, lang_config)


def analyze_python_file(filepath: str, content: str, config: LanguageConfig) -> FileAnalysis:
    """
    Analyze Python files using the built-in AST module.
    
    This is more accurate than regex for Python since we can parse the syntax tree.
    """
    analysis = FileAnalysis(path=filepath, language=config.name)
    
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        logger.debug(f"Could not parse {filepath}: {e}")
        # Fallback to pattern-based analysis
        return analyze_with_patterns(filepath, content, config)
    
    has_main_block = False
    
    for node in ast.walk(tree):
        # Extract function definitions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
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
            
            prefix = 'async ' if isinstance(node, ast.AsyncFunctionDef) else ''
            signature = f"{prefix}def {node.name}({', '.join(args)})"
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
            
            # Entry point detection
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
        
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                analysis.imports.append(node.module)
        
        # Detect env vars and ports from function calls
        elif isinstance(node, ast.Call):
            _extract_from_call_node(node, analysis, config)
        
        # Detect if __name__ == "__main__"
        elif isinstance(node, ast.If):
            if _is_main_block(node):
                has_main_block = True
        
        # Detect app assignments (app = FastAPI(), etc.)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('app', 'application'):
                    if isinstance(node.value, ast.Call):
                        analysis.entry_points.append(f"{filepath}:{target.id}")
    
    if has_main_block:
        analysis.entry_points.append(f"{filepath}:__main__")
    
    # Detect frameworks from imports
    analysis.framework_hints = _detect_frameworks_from_content(
        content, 
        analysis.imports, 
        config.frameworks
    )
    
    # Deduplicate
    _deduplicate_analysis(analysis)
    
    return analysis


def analyze_with_patterns(filepath: str, content: str, config: LanguageConfig) -> FileAnalysis:
    """
    Analyze a file using regex pattern matching based on language configuration.
    
    This works for any language defined in language_configs.py.
    """
    analysis = FileAnalysis(path=filepath, language=config.name)
    
    # Extract imports
    for pattern in config.import_patterns:
        for match in re.finditer(pattern, content, re.MULTILINE):
            # Get the captured group (the import path)
            if match.groups():
                analysis.imports.append(match.group(1))
    
    # Detect frameworks
    analysis.framework_hints = _detect_frameworks_from_content(
        content,
        analysis.imports,
        config.frameworks
    )
    
    # Extract environment variables
    for pattern in config.env_var_patterns:
        for match in re.finditer(pattern, content):
            if match.groups():
                env_var = match.group(1)
                if env_var and len(env_var) > 1:  # Avoid single-char false positives
                    analysis.env_vars.append(env_var)
    
    # Extract ports
    for pattern in config.port_patterns:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            try:
                port = int(match.group(1))
                if 1000 <= port <= 65535:
                    analysis.exposed_ports.append(port)
            except (ValueError, IndexError):
                pass
    
    # Detect entry points
    for pattern in config.entry_point_patterns:
        if re.search(pattern, content, re.MULTILINE):
            analysis.entry_points.append(f"{filepath}:detected")
    
    # Extract symbols (basic pattern matching for classes/functions)
    _extract_symbols_with_patterns(filepath, content, analysis, config)
    
    _deduplicate_analysis(analysis)
    
    return analysis


def _detect_frameworks_from_content(
    content: str, 
    imports: List[str], 
    frameworks: List[FrameworkPattern]
) -> List[str]:
    """
    Detect frameworks using both imports and content patterns.
    """
    detected = set()
    
    # Sort frameworks by priority (higher first)
    sorted_frameworks = sorted(frameworks, key=lambda f: f.priority, reverse=True)
    
    for fw in sorted_frameworks:
        # Check import patterns
        for pattern in fw.import_patterns:
            if any(re.search(pattern, imp, re.IGNORECASE) for imp in imports):
                detected.add(fw.name)
                break
        
        # Check content patterns
        if fw.name not in detected:
            for pattern in fw.content_patterns:
                if re.search(pattern, content, re.MULTILINE):
                    detected.add(fw.name)
                    break
    
    return list(detected)


def _extract_symbols_with_patterns(
    filepath: str, 
    content: str, 
    analysis: FileAnalysis,
    config: LanguageConfig
) -> None:
    """
    Extract basic symbol information using regex patterns.
    """
    # Language-specific symbol patterns
    if config.name == "JavaScript" or config.name == "TypeScript":
        # Functions
        func_patterns = [
            r'export\s+(?:async\s+)?function\s+(\w+)',
            r'function\s+(\w+)\s*\(',
            r'const\s+(\w+)\s*=\s*(?:async\s*)?\(',
        ]
        for pattern in func_patterns:
            for match in re.finditer(pattern, content):
                analysis.symbols.append(CodeSymbol(match.group(1), 'function', filepath, 0, 0))
        
        # Classes
        class_pattern = r'(?:export\s+)?class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'class', filepath, 0, 0))
    
    elif config.name == "Go":
        # Functions
        func_pattern = r'func\s+(\w+)\s*\('
        for match in re.finditer(func_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'function', filepath, 0, 0))
        
        # Structs (Go's version of classes)
        struct_pattern = r'type\s+(\w+)\s+struct'
        for match in re.finditer(struct_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'struct', filepath, 0, 0))
    
    elif config.name == "Rust":
        # Functions
        func_pattern = r'fn\s+(\w+)\s*\('
        for match in re.finditer(func_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'function', filepath, 0, 0))
        
        # Structs
        struct_pattern = r'struct\s+(\w+)'
        for match in re.finditer(struct_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'struct', filepath, 0, 0))
    
    elif config.name in ("Ruby", "PHP", "Java"):
        # Classes
        class_pattern = r'class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'class', filepath, 0, 0))
    
    elif config.name == "C#":
        # Classes
        class_pattern = r'(?:public\s+|private\s+|internal\s+)?class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'class', filepath, 0, 0))
        
        # Methods
        method_pattern = r'(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:async\s+)?[\w<>]+\s+(\w+)\s*\('
        for match in re.finditer(method_pattern, content):
            if match.group(1) not in ('if', 'for', 'while', 'switch'):  # Filter out keywords
                analysis.symbols.append(CodeSymbol(match.group(1), 'method', filepath, 0, 0))
    
    elif config.name == "Kotlin":
        # Functions
        func_pattern = r'fun\s+(\w+)\s*\('
        for match in re.finditer(func_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'function', filepath, 0, 0))
        
        # Classes
        class_pattern = r'class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'class', filepath, 0, 0))
    
    elif config.name == "Scala":
        # Functions/Methods
        func_pattern = r'def\s+(\w+)\s*[\[\(]'
        for match in re.finditer(func_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'function', filepath, 0, 0))
        
        # Classes and Objects
        class_pattern = r'(?:case\s+)?class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'class', filepath, 0, 0))
        
        object_pattern = r'object\s+(\w+)'
        for match in re.finditer(object_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'object', filepath, 0, 0))
    
    elif config.name == "Elixir":
        # Functions
        func_pattern = r'def\s+(\w+)(?:\s*\(|,|\s+do)'
        for match in re.finditer(func_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'function', filepath, 0, 0))
        
        # Modules
        module_pattern = r'defmodule\s+([\w.]+)'
        for match in re.finditer(module_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'module', filepath, 0, 0))
    
    elif config.name == "Haskell":
        # Functions
        func_pattern = r'^(\w+)\s*::'
        for match in re.finditer(func_pattern, content, re.MULTILINE):
            analysis.symbols.append(CodeSymbol(match.group(1), 'function', filepath, 0, 0))
        
        # Data types
        data_pattern = r'data\s+(\w+)'
        for match in re.finditer(data_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'type', filepath, 0, 0))
    
    elif config.name == "Dart":
        # Functions
        func_pattern = r'(?:Future<\w+>|void|[\w<>]+)\s+(\w+)\s*\('
        for match in re.finditer(func_pattern, content):
            if match.group(1) not in ('if', 'for', 'while', 'switch'):
                analysis.symbols.append(CodeSymbol(match.group(1), 'function', filepath, 0, 0))
        
        # Classes
        class_pattern = r'class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'class', filepath, 0, 0))
    
    elif config.name == "Swift":
        # Functions
        func_pattern = r'func\s+(\w+)\s*\('
        for match in re.finditer(func_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'function', filepath, 0, 0))
        
        # Classes and Structs
        class_pattern = r'class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'class', filepath, 0, 0))
        
        struct_pattern = r'struct\s+(\w+)'
        for match in re.finditer(struct_pattern, content):
            analysis.symbols.append(CodeSymbol(match.group(1), 'struct', filepath, 0, 0))



def _extract_from_call_node(node: ast.Call, analysis: FileAnalysis, config: LanguageConfig) -> None:
    """Extract environment variables and ports from AST Call nodes."""
    try:
        # Environment variables
        if hasattr(node.func, 'attr') and node.func.attr in ('getenv', 'get'):
            if node.args and isinstance(node.args[0], ast.Constant):
                var_name = node.args[0].value
                if isinstance(var_name, str) and len(var_name) > 1:
                    analysis.env_vars.append(var_name)
        
        # Ports
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
            
            # Check positional arguments
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                    port = arg.value
                    if 1000 <= port <= 65535:
                        analysis.exposed_ports.append(port)
    except:
        pass


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


def _deduplicate_analysis(analysis: FileAnalysis) -> None:
    """Remove duplicates from analysis results."""
    analysis.imports = list(set(analysis.imports))
    analysis.env_vars = list(set(analysis.env_vars))
    analysis.exposed_ports = list(set(analysis.exposed_ports))
    analysis.framework_hints = list(set(analysis.framework_hints))
    analysis.entry_points = list(set(analysis.entry_points))


# ============================================================================
# MANIFEST FILE ANALYZERS
# ============================================================================

def analyze_package_json(filepath: str, content: str) -> FileAnalysis:
    """Analyze package.json for Node.js frameworks."""
    from .language_configs import JS_CONFIG
    analysis = FileAnalysis(path=filepath, language="json")
    
    # Detect frameworks from dependencies
    for fw in JS_CONFIG.frameworks:
        for pattern in fw.import_patterns:
            # Search for dependency names
            clean_pattern = pattern.replace(r"\\b", "")
            dep_pattern = f'"{clean_pattern}"'
            if re.search(dep_pattern, content):
                analysis.framework_hints.append(fw.name)
    
    # Extract start script as entry point
    start_script = re.search(r'"start":\s*"([^"]+)"', content)
    if start_script:
        analysis.entry_points.append(f"npm run start ({start_script.group(1)})")
    
    _deduplicate_analysis(analysis)
    return analysis


def analyze_go_mod(filepath: str, content: str) -> FileAnalysis:
    """Analyze go.mod for Go frameworks."""
    from .language_configs import GO_CONFIG
    analysis = FileAnalysis(path=filepath, language="go-mod")
    
    for fw in GO_CONFIG.frameworks:
        for pattern in fw.import_patterns:
            if re.search(pattern, content):
                analysis.framework_hints.append(fw.name)
    
    _deduplicate_analysis(analysis)
    return analysis


def analyze_requirements_txt(filepath: str, content: str) -> FileAnalysis:
    """Analyze requirements.txt for Python frameworks."""
    from .language_configs import PYTHON_CONFIG
    analysis = FileAnalysis(path=filepath, language="pip-requirements")
    
    content_lower = content.lower()
    for fw in PYTHON_CONFIG.frameworks:
        for pattern in fw.import_patterns:
            # Match package names at start of line
            clean_pattern = pattern.replace(r'\b', '').lower()
            if re.search(rf'^\s*{clean_pattern}\b', content_lower, re.MULTILINE):
                analysis.framework_hints.append(fw.name)
    
    _deduplicate_analysis(analysis)
    return analysis


def analyze_pyproject_toml(filepath: str, content: str) -> FileAnalysis:
    """Analyze pyproject.toml for Python frameworks."""
    # Reuse requirements.txt logic
    return analyze_requirements_txt(filepath, content)


def analyze_cargo_toml(filepath: str, content: str) -> FileAnalysis:
    """Analyze Cargo.toml for Rust frameworks."""
    from .language_configs import RUST_CONFIG
    analysis = FileAnalysis(path=filepath, language="toml")
    
    for fw in RUST_CONFIG.frameworks:
        for pattern in fw.import_patterns:
            if re.search(pattern, content):
                analysis.framework_hints.append(fw.name)
    
    _deduplicate_analysis(analysis)
    return analysis


def analyze_gemfile(filepath: str, content: str) -> FileAnalysis:
    """Analyze Gemfile for Ruby frameworks."""
    from .language_configs import RUBY_CONFIG
    analysis = FileAnalysis(path=filepath, language="ruby-gemfile")
    
    for fw in RUBY_CONFIG.frameworks:
        for pattern in fw.import_patterns:
            if re.search(pattern, content):
                analysis.framework_hints.append(fw.name)
    
    _deduplicate_analysis(analysis)
    return analysis


def analyze_composer_json(filepath: str, content: str) -> FileAnalysis:
    """Analyze composer.json for PHP frameworks."""
    from .language_configs import PHP_CONFIG
    analysis = FileAnalysis(path=filepath, language="json")
    
    for fw in PHP_CONFIG.frameworks:
        for pattern in fw.import_patterns:
            dep_pattern = f'"{pattern}"'
            if re.search(dep_pattern, content, re.IGNORECASE):
                analysis.framework_hints.append(fw.name)
    
    _deduplicate_analysis(analysis)
    return analysis


def analyze_generic_file(filepath: str, content: str) -> FileAnalysis:
    """
    Perform generic analysis on unsupported file types.
    
    Uses universal patterns to extract:
    - Environment variables (SCREAMING_SNAKE_CASE)
    - Ports (in assignment patterns)
    - Language hints from shebangs
    """
    ext = os.path.splitext(filepath)[1].lower().replace('.', '') or "unknown"
    analysis = FileAnalysis(path=filepath, language=ext)
    
    # Generic env var detection
    env_pattern = r'\b[A-Z][A-Z0-9_]*_[A-Z0-9_]+\b'
    potential_envs = re.findall(env_pattern, content)
    
    # Filter out noise
    noise = {'STDIN', 'STDOUT', 'STDERR', 'UTF8', 'UUID', 'JSON', 'HTML', 'HTTP', 'HTTPS', 'TODO', 'FIXME'}
    analysis.env_vars = [e for e in set(potential_envs) if e not in noise and len(e) > 3]
    
    # Generic port detection
    port_pattern = r'(?i)port.{0,20}[=:]\s*(\d{4,5})'
    for match in re.finditer(port_pattern, content):
        try:
            port = int(match.group(1))
            if 1024 <= port <= 65535:
                analysis.exposed_ports.append(port)
        except:
            pass
    
    # Shebang detection
    if content.startswith('#!'):
        first_line = content.split('\n')[0].lower()
        lang_map = {
            'python': 'python',
            'node': 'javascript',
            'ruby': 'ruby',
            'php': 'php',
            'bash': 'shell',
            'sh': 'shell',
        }
        for key, lang in lang_map.items():
            if key in first_line:
                analysis.language = lang
                break
    
    _deduplicate_analysis(analysis)
    return analysis


# ============================================================================
# BATCH ANALYSIS
# ============================================================================

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
    supported_exts = set(get_all_supported_extensions())
    
    for rel_path in file_tree:
        abs_path = os.path.join(root_path, rel_path)
        ext = os.path.splitext(rel_path)[1].lower()
        filename = os.path.basename(rel_path).lower()
        
        # Skip if not a supported extension and not a known manifest
        manifest_files = {'package.json', 'go.mod', 'requirements.txt', 'pyproject.toml', 
                         'cargo.toml', 'gemfile', 'composer.json'}
        
        if ext not in supported_exts and filename not in manifest_files:
            continue
        
        try:
            with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            analysis = analyze_file(rel_path, content)
            if analysis:
                results[rel_path] = analysis
                analyzed += 1
                
        except Exception as e:
            logger.debug(f"Could not analyze {rel_path}: {e}")
    
    logger.info(f"Code intelligence: analyzed {analyzed} files across {len(set(get_all_supported_extensions()))} languages")
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
            elif sym.type in ("class", "struct"):
                summary["total_classes"] += 1
    
    # Convert sets to lists for JSON serialization
    summary["languages"] = sorted(summary["languages"])
    summary["frameworks"] = sorted(summary["frameworks"])
    summary["all_env_vars"] = sorted(summary["all_env_vars"])
    summary["all_ports"] = sorted(summary["all_ports"])
    
    return summary
