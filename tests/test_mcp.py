#!/usr/bin/env python3
"""
Script para probar el servidor MCP en Windows
"""
import subprocess
import json
import sys

def test_mcp_server():
    """Prueba el servidor MCP enviando un mensaje de inicialización"""
    
    # Mensaje de inicialización MCP
    init_message = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        },
        "id": 1
    }
    
    # Mensaje de initialized (notification)
    initialized_message = {
        "jsonrpc": "2.0",
        "method": "initialized",
        "params": {}
    }
    
    # Mensaje para listar tools
    list_tools_message = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2
    }
    
    try:
        print("Iniciando servidor MCP...")
        
        # Iniciar el proceso del servidor
        process = subprocess.Popen(
            [sys.executable, "-m", "server.main"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0,  # Sin buffer
            cwd=r"C:\Users\Andy Ortega\Progras\Redes\MCP-PokeVGC-Teambuilder"
        )
        
        print("Enviando mensaje de inicialización...")
        
        # Enviar mensaje de inicialización
        init_json = json.dumps(init_message) + "\n"
        process.stdin.write(init_json)
        process.stdin.flush()
        
        # Leer respuesta
        response_line = process.stdout.readline()
        if response_line:
            print("Respuesta de initialize:")
            print(response_line.strip())
            
            try:
                response = json.loads(response_line)
                if response.get("result"):
                    print("✓ Inicialización exitosa")
                else:
                    print("❌ Error en inicialización:", response.get("error"))
            except json.JSONDecodeError:
                print("❌ Respuesta no es JSON válido")
        
        # Enviar initialized notification
        print("\nEnviando notification 'initialized'...")
        initialized_json = json.dumps(initialized_message) + "\n"
        process.stdin.write(initialized_json)
        process.stdin.flush()
        
        # Enviar tools/list
        print("\nSolicitando lista de herramientas...")
        list_tools_json = json.dumps(list_tools_message) + "\n"
        process.stdin.write(list_tools_json)
        process.stdin.flush()
        
        # Leer respuesta de tools/list
        tools_response = process.stdout.readline()
        if tools_response:
            print("Respuesta de tools/list:")
            print(tools_response.strip())
            
            try:
                tools_data = json.loads(tools_response)
                if tools_data.get("result") and tools_data["result"].get("tools"):
                    tools = tools_data["result"]["tools"]
                    print(f"✓ {len(tools)} herramientas encontradas:")
                    for tool in tools:
                        print(f"  - {tool.get('name')}: {tool.get('description')}")
                else:
                    print("❌ No se encontraron herramientas")
            except json.JSONDecodeError:
                print("❌ Respuesta de tools no es JSON válido")
        
        # Cerrar el proceso
        process.stdin.close()
        process.wait(timeout=5)
        
        # Mostrar stderr si hay errores
        stderr_output = process.stderr.read()
        if stderr_output:
            print("\nOutput de stderr:")
            print(stderr_output)
            
    except subprocess.TimeoutExpired:
        print("❌ Timeout - el servidor no respondió")
        process.kill()
    except Exception as e:
        print(f"❌ Error ejecutando test: {e}")
        if 'process' in locals():
            process.kill()

if __name__ == "__main__":
    test_mcp_server()