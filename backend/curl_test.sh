TOKEN=$(curl -s -X POST http://localhost:7860/api/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"password"}' | grep -o '"token":"[^"]*' | cut -d'"' -f4)
echo "Token: $TOKEN"
curl -s -N -X POST http://localhost:7860/api/chat/send -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"message":"cek ram dan simpan", "model":"orchestrator", "use_rag":false}'
