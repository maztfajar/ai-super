#!/bin/bash
echo "═══════════════════════════════════════"
echo "TEST 1: SYNTAX & IMPORT CHECK"
echo "═══════════════════════════════════════"
python3 -m py_compile agents/tools/core_tools.py && echo "✅ agents/tools/core_tools.py PASS" || echo "❌ agents/tools/core_tools.py FAIL"
python3 -m py_compile agents/executor.py && echo "✅ agents/executor.py PASS" || echo "❌ agents/executor.py FAIL"
python3 -m py_compile core/orchestrator.py && echo "✅ core/orchestrator.py PASS" || echo "❌ core/orchestrator.py FAIL"
python3 -m py_compile core/error_recovery.py && echo "✅ core/error_recovery.py PASS" || echo "❌ core/error_recovery.py FAIL"
python3 -m py_compile agents/agent_registry.py && echo "✅ agents/agent_registry.py PASS" || echo "❌ agents/agent_registry.py FAIL"
python3 -c "import aiofiles; print('✅ aiofiles OK')" || echo "❌ aiofiles FAIL"

echo -e "\n═══════════════════════════════════════"
echo "TEST 2: ASYNC FILE I/O TEST"
echo "═══════════════════════════════════════"
python3 test_file_io.py

echo -e "\n═══════════════════════════════════════"
echo "TEST 3: JSON PARSER ROBUSTNESS TEST"
echo "═══════════════════════════════════════"
python3 test_json_parser.py

echo -e "\n═══════════════════════════════════════"
echo "TEST 4: CONTEXT WINDOW PRUNING TEST"
echo "═══════════════════════════════════════"
python3 test_context_pruning.py

echo -e "\n═══════════════════════════════════════"
echo "TEST 5: SILENT FAILURE PREVENTION TEST"
echo "═══════════════════════════════════════"
python3 test_silent_failure.py

echo -e "\n═══════════════════════════════════════"
echo "TEST 6: PERFORMANCE BENCHMARK"
echo "═══════════════════════════════════════"
python3 test_performance.py
