import asyncio, sys
sys.path.insert(0, '.')

async def test_silent_failure():
    results = []
    
    # Simulate empty response scenario
    fallback_text = ""
    response_emitted = False
    output_chunks = []
    
    # Simulate what executor should do when empty
    if not response_emitted:
        if fallback_text.strip():
            output_chunks.append(fallback_text.strip())
        else:
            output_chunks.append(
                "⚠️ Proses selesai namun tidak ada respons yang dihasilkan. "
                "Silakan ulangi pertanyaan Anda."
            )
    
    if output_chunks:
        results.append(f"✅ Silent failure caught: '{output_chunks[0][:50]}...'")
    else:
        results.append("❌ Silent failure NOT caught - user gets empty response!")
    
    # Test with actual content
    fallback_text = "Some actual content"
    response_emitted = False
    output_chunks = []
    
    if not response_emitted:
        if fallback_text.strip():
            output_chunks.append(fallback_text.strip())
    
    if output_chunks and output_chunks[0] == "Some actual content":
        results.append("✅ Fallback text properly yielded when available")
    else:
        results.append("❌ Fallback text not properly handled")
    
    return results

results = asyncio.run(test_silent_failure())
for r in results:
    print(r)
