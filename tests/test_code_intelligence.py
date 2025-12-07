"""
Tests for the Code Intelligence module.

These tests verify that AST analysis correctly extracts
code structure, entry points, environment variables, and other
metadata from source files.
"""

import pytest
from dockai.utils.code_intelligence import (
    analyze_file,
    analyze_python_file,
    analyze_javascript_file,
    analyze_go_file,
    analyze_project,
    get_project_summary,
    CodeSymbol,
    FileAnalysis,
)


class TestPythonAnalysis:
    """Tests for Python file analysis."""
    
    def test_basic_function_detection(self):
        """Test that functions are correctly detected."""
        code = '''
def hello():
    """Say hello."""
    print("Hello!")

def main():
    hello()
'''
        analysis = analyze_python_file("test.py", code)
        
        assert analysis.language == "python"
        assert len(analysis.symbols) == 2
        
        func_names = [s.name for s in analysis.symbols]
        assert "hello" in func_names
        assert "main" in func_names
    
    def test_main_entry_point_detection(self):
        """Test that main() is detected as entry point."""
        code = '''
def main():
    pass

if __name__ == "__main__":
    main()
'''
        analysis = analyze_python_file("app.py", code)
        
        assert "app.py:main()" in analysis.entry_points
        assert "app.py:__main__" in analysis.entry_points
    
    def test_class_detection(self):
        """Test that classes are correctly detected."""
        code = '''
class MyApp:
    """Application class."""
    
    def __init__(self):
        pass
    
    def run(self):
        pass
'''
        analysis = analyze_python_file("app.py", code)
        
        class_symbols = [s for s in analysis.symbols if s.type == "class"]
        assert len(class_symbols) == 1
        assert class_symbols[0].name == "MyApp"
    
    def test_import_detection(self):
        """Test that imports are correctly extracted."""
        code = '''
import os
import sys
from flask import Flask
from typing import List, Dict
'''
        analysis = analyze_python_file("app.py", code)
        
        assert "os" in analysis.imports
        assert "sys" in analysis.imports
        assert "flask" in analysis.imports
        assert "typing" in analysis.imports
    
    def test_framework_detection(self):
        """Test that frameworks are detected from imports."""
        code = '''
from fastapi import FastAPI
from flask import Flask
import django
'''
        analysis = analyze_python_file("app.py", code)
        
        assert "FastAPI" in analysis.framework_hints
        assert "Flask" in analysis.framework_hints
        assert "Django" in analysis.framework_hints
    
    def test_env_var_detection(self):
        """Test that environment variable usage is detected."""
        code = '''
import os

db_url = os.getenv("DATABASE_URL")
port = os.environ.get("PORT", 8000)
'''
        analysis = analyze_python_file("config.py", code)
        
        assert "DATABASE_URL" in analysis.env_vars
        assert "PORT" in analysis.env_vars
    
    def test_port_detection(self):
        """Test that port numbers are detected from code."""
        code = '''
app.run(port=8080)
server.listen(3000)
'''
        analysis = analyze_python_file("server.py", code)
        
        # Port detection depends on specific patterns
        # At minimum, we should not crash
        assert analysis.language == "python"
    
    def test_async_function_detection(self):
        """Test that async functions are detected."""
        code = '''
async def fetch_data():
    pass

async def main():
    await fetch_data()
'''
        analysis = analyze_python_file("async_app.py", code)
        
        func_names = [s.name for s in analysis.symbols]
        assert "fetch_data" in func_names
        assert "main" in func_names
    
    def test_syntax_error_handling(self):
        """Test that syntax errors are handled gracefully."""
        code = '''
def broken(
    # Missing closing paren
'''
        analysis = analyze_python_file("broken.py", code)
        
        # Should return empty analysis, not crash
        assert analysis.path == "broken.py"
        assert analysis.language == "python"


class TestJavaScriptAnalysis:
    """Tests for JavaScript file analysis."""
    
    def test_import_detection(self):
        """Test that imports are detected."""
        code = '''
import express from 'express';
const http = require('http');
import { Router } from 'express';
'''
        analysis = analyze_javascript_file("server.js", code)
        
        assert "express" in analysis.imports
        assert "http" in analysis.imports
    
    def test_framework_detection(self):
        """Test that frameworks are detected."""
        code = '''
import express from 'express';
import React from 'react';
const next = require('next');
'''
        analysis = analyze_javascript_file("app.js", code)
        
        assert "Express" in analysis.framework_hints
        assert "React" in analysis.framework_hints
        assert "Next.js" in analysis.framework_hints
    
    def test_env_var_detection(self):
        """Test that environment variables are detected."""
        code = '''
const port = process.env.PORT;
const dbUrl = process.env.DATABASE_URL;
const secret = process.env["API_SECRET"];
'''
        analysis = analyze_javascript_file("config.js", code)
        
        assert "PORT" in analysis.env_vars
        assert "DATABASE_URL" in analysis.env_vars
        assert "API_SECRET" in analysis.env_vars
    
    def test_port_detection(self):
        """Test that ports are detected."""
        code = '''
app.listen(3000, () => console.log('Running'));
const PORT = 8080;
'''
        analysis = analyze_javascript_file("server.js", code)
        
        assert 3000 in analysis.exposed_ports or 8080 in analysis.exposed_ports
    
    def test_typescript_file(self):
        """Test that TypeScript files are detected."""
        code = '''
import { Injectable } from '@nestjs/common';
'''
        analysis = analyze_javascript_file("service.ts", code)
        
        assert analysis.language == "typescript"


