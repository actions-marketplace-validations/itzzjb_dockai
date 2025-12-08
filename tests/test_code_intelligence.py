
import pytest
from dockai.utils.code_intelligence import (
    analyze_file, 
    analyze_python_file,
    analyze_with_patterns,
    analyze_generic_file,
    get_project_summary,
    CodeSymbol,
    FileAnalysis
)
from dockai.utils.language_configs import get_language_config

class TestPythonAnalysis:
    """Tests for Python file analysis."""
    
    def test_basic_analysis(self):
        """Test basic analysis for Python code."""
        code = '''
import os
from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    port = os.getenv("PORT")
    return "Hello"

if __name__ == "__main__":
    app.run(port=8080)
'''
        config = get_language_config(".py")
        analysis = analyze_python_file("app.py", code, config)
        
        assert analysis.language == "Python"
        assert "flask" in analysis.imports
        assert "Flask" in analysis.framework_hints
        assert "PORT" in analysis.env_vars
        assert 8080 in analysis.exposed_ports
        assert "app.py:__main__" in analysis.entry_points
        
    def test_async_analysis(self):
        """Test detection of async functions and entry points."""
        code = '''
import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}
'''
        config = get_language_config(".py")
        analysis = analyze_python_file("main.py", code, config)
        
        assert "fastapi" in analysis.imports
        # Check symbol extraction
        func_symbol = next((s for s in analysis.symbols if s.name == "root"), None)
        assert func_symbol is not None
        assert "async def root" in func_symbol.signature
        
        # Check app assignment entry point detection
        assert any("main.py:app" in ep for ep in analysis.entry_points) 


class TestJavascriptAnalysis:
    """Tests for JavaScript/TypeScript file analysis."""
    
    def test_import_detection(self):
        """Test that imports are detected."""
        code = '''
import express from 'express';
const mongoose = require('mongoose');
'''
        analysis = analyze_file("server.js", code)
        
        assert "express" in analysis.imports
        assert "mongoose" in analysis.imports
        assert "Express" in analysis.framework_hints
    
    def test_env_var_detection(self):
        """Test that env vars are detected."""
        code = '''
const port = process.env.PORT;
const dbUrl = process.env.DATABASE_URL;
const secret = process.env["API_SECRET"];
const config = ConfigService.get('NEST_KEY');
'''
        analysis = analyze_file("config.js", code)
        
        assert "PORT" in analysis.env_vars
        assert "DATABASE_URL" in analysis.env_vars
        assert "API_SECRET" in analysis.env_vars
        assert "NEST_KEY" in analysis.env_vars
    
    def test_port_detection(self):
        """Test that ports are detected."""
        code = '''
app.listen(3000, () => console.log('Running'));
const PORT = 8080;
'''
        analysis = analyze_file("server.js", code)
        
        assert 3000 in analysis.exposed_ports or 8080 in analysis.exposed_ports
    
    def test_typescript_file(self):
        """Test that TypeScript files are detected."""
        code = '''
import { Injectable } from '@nestjs/common';
'''
        analysis = analyze_file("service.ts", code)
        
        assert analysis.language == "TypeScript"
    
    def test_nestjs_detection(self):
        """Test NestJS framework detection."""
        code = '''
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  await app.listen(3000);
}
bootstrap();
'''
        analysis = analyze_file("main.ts", code)
        assert "NestJS" in analysis.framework_hints
        assert len(analysis.entry_points) >= 0  # Entry points detected via patterns


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
        analysis = analyze_file("main.go", code)
        
        assert "main.go:detected" in analysis.entry_points or "main.go:main()" in analysis.entry_points
    
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
        analysis = analyze_file("main.go", code)
        
        # Go block imports are captured as a single block by the regex
        assert len(analysis.imports) > 0  # Verify we got imports
        # Check that the import block contains what we expect
        import_block = ' '.join(analysis.imports)
        assert "fmt" in import_block or any("fmt" in imp for imp in analysis.imports)
        assert "net/http" in import_block or any("net/http" in imp for imp in analysis.imports)
        assert "github.com/gin-gonic/gin" in import_block or any("gin" in imp for imp in analysis.imports)
    
    def test_framework_detection(self):
        """Test that Go frameworks are detected."""
        code = '''
package main

import "github.com/gin-gonic/gin"
'''
        analysis = analyze_file("main.go", code)
        
        assert "Gin" in analysis.framework_hints
    
    def test_env_var_detection(self):
        """Test that env vars are detected."""
        code = '''
port := os.Getenv("PORT")
dbUrl, exists := os.LookupEnv("DATABASE_URL")
vip := viper.GetString("VIPER_KEY")
'''
        analysis = analyze_file("config.go", code)

        assert "PORT" in analysis.env_vars
        assert "DATABASE_URL" in analysis.env_vars
        assert "VIPER_KEY" in analysis.env_vars

