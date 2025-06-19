import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.validation.signature_validator import (
    validate_signature,
    has_pdf_signatures,
    validate_signatures_cryptographically,
    format_pdf_date
)

class TestSignatureValidator(unittest.TestCase):
    """Testes para o módulo de validação de assinaturas"""
    
    def setUp(self):
        """Configuração para testes"""
        # Criar arquivo temporário para testes
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        self.temp_file.write(b'%PDF-1.7\n')  # Cabeçalho de PDF
        self.temp_file.close()
    
    def tearDown(self):
        """Limpeza após testes"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_validate_nonexistent_file(self):
        """Testa validação com arquivo inexistente"""
        result = validate_signature("arquivo_inexistente.pdf")
        self.assertFalse(result["valid"])
        self.assertEqual("Arquivo não encontrado", result["error"])
    
    @patch('app.validation.signature_validator.PdfReader')
    def test_has_pdf_signatures_with_signature(self, mock_pdf_reader):
        """Testa detecção de assinaturas em um PDF"""
        # Configurar mock para simular um PDF com assinatura
        mock_pdf = MagicMock()
        mock_pdf.trailer = {
            "/Root": {
                "/AcroForm": {
                    "/Fields": [MagicMock()]
                }
            }
        }
        mock_field = mock_pdf.trailer["/Root"]["/AcroForm"]["/Fields"][0]
        mock_field.get_object.return_value = {"/FT": "/Sig"}
        
        mock_pdf_reader.return_value = mock_pdf
        
        # Testar função
        with open(self.temp_file.name, 'rb') as f:
            pdf = mock_pdf_reader(f)
            self.assertTrue(has_pdf_signatures(pdf))
    
    @patch('app.validation.signature_validator.PdfReader')
    def test_has_pdf_signatures_without_signature(self, mock_pdf_reader):
        """Testa detecção de PDF sem assinaturas"""
        # Configurar mock para simular um PDF sem assinatura
        mock_pdf = MagicMock()
        mock_pdf.trailer = {
            "/Root": {
                "/AcroForm": {
                    "/Fields": [MagicMock()]
                }
            }
        }
        mock_field = mock_pdf.trailer["/Root"]["/AcroForm"]["/Fields"][0]
        mock_field.get_object.return_value = {"/FT": "/Btn"}  # Não é assinatura
        
        mock_pdf_reader.return_value = mock_pdf
        
        # Testar função
        with open(self.temp_file.name, 'rb') as f:
            pdf = mock_pdf_reader(f)
            self.assertFalse(has_pdf_signatures(pdf))
    
    def test_format_pdf_date(self):
        """Testa formatação de data do PDF"""
        # Formato típico de data em PDF
        date_str = "D:20250619184145+03'00'"
        formatted = format_pdf_date(date_str)
        self.assertEqual("19/06/2025 18:41:45", formatted)
        
        # Teste com formato inválido
        self.assertEqual("Invalid Date", format_pdf_date("Invalid Date"))
        
        # Teste com None
        self.assertEqual("Desconhecido", format_pdf_date(None))


if __name__ == '__main__':
    unittest.main()