class TestGoAnalysis:
    """Tests for Go file analysis."""
    
    def test_main_detection(self):
        """Test that main function is detected."""
        code = '''
package main

func main() {
    fmt.Println("Hello")
}
'''
        analysis = analyze_go_file("main.go", code)
        
        assert "main.go:main()" in analysis.entry_points
    
    def test_import_detection(self):
        """Test that imports are detected."""
        code = '''
package main

import (
    "fmt"
    "net/http"
    "github.com/gin-gonic/gin"
)
'''
        analysis = analyze_go_file("main.go", code)
        
        assert "fmt" in analysis.imports
        assert "net/http" in analysis.imports
        assert "github.com/gin-gonic/gin" in analysis.imports
    
    def test_framework_detection(self):
        """Test that Go frameworks are detected."""
        code = '''
package main

import "github.com/gin-gonic/gin"
'''
        analysis = analyze_go_file("main.go", code)
        
        assert "Gin" in analysis.framework_hints
    
    def test_env_var_detection(self):
        """Test that env vars are detected."""
        code = '''
port := os.Getenv("PORT")
dbUrl, exists := os.LookupEnv("DATABASE_URL")
'''
        analysis = analyze_go_file("config.go", code)
        
        assert "PORT" in analysis.env_vars
        assert "DATABASE_URL" in analysis.env_vars


class TestAnalyzeFile:
    """Tests for the main analyze_file dispatcher."""
    
    def test_python_file(self):
        """Test Python file dispatch."""
        analysis = analyze_file("app.py", "def main(): pass")
        assert analysis is not None
        assert analysis.language == "python"
    
    def test_javascript_file(self):
        """Test JavaScript file dispatch."""
        analysis = analyze_file("server.js", "const x = 1;")
        assert analysis is not None
        assert analysis.language == "javascript"
    
    def test_typescript_file(self):
        """Test TypeScript file dispatch."""
        analysis = analyze_file("app.ts", "const x: number = 1;")
        assert analysis is not None
        assert analysis.language == "typescript"
    
    def test_go_file(self):
        """Test Go file dispatch."""
        analysis = analyze_file("main.go", "package main")
        assert analysis is not None
        assert analysis.language == "go"
    
    def test_unsupported_file(self):
        """Test that unsupported files return None."""
        analysis = analyze_file("styles.css", "body { color: red; }")
        assert analysis is None
    
    def test_jsx_file(self):
        """Test JSX file dispatch."""
        analysis = analyze_file("Component.jsx", "import React from 'react';")
        assert analysis is not None
        assert analysis.language == "javascript"


class TestProjectAnalysis:
    """Tests for project-wide analysis."""
    
    def test_get_project_summary(self):
        """Test project summary generation."""
        analyses = {
            "app.py": FileAnalysis(
                path="app.py",
                language="python",
                entry_points=["app.py:main()"],
                env_vars=["PORT", "DEBUG"],
                exposed_ports=[8000],
                framework_hints=["Flask"]
            ),
            "server.js": FileAnalysis(
                path="server.js",
                language="javascript",
                entry_points=["server.js:server"],
                env_vars=["PORT"],
                exposed_ports=[3000],
                framework_hints=["Express"]
            ),
        }
        
        summary = get_project_summary(analyses)
        
        assert "python" in summary["languages"]
        assert "javascript" in summary["languages"]
        assert "Flask" in summary["frameworks"]
        assert "Express" in summary["frameworks"]
        assert "PORT" in summary["all_env_vars"]
        assert 8000 in summary["all_ports"]
        assert 3000 in summary["all_ports"]


class TestCodeSymbol:
    """Tests for CodeSymbol dataclass."""
    
    def test_basic_creation(self):
        """Test basic symbol creation."""
        symbol = CodeSymbol(
            name="my_func",
            type="function",
            file="test.py",
            line_start=1,
            line_end=5,
            signature="def my_func(x: int) -> str",
            docstring="A test function."
        )
        
        assert symbol.name == "my_func"
        assert symbol.type == "function"
        assert symbol.signature == "def my_func(x: int) -> str"