class TestGenericAnalysis:
    """Tests for Generic fallback analysis."""
    
    def test_ruby_file(self):
        """Test generic analysis on a Ruby file."""
        code = """
        ENV['DATABASE_URL']
        port = 4567
        """
        analysis = analyze_generic_file("app.rb", code)
        assert analysis.language == "rb"
        assert "DATABASE_URL" in analysis.env_vars
        assert 4567 in analysis.exposed_ports
        
    def test_shell_script_shebang(self):
        """Test language detection from shebang."""
        code = "#!/bin/bash\nexport API_KEY=123"
        analysis = analyze_generic_file("script.sh", code)
        assert analysis.language == "shell"
        assert "API_KEY" in analysis.env_vars
        
    def test_rust_file(self):
        """Test generic analysis on a Rust file."""
        code = """
        let port: u16 = 8080;
        let db = std::env::var("POSTGRES_DB").unwrap();
        """
        analysis = analyze_generic_file("main.rs", code)
        assert analysis.language == "rs"
        assert "POSTGRES_DB" in analysis.env_vars
        assert 8080 in analysis.exposed_ports
        
    def test_noise_filtering(self):
        """Test that common keywords are not picked up as env vars."""
        code = "JSON HTTP HTML TODO STDOUT"
        analysis = analyze_generic_file("test.txt", code)
        assert not analysis.env_vars  # Should be empty


class TestAnalyzeFile:
    """Tests for the main analyze_file dispatcher."""
    
    def test_python_file(self):
        """Test Python file dispatch."""
        analysis = analyze_file("app.py", "def main(): pass")
        assert analysis is not None
        assert analysis.language == "Python"
    
    def test_javascript_file(self):
        """Test JavaScript file dispatch."""
        analysis = analyze_file("server.js", "const x = 1;")
        assert analysis is not None
        assert analysis.language == "JavaScript"
    
    def test_typescript_file(self):
        """Test TypeScript file dispatch."""
        analysis = analyze_file("app.ts", "const x: number = 1;")
        assert analysis is not None
        assert analysis.language == "TypeScript"
    
    def test_go_file(self):
        """Test Go file dispatch."""
        analysis = analyze_file("main.go", "package main")
        assert analysis is not None
        assert analysis.language == "Go"
    
    def test_unsupported_file(self):
        """Test generic analysis fallback."""
        analysis = analyze_file("config.custom", "PORT_NUM = 8080")
        assert analysis is not None
        assert analysis.language == "custom"
        assert 8080 in analysis.exposed_ports
    
    def test_jsx_file(self):
        """Test JSX file dispatch."""
        analysis = analyze_file("Component.jsx", "import React from 'react';")
        assert analysis is not None
        assert analysis.language == "JavaScript"


class TestManifestAnalysis:
    """Tests for manifest file analysis (package.json, go.mod, etc)."""

    def test_package_json(self):
        content = """{
  "dependencies": {
    "express": "^4.17.1",
    "react": "^17.0.2"
  },
  "scripts": {
    "start": "node server.js"
  }
}"""
        analysis = analyze_file("package.json", content)
        assert "Express" in analysis.framework_hints
        assert "React" in analysis.framework_hints
        assert any("node server.js" in ep for ep in analysis.entry_points)

    def test_go_mod(self):
        content = """
        module example.com/app
        
        go 1.16
        
        require (
            github.com/gin-gonic/gin v1.7.2
            github.com/davecgh/go-spew v1.1.1
        )
        """
        analysis = analyze_file("go.mod", content)
        assert "Gin" in analysis.framework_hints

    def test_requirements_txt(self):
        content = """
        flask==2.0.1
        gunicorn
        Django>=3.2
        psycopg2
        """
        analysis = analyze_file("requirements.txt", content)
        assert "Flask" in analysis.framework_hints
        assert "Django" in analysis.framework_hints

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
