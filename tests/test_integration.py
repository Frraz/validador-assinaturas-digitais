import os
import unittest
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.models import Base
from app.database.database import get_db

# Criar banco de dados de teste em memória
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Criar as tabelas no banco de teste
Base.metadata.create_all(bind=engine)

# Sobrescrever a dependência get_db
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

class TestIntegration(unittest.TestCase):
    """Testes de integração para a aplicação"""
    
    def setUp(self):
        """Configuração para testes"""
        # Criar diretórios temporários para upload e relatórios
        self.test_upload_dir = tempfile.mkdtemp()
        self.test_report_dir = tempfile.mkdtemp()
        
        # Criar um arquivo PDF de teste
        self.test_pdf = os.path.join(self.test_upload_dir, "test.pdf")
        with open(self.test_pdf, "wb") as f:
            f.write(b"%PDF-1.7\nTest PDF content")
    
    def tearDown(self):
        """Limpeza após testes"""
        # Remover arquivos e diretórios temporários
        if os.path.exists(self.test_pdf):
            os.unlink(self.test_pdf)
        
        for file in os.listdir(self.test_upload_dir):
            os.unlink(os.path.join(self.test_upload_dir, file))
        os.rmdir(self.test_upload_dir)
        
        for file in os.listdir(self.test_report_dir):
            os.unlink(os.path.join(self.test_report_dir, file))
        os.rmdir(self.test_report_dir)
    
    def test_home_page(self):
        """Testa se a página inicial é carregada corretamente"""
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Validador de Assinaturas Digitais em Massa", response.content)
    
    def test_upload_invalid_file(self):
        """Testa upload de arquivo inválido"""
        # Criar um arquivo não-PDF
        invalid_file = os.path.join(self.test_upload_dir, "test.txt")
        with open(invalid_file, "w") as f:
            f.write("This is not a PDF")
            
        with open(invalid_file, "rb") as f:
            files = {"files": (os.path.basename(invalid_file), f, "text/plain")}
            response = client.post("/upload/", files=files)
            
        # Deve retornar erro 400
        self.assertEqual(response.status_code, 400)
        self.assertIn("Tipo de arquivo não permitido", response.json()["detail"])
        
        # Limpar
        os.unlink(invalid_file)
    
    def test_nonexistent_job(self):
        """Testa acesso a job inexistente"""
        response = client.get("/status/nonexistent-job-id")
        self.assertEqual(response.status_code, 404)
        self.assertIn("Trabalho de validação não encontrado", response.json()["detail"])
        
        report_response = client.get("/report/nonexistent-job-id")
        self.assertEqual(report_response.status_code, 404)
        self.assertIn("Trabalho de validação não encontrado", report_response.json()["detail"])


if __name__ == '__main__':
    unittest.main